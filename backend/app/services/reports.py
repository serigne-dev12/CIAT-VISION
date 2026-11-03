"""Rapports et exportations : PDF (ReportLab), Excel (OpenPyXL) et CSV (cahier des charges § 6.8).

Une seule fonction rassemble les données d'un rapport (`build_report`) ; trois fonctions les mettent en forme.
Les chiffres sont donc identiques dans les trois formats et dans le tableau de bord.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Funding, Project
from app.services import kpi
from app.services.common import get_setting, has_simulated_data

BRUN = colors.HexColor("#4C311F")
BEIGE = colors.HexColor("#CA9871")
BRUN_PROFOND = colors.HexColor("#362316")
GRIS = colors.HexColor("#F5F5F5")
GRIS_TEXTE = colors.HexColor("#6B625B")
# Palette catégorielle (séries multiples), fixe par série
SERIES = [colors.HexColor(c) for c in ("#4C311F", "#CA9871", "#2A78D6", "#1BAF7A", "#E87BA4", "#6250D6",
                                        "#EB6834", "#8C8A85", "#EDA100")]
STATUS_COLORS = {s: SERIES[i % len(SERIES)] for i, s in enumerate(
    ["En attente", "En évaluation", "Non retenu", "Sélectionné", "En incubation", "En développement",
     "Prototype réalisé", "Terminé", "Suspendu"])}
STATUS_COLORS.update({"Non retenu": colors.HexColor("#B9B4AE"), "Terminé": colors.HexColor("#1BAF7A"),
                      "Suspendu": colors.HexColor("#E34948")})

LOGO_FILE = Path(__file__).resolve().parent.parent / "assets" / "logo.png"  # logo officiel CIAT VISION

TITRES = {
    "global": "Rapport global des activités",
    "projects": "Rapport des projets",
    "cohorts": "Rapport des cohortes",
    "fundings": "Rapport des financements",
    "performance": "Rapport des performances",
    "delays": "Rapport des retards",
}

KPIS_PAR_RAPPORT = {
    "global": ["total_projects", "applications", "selected", "in_incubation", "prototypes", "completed", "delayed",
               "funding_received", "selection_rate", "completion_rate", "delay_rate", "avg_progress"],
    "projects": ["total_projects", "active", "in_incubation", "prototypes", "completed", "suspended", "delayed",
                 "avg_progress", "planned_budget"],
    "cohorts": ["applications", "selected", "selection_rate", "completed", "completion_rate", "avg_funding"],
    "fundings": ["planned_budget", "funding_requested", "funding_granted", "funding_received", "remaining_to_receive",
                 "uncovered_need", "avg_funding"],
    "performance": ["selection_rate", "completion_rate", "delay_rate", "avg_progress", "prototypes", "completed"],
    "delays": ["active", "delayed", "delay_rate", "suspended", "avg_progress"],
}


@dataclass
class TableData:
    title: str
    columns: list[str]
    rows: list[list]
    widths: list[float] | None = None  # proportions pour le PDF


@dataclass
class Chart:
    kind: str  # bar | hbar | pie | line
    title: str
    categories: list[str]
    series: list[tuple[str, list[float]]]


@dataclass
class Report:
    type: str
    title: str
    perimetre: str
    kpis: dict
    kpi_keys: list[str]
    tables: list[TableData] = field(default_factory=list)
    charts: list[Chart] = field(default_factory=list)
    commentary: str | None = None
    simulated: bool = False
    institution: str = ""
    generated_at: datetime = field(default_factory=datetime.now)


def _fcfa(v) -> str:
    return f"{int(v):,}".replace(",", " ")


def _pct(v) -> str:
    return "—" if v is None else f"{v * 100:.1f} %".replace(".", ",")


# ------------------------------------------------------------------ collecte des données
def build_report(db: Session, report_type: str, f: kpi.Filters, commentary: str | None = None) -> Report:
    k = kpi.compute_kpis(db, f)
    r = Report(type=report_type, title=TITRES[report_type], perimetre=f.describe(db), kpis=k,
               kpi_keys=KPIS_PAR_RAPPORT[report_type], commentary=commentary, simulated=has_simulated_data(db),
               institution=get_setting(db, "institution_name"))

    def projets_table() -> TableData:
        rows = []
        q = (select(Project).join(Project.application).where(*f.conditions()).order_by(Project.cohort_id, Project.name))
        granted = {}
        for pid, g in db.execute(select(Funding.project_id, Funding.amount_granted)):
            granted[pid] = granted.get(pid, 0) + g
        retards = {p["id"] for p in kpi.delayed_projects(db, f)}
        for p in db.scalars(q):
            rows.append([p.id, p.name, p.domain.name, p.cohort.name, p.status, p.progress_pct,
                         p.planned_budget, granted.get(p.id, 0), p.deadline.isoformat() if p.deadline else "",
                         "Oui" if p.id in retards else "Non"])
        return TableData("Liste des projets", ["N°", "Projet", "Domaine", "Cohorte", "Statut", "Progression (%)",
                                               "Budget (FCFA)", "Financement obtenu (FCFA)", "Date limite", "En retard"],
                         rows, [5, 26, 17, 11, 12, 7, 9, 9, 9, 5])

    def cohortes_table() -> TableData:
        comp = kpi.cohorts_comparison(db, f)
        return TableData("Comparaison des cohortes",
                         ["Cohorte", "Candidatures", "Sélectionnés", "Taux de sélection", "Terminés",
                          "Taux de réussite", "En retard", "Progression moy. (%)", "Financement moyen (FCFA)"],
                         [[c["cohort"], c["applications"], c["selected"], _pct(c["selection_rate"]), c["completed"],
                           _pct(c["success_rate"]), c["delayed"],
                           "—" if c["avg_progress"] is None else c["avg_progress"],
                           "—" if c["avg_funding"] is None else c["avg_funding"]] for c in comp]), comp

    def retards_table(limit: int | None = None) -> TableData:
        d = kpi.delayed_projects(db, f, limit=limit, include_leader=True)
        return TableData("Projets en retard" + (f" (les {limit} plus importants)" if limit else ""),
                         ["Projet", "Porteur", "Domaine", "Cohorte", "Statut", "Progression (%)", "Jalons en retard",
                          "Date limite dépassée", "Retard max (jours)"],
                         [[p["name"], p["leader"], p["domain"], p["cohort"], p["status"], p["progress_pct"],
                           p["late_milestones"], "Oui" if p["deadline_passed"] else "Non", p["days_late"]]
                          for p in d], [24, 14, 16, 10, 12, 7, 6, 6, 7])

    status = kpi.projects_by_status(db, f)
    domains = kpi.projects_by_domain(db, f)
    pie_status = Chart("pie", "Répartition des projets par statut", [s["status"] for s in status],
                       [("Projets", [s["count"] for s in status])])
    bar_domain = Chart("hbar", "Projets par domaine (hors non retenus)", [d["domain"] for d in domains],
                       [("Projets", [d["projects"] for d in domains])])

    if report_type == "global":
        monthly = kpi.applications_monthly(db, f)
        r.charts += [pie_status, bar_domain,
                     Chart("line", "Évolution mensuelle des candidatures", [m["month"] for m in monthly],
                           [("Reçues", [m["received"] for m in monthly]), ("Acceptées", [m["accepted"] for m in monthly])])]
        r.tables += [cohortes_table()[0], retards_table(10)]
    elif report_type == "projects":
        r.charts += [pie_status, bar_domain]
        r.tables.append(projets_table())
    elif report_type == "cohorts":
        t, comp = cohortes_table()
        cats = [c["cohort"] for c in comp]
        r.charts += [Chart("bar", "Candidatures, sélections et projets terminés par cohorte", cats,
                           [("Candidatures", [c["applications"] for c in comp]),
                            ("Sélectionnés", [c["selected"] for c in comp]),
                            ("Terminés", [c["completed"] for c in comp])]),
                     Chart("line", "Taux de sélection et de réussite par cohorte (%)", cats,
                           [("Sélection", [round((c["selection_rate"] or 0) * 100, 1) for c in comp]),
                            ("Réussite", [round((c["success_rate"] or 0) * 100, 1) for c in comp])])]
        r.tables.append(t)
    elif report_type == "fundings":
        by_source = kpi.fundings_by(db, f, "source")
        by_domain = kpi.fundings_by(db, f, "domain")
        r.charts += [Chart("hbar", "Montants accordés par source (millions FCFA)", [x["label"] for x in by_source],
                           [("Accordé", [round(x["granted"] / 1e6, 1) for x in by_source])]),
                     Chart("hbar", "Montants reçus par domaine (millions FCFA)", [x["label"] for x in by_domain],
                           [("Reçu", [round(x["received"] / 1e6, 1) for x in by_domain])])]
        cols = ["Regroupement", "Nombre", "Demandé (FCFA)", "Accordé (FCFA)", "Reçu (FCFA)", "Reste à recevoir (FCFA)"]
        r.tables += [TableData("Financements par source", cols, [[x["label"], x["count"], x["requested"], x["granted"],
                                                                   x["received"], x["granted"] - x["received"]]
                                                                  for x in by_source]),
                     TableData("Financements par domaine", cols, [[x["label"], x["count"], x["requested"],
                                                                    x["granted"], x["received"],
                                                                    x["granted"] - x["received"]] for x in by_domain])]
    elif report_type == "performance":
        t, comp = cohortes_table()
        dist = kpi.progress_distribution(db, f)
        r.charts += [Chart("bar", "Progression des projets actifs", [d["range"] for d in dist],
                           [("Projets", [d["count"] for d in dist])]),
                     Chart("line", "Taux par cohorte (%)", [c["cohort"] for c in comp],
                           [("Sélection", [round((c["selection_rate"] or 0) * 100, 1) for c in comp]),
                            ("Achèvement", [round((c["completion_rate"] or 0) * 100, 1) for c in comp]),
                            ("Retard", [round((c["delay_rate"] or 0) * 100, 1) for c in comp])]),
                     Chart("hbar", "Projets terminés par domaine", [d["domain"] for d in domains],
                           [("Terminés", [d["completed"] for d in domains])])]
        r.tables.append(t)
    elif report_type == "delays":
        t = retards_table()
        par_domaine: dict[str, int] = {}
        for row in t.rows:
            par_domaine[row[2]] = par_domaine.get(row[2], 0) + 1
        r.charts.append(Chart("hbar", "Projets en retard par domaine", list(par_domaine),
                              [("En retard", list(par_domaine.values()))]))
        r.tables.append(t)
    return r


# ------------------------------------------------------------------ PDF
def _safe(t) -> str:
    """Helvetica (encodage WinAnsi) ne contient pas certains symboles : on les remplace."""
    s = str(t)
    for a, b in (("→", "->"), ("≤", "<="), ("≥", ">="), ("−", "-"), ("⚠️", ""), ("⚠", ""), ("…", "...")):
        s = s.replace(a, b)
    return s.encode("cp1252", "replace").decode("cp1252")


def _esc(t) -> str:
    return _safe(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def draw_logo(width: float = 170, height: float = 34, on_dark: bool = False) -> Drawing:
    """Logo CIAT VISION (version horizontale). Remplacé par app/assets/logo.png si ce fichier existe."""
    d = Drawing(width, height)
    d.add(Rect(0, 0, height, height, rx=6, ry=6, fillColor=BEIGE if on_dark else BRUN, strokeColor=None))
    barres = [(0.22, 0.30), (0.42, 0.50), (0.62, 0.72)]
    for x, h in barres:
        d.add(Rect(height * x, height * 0.18, height * 0.14, height * h, fillColor=BRUN if on_dark else BEIGE,
                   strokeColor=None))
    texte = colors.white if on_dark else BRUN_PROFOND
    d.add(String(height + 8, height * 0.48, "CIAT", fontName="Helvetica-Bold", fontSize=height * 0.42, fillColor=texte))
    d.add(String(height + 8 + height * 1.15, height * 0.48, "VISION", fontName="Helvetica", fontSize=height * 0.42,
                 fillColor=BEIGE))
    d.add(String(height + 8, height * 0.12, "Le pilotage intelligent de l'innovation par la donnée",
                 fontName="Helvetica", fontSize=height * 0.17, fillColor=colors.white if on_dark else GRIS_TEXTE))
    return d


def _chart_drawing(c: Chart, width: float) -> Drawing:
    h = 190 if c.kind != "hbar" else max(120, 22 * len(c.categories) + 50)
    d = Drawing(width, h + 22)
    d.add(String(0, h + 8, _safe(c.title), fontName="Helvetica-Bold", fontSize=10, fillColor=BRUN_PROFOND))
    if not c.categories or not any(any(v for v in s[1]) for s in c.series):
        d.add(String(width / 2, h / 2, "Aucune donnée sur ce périmètre", textAnchor="middle", fontName="Helvetica",
                     fontSize=9, fillColor=GRIS_TEXTE))
        return d
    cats = [_safe(x) for x in c.categories]
    if c.kind == "pie":
        p = Pie()
        p.x, p.y, p.width, p.height = 20, 15, h - 40, h - 40
        p.data = c.series[0][1]
        p.labels = None
        p.slices.strokeColor = colors.white
        p.slices.strokeWidth = 1.5
        for i, cat in enumerate(c.categories):
            p.slices[i].fillColor = STATUS_COLORS.get(cat, SERIES[i % len(SERIES)])
        d.add(p)
        lg = Legend()
        lg.x, lg.y = h + 10, h - 30
        lg.fontName, lg.fontSize = "Helvetica", 8
        lg.alignment = "right"
        lg.columnMaximum = 9
        lg.colorNamePairs = [(STATUS_COLORS.get(cat, SERIES[i % len(SERIES)]), f"{_safe(cat)} : {int(v)}")
                             for i, (cat, v) in enumerate(zip(c.categories, c.series[0][1]))]
        d.add(lg)
        return d
    if c.kind == "hbar":
        ch = HorizontalBarChart()
        ch.x, ch.y, ch.width, ch.height = 190, 10, width - 225, h - 30
        ch.data = [s[1] for s in c.series]
        ch.categoryAxis.categoryNames = cats
        ch.categoryAxis.labels.fontSize = 7.5
        ch.categoryAxis.labels.boxAnchor = "e"
        ch.valueAxis.valueMin = 0
        ch.valueAxis.labels.fontSize = 7
        ch.bars[0].fillColor = BRUN
        ch.bars.strokeColor = None
        ch.barLabelFormat = "%s"
        ch.barLabels.fontSize = 7
        ch.barLabels.nudge = 8
        d.add(ch)
        return d
    if c.kind == "bar":
        ch = VerticalBarChart()
        ch.x, ch.y, ch.width, ch.height = 40, 30, width - 60, h - 70
        ch.data = [s[1] for s in c.series]
        ch.categoryAxis.categoryNames = cats
        ch.categoryAxis.labels.fontSize = 8
        ch.valueAxis.valueMin = 0
        ch.valueAxis.labels.fontSize = 7
        ch.bars.strokeColor = None
        ch.groupSpacing = 8
        for i in range(len(c.series)):
            ch.bars[i].fillColor = SERIES[i] if len(c.series) > 1 else BRUN
        d.add(ch)
    else:  # line
        ch = HorizontalLineChart()
        ch.x, ch.y, ch.width, ch.height = 40, 30, width - 60, h - 70
        ch.data = [s[1] for s in c.series]
        ch.categoryAxis.categoryNames = cats
        ch.categoryAxis.labels.fontSize = 7
        ch.categoryAxis.labels.angle = 45 if len(cats) > 8 else 0
        ch.categoryAxis.labels.boxAnchor = "ne" if len(cats) > 8 else "n"
        ch.valueAxis.valueMin = 0
        ch.valueAxis.labels.fontSize = 7
        for i in range(len(c.series)):
            ch.lines[i].strokeColor = SERIES[i]
            ch.lines[i].strokeWidth = 2
        d.add(ch)
    if len(c.series) > 1:
        lg = Legend()
        lg.x, lg.y = 40, h - 14
        lg.fontName, lg.fontSize = "Helvetica", 8
        lg.alignment = "right"
        lg.columnMaximum = 1
        lg.deltax = 85
        lg.colorNamePairs = [(SERIES[i], _safe(s[0])) for i, s in enumerate(c.series)]
        d.add(lg)
    return d


def render_pdf(r: Report) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=28 * mm,
                            bottomMargin=18 * mm, title=_safe(f"CIAT VISION – {r.title}"), author="CIAT VISION")
    largeur = A4[0] - 32 * mm
    st = getSampleStyleSheet()
    s_titre = ParagraphStyle("t", parent=st["Title"], fontName="Helvetica-Bold", fontSize=18, textColor=BRUN_PROFOND,
                             alignment=TA_LEFT, spaceAfter=4)
    s_h2 = ParagraphStyle("h2", parent=st["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, textColor=BRUN,
                          spaceBefore=10, spaceAfter=6)
    s_txt = ParagraphStyle("p", parent=st["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13.5)
    s_petit = ParagraphStyle("s", parent=s_txt, fontSize=8, leading=10.5, textColor=GRIS_TEXTE)
    s_cell = ParagraphStyle("c", parent=s_txt, fontSize=7.5, leading=9.5)
    s_head = ParagraphStyle("ch", parent=s_cell, fontName="Helvetica-Bold", textColor=colors.white)

    def page(canvas, _doc):
        canvas.saveState()
        # En-tête blanc : le logo officiel (fond transparent, conçu pour un fond clair) s'y pose directement
        if LOGO_FILE.exists():
            canvas.drawImage(str(LOGO_FILE), 15 * mm, A4[1] - 19 * mm, width=42 * mm, height=16 * mm,
                             preserveAspectRatio=True, anchor="w", mask="auto")
        else:
            draw_logo(180, 36).drawOn(canvas, 16 * mm, A4[1] - 16.5 * mm)
        canvas.setFillColor(BRUN)
        canvas.rect(0, A4[1] - 21.5 * mm, A4[0], 1.2 * mm, stroke=0, fill=1)   # filet marron
        canvas.setFillColor(BEIGE)
        canvas.rect(0, A4[1] - 22.3 * mm, A4[0], 0.8 * mm, stroke=0, fill=1)   # filet beige
        canvas.setFillColor(BRUN_PROFOND)
        canvas.setFont("Helvetica", 8.5)
        canvas.drawRightString(A4[0] - 16 * mm, A4[1] - 9 * mm, _safe(r.institution))
        canvas.drawRightString(A4[0] - 16 * mm, A4[1] - 13.5 * mm, "Centre d'Innovation, d'Application et de Transfert")
        canvas.setFillColor(GRIS_TEXTE)
        canvas.setFont("Helvetica", 7.5)
        pied = f"CIAT VISION · {_safe(r.title)} · généré le {r.generated_at:%d/%m/%Y à %H:%M}"
        if r.simulated:
            pied += " · DONNÉES SIMULÉES – NON OFFICIELLES"
        canvas.drawString(16 * mm, 10 * mm, _safe(pied))
        canvas.drawRightString(A4[0] - 16 * mm, 10 * mm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    el: list = [Paragraph(_esc(r.title), s_titre),
                Paragraph(_esc(f"Période / périmètre analysé : {r.perimetre}"), s_txt),
                Paragraph(_esc(f"Date de génération : {r.generated_at:%d/%m/%Y à %H:%M}"), s_petit)]
    if r.simulated:
        t = Table([[Paragraph("<b>Données simulées.</b> Les chiffres de ce rapport proviennent du jeu de données de "
                              "démonstration et ne constituent pas des statistiques officielles du CIAT.", s_cell)]],
                  colWidths=[largeur])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF4E5")),
                               ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#EDA100")),
                               ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        el += [Spacer(1, 6), t]

    # Indicateurs : grille de cartes (3 par ligne)
    el.append(Paragraph("Indicateurs principaux", s_h2))
    cartes = []
    for key in r.kpi_keys:
        lab, _, _ = kpi.KPI_DEFINITIONS[key]
        cartes.append([Paragraph(_esc(lab), s_petit),
                       Paragraph(f"<font size=14 color='#4C311F'><b>{_esc(kpi.format_value(key, r.kpis[key]))}</b></font>",
                                 s_txt)])
    lignes = [cartes[i:i + 3] for i in range(0, len(cartes), 3)]
    lignes[-1] += [""] * (3 - len(lignes[-1]))
    grille = Table([[Table([[c[0]], [c[1]]], colWidths=[largeur / 3 - 8]) if c else "" for c in ln] for ln in lignes],
                   colWidths=[largeur / 3] * 3)
    grille.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GRIS), ("BOX", (0, 0), (-1, -1), 0, colors.white),
                                ("INNERGRID", (0, 0), (-1, -1), 4, colors.white),
                                ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 4),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    el.append(grille)
    el.append(Paragraph("Définitions : " + _esc(" ; ".join(f"{kpi.KPI_DEFINITIONS[k][0]} = {kpi.KPI_DEFINITIONS[k][2]}"
                                                            for k in r.kpi_keys)), s_petit))

    if r.commentary:
        el.append(Paragraph("Commentaire analytique", s_h2))
        for para in r.commentary.strip().split("\n"):
            if para.strip():
                el.append(Paragraph(_esc(para.strip()), s_txt))
        el.append(Paragraph("Commentaire relu et validé par l'utilisateur avant export.", s_petit))

    for i, c in enumerate(r.charts):  # le titre de section reste attaché au premier graphique
        bloc = ([Paragraph("Graphiques", s_h2)] if i == 0 else []) + [_chart_drawing(c, largeur)]
        el += [KeepTogether(bloc), Spacer(1, 8)]

    for t in r.tables:
        el.append(Paragraph(_esc(t.title) + f" ({len(t.rows)})", s_h2))
        if not t.rows:
            el.append(Paragraph("Aucune donnée sur ce périmètre.", s_petit))
            continue
        w = t.widths or [1] * len(t.columns)
        cw = [largeur * x / sum(w) for x in w]
        data = [[Paragraph(_esc(c), s_head) for c in t.columns]]
        for row in t.rows:
            data.append([Paragraph(_esc(_fcfa(v) if isinstance(v, int) and abs(v) >= 10000 else v), s_cell)
                         for v in row])
        tab = Table(data, colWidths=cw, repeatRows=1)
        tab.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), BRUN),
                                 ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
                                 ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5DED6")),
                                 ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                 ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        el.append(tab)

    doc.build(el, onFirstPage=page, onLaterPages=page)
    return buf.getvalue()


# ------------------------------------------------------------------ Excel
def render_xlsx(r: Report) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Synthèse"
    entete = PatternFill("solid", fgColor="4C311F")
    blanc = Font(bold=True, color="FFFFFF")
    ws["A1"] = f"CIAT VISION – {r.title}"
    ws["A1"].font = Font(bold=True, size=14, color="362316")
    ws["A2"] = r.institution
    ws["A3"] = f"Périmètre : {r.perimetre}"
    ws["A4"] = f"Généré le {r.generated_at:%d/%m/%Y %H:%M}"
    ligne = 5
    if r.simulated:
        ws.cell(5, 1, "DONNÉES SIMULÉES – non officielles").font = Font(bold=True, color="C0392B")
        ligne = 6
    ligne += 1
    for j, h in enumerate(["Indicateur", "Valeur", "Valeur affichée", "Définition"], 1):
        c = ws.cell(ligne, j, h)
        c.font, c.fill = blanc, entete
    for key in r.kpi_keys:
        ligne += 1
        lab, unit, defi = kpi.KPI_DEFINITIONS[key]
        ws.cell(ligne, 1, lab)
        v = ws.cell(ligne, 2, r.kpis[key])
        if unit == "rate":
            v.number_format = "0.0%"
        elif unit == "amount":
            v.number_format = "#,##0"
        ws.cell(ligne, 3, kpi.format_value(key, r.kpis[key]))
        ws.cell(ligne, 4, defi).alignment = Alignment(wrap_text=True, vertical="top")
    if r.commentary:
        ligne += 2
        ws.cell(ligne, 1, "Commentaire analytique").font = Font(bold=True, color="4C311F")
        ws.cell(ligne + 1, 1, r.commentary).alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=ligne + 1, start_column=1, end_row=ligne + 1, end_column=4)
        ws.row_dimensions[ligne + 1].height = 15 * (r.commentary.count("\n") + len(r.commentary) // 110 + 2)
    for col, w in zip("ABCD", (32, 16, 20, 90)):
        ws.column_dimensions[col].width = w

    for t in r.tables:
        sh = wb.create_sheet(t.title[:31].replace("/", "-"))
        for j, h in enumerate(t.columns, 1):
            c = sh.cell(1, j, h)
            c.font, c.fill = blanc, entete
        for i, row in enumerate(t.rows, 2):
            for j, v in enumerate(row, 1):
                c = sh.cell(i, j, v)
                if isinstance(v, int) and abs(v) >= 10000:
                    c.number_format = "#,##0"
        for j, h in enumerate(t.columns, 1):
            largeur = max([len(str(h))] + [len(str(row[j - 1])) for row in t.rows[:200]])
            sh.column_dimensions[get_column_letter(j)].width = min(60, max(10, largeur + 2))
        sh.freeze_panes = "A2"
        sh.auto_filter.ref = sh.dimensions

    for c in r.charts:  # données des graphiques, réutilisables dans Excel
        sh = wb.create_sheet(("Graph. " + c.title)[:31].replace("/", "-").replace(":", ""))
        sh.append(["Catégorie"] + [s[0] for s in c.series])
        for i, cat in enumerate(c.categories):
            sh.append([cat] + [s[1][i] for s in c.series])
        sh.column_dimensions["A"].width = 40
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ------------------------------------------------------------------ CSV
def render_csv(r: Report) -> bytes:
    """CSV (séparateur « ; », UTF-8 avec BOM pour Excel) : indicateurs puis tableau principal du rapport."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow([f"CIAT VISION – {r.title}"])
    w.writerow([f"Périmètre : {r.perimetre}"])
    w.writerow([f"Généré le {r.generated_at:%d/%m/%Y %H:%M}"] + (["DONNÉES SIMULÉES"] if r.simulated else []))
    w.writerow([])
    w.writerow(["Indicateur", "Valeur"])
    for key in r.kpi_keys:
        w.writerow([kpi.KPI_DEFINITIONS[key][0], kpi.format_value(key, r.kpis[key])])
    for t in r.tables:
        w.writerow([])
        w.writerow([t.title])
        w.writerow(t.columns)
        w.writerows(t.rows)
    return ("﻿" + buf.getvalue()).encode("utf-8")


def render(r: Report, fmt: str) -> tuple[bytes, str, str]:
    nom = f"ciat_vision_{r.type}_{r.generated_at:%Y%m%d_%H%M}"
    if fmt == "pdf":
        return render_pdf(r), "application/pdf", f"{nom}.pdf"
    if fmt == "xlsx":
        return render_xlsx(r), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"{nom}.xlsx"
    return render_csv(r), "text/csv; charset=utf-8", f"{nom}.csv"
