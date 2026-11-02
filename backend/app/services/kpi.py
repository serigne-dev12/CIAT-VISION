"""Moteur d'indicateurs – SOURCE UNIQUE des définitions et des calculs (cahier des charges § 7).

Le tableau de bord, les graphiques, les rapports et l'assistant IA appellent tous ces fonctions :
les chiffres sont donc identiques partout. Les agrégations sont faites en SQL par PostgreSQL.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.orm import Session

from app.constants import (ACTIVE_STATUSES, INCUBATED_STATUSES, ApplicationStatus, ProjectStatus)
from app.models import Application, Cohort, Domain, Funding, Milestone, Project
from app.services.common import get_int_setting

KPI_DEFINITIONS: dict[str, tuple[str, str, str]] = {
    # clé: (libellé, unité, définition)
    "total_projects": ("Total des projets", "count",
                       "Projets enregistrés dont la candidature n'a pas été rejetée (hors « Non retenu »)."),
    "applications": ("Candidatures reçues", "count", "Nombre de candidatures déposées sur le périmètre."),
    "selected": ("Projets sélectionnés", "count", "Candidatures acceptées par le comité de sélection."),
    "in_incubation": ("Projets en incubation", "count", "Projets au statut « En incubation » ou « En développement »."),
    "prototypes": ("Prototypes réalisés", "count",
                   "Projets au statut « Prototype réalisé » ou « Terminé » (un projet terminé a réalisé son prototype)."),
    "completed": ("Projets terminés", "count", "Projets au statut « Terminé »."),
    "delayed": ("Projets en retard", "count",
                "Projets actifs dont la date limite est dépassée, ou dont un jalon non atteint a une date prévue "
                "dépassée de plus du seuil de tolérance. Les projets suspendus ne sont jamais comptés en retard."),
    "funding_received": ("Financements reçus", "amount",
                         "Somme des montants effectivement reçus (FCFA) par les projets du périmètre."),
    "funding_granted": ("Financements accordés", "amount", "Somme des montants accordés (FCFA)."),
    "funding_requested": ("Financements demandés", "amount", "Somme des montants demandés (FCFA)."),
    "planned_budget": ("Budget prévisionnel", "amount", "Somme des budgets prévisionnels des projets (hors non retenus)."),
    "suspended": ("Projets suspendus", "count", "Projets au statut « Suspendu » (comptés à part)."),
    "active": ("Projets actifs", "count",
               "Projets « Sélectionné », « En incubation », « En développement » ou « Prototype réalisé »."),
    "incubated": ("Projets incubés", "count",
                  "Projets ayant atteint au moins « En incubation » (y compris terminés et suspendus)."),
    "selection_rate": ("Taux de sélection", "rate", "Candidatures acceptées ÷ (acceptées + rejetées)."),
    "completion_rate": ("Taux d'achèvement", "rate", "Projets terminés ÷ projets incubés."),
    "delay_rate": ("Taux de retard", "rate", "Projets en retard ÷ projets actifs."),
    "avg_progress": ("Progression moyenne", "percent", "Moyenne des progressions des projets actifs."),
    "avg_funding": ("Financement moyen", "amount",
                    "Somme des montants accordés ÷ nombre de projets ayant obtenu un financement."),
    "remaining_to_receive": ("Reste à recevoir", "amount", "Montants accordés − montants reçus."),
    "uncovered_need": ("Besoin non couvert", "amount",
                       "Budget prévisionnel − montants accordés (projets sélectionnés et suivants)."),
}

DASHBOARD_KPIS = ["total_projects", "applications", "selected", "in_incubation", "prototypes", "completed",
                  "delayed", "funding_received"]


@dataclass
class Filters:
    """Périmètre d'analyse. La période porte sur la date de dépôt de la candidature."""
    start_date: date | None = None
    end_date: date | None = None
    cohort_ids: list[int] = field(default_factory=list)
    domain_ids: list[int] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)

    def conditions(self) -> list:
        c = [Project.is_archived.is_(False)]
        if self.start_date:
            c.append(Application.submitted_at >= self.start_date)
        if self.end_date:
            c.append(Application.submitted_at <= self.end_date)
        if self.cohort_ids:
            c.append(Project.cohort_id.in_(self.cohort_ids))
        if self.domain_ids:
            c.append(Project.domain_id.in_(self.domain_ids))
        if self.statuses:
            c.append(Project.status.in_(self.statuses))
        return c

    def describe(self, db: Session) -> str:
        parts = []
        if self.start_date or self.end_date:
            d1 = self.start_date.strftime("%d/%m/%Y") if self.start_date else "…"
            d2 = self.end_date.strftime("%d/%m/%Y") if self.end_date else "…"
            parts.append(f"Période de dépôt : {d1} → {d2}")
        if self.cohort_ids:
            parts.append("Cohortes : " + ", ".join(db.scalars(select(Cohort.name).where(Cohort.id.in_(self.cohort_ids))
                                                              .order_by(Cohort.year))))
        if self.domain_ids:
            parts.append("Domaines : " + ", ".join(db.scalars(select(Domain.name).where(Domain.id.in_(self.domain_ids))
                                                              .order_by(Domain.name))))
        if self.statuses:
            parts.append("Statuts : " + ", ".join(self.statuses))
        return " | ".join(parts) or "Toutes les données"


def _ratio(a: float | int, b: float | int) -> float | None:
    """Dénominateur nul → None (« non calculable »), jamais 0 ni erreur (cahier des charges § 7.3)."""
    return round(a / b, 4) if b else None


def delayed_condition(db: Session, today: date | None = None):
    """Expression SQL « projet en retard » (cahier des charges § 7.1)."""
    today = today or date.today()
    seuil = today - timedelta(days=get_int_setting(db, "delay_tolerance_days"))
    jalon_en_retard = exists(select(Milestone.id).where(
        Milestone.project_id == Project.id, Milestone.completed_date.is_(None), Milestone.due_date < seuil))
    return and_(Project.status.in_(ACTIVE_STATUSES), or_(Project.deadline < today, jalon_en_retard))


def compute_kpis(db: Session, f: Filters, today: date | None = None) -> dict[str, float | int | None]:
    conds = f.conditions()
    delayed = delayed_condition(db, today)
    active = Project.status.in_(ACTIVE_STATUSES)
    not_rejected = Project.status != ProjectStatus.NOT_RETAINED

    r = db.execute(
        select(
            func.count(Project.id).label("applications"),
            func.count(Project.id).filter(not_rejected).label("total_projects"),
            func.count(Project.id).filter(Application.status == ApplicationStatus.ACCEPTED).label("selected"),
            func.count(Project.id).filter(Application.status == ApplicationStatus.REJECTED).label("rejected"),
            func.count(Project.id).filter(Project.status.in_([ProjectStatus.INCUBATION,
                                                              ProjectStatus.DEVELOPMENT])).label("in_incubation"),
            func.count(Project.id).filter(Project.status.in_([ProjectStatus.PROTOTYPE,
                                                              ProjectStatus.COMPLETED])).label("prototypes"),
            func.count(Project.id).filter(Project.status == ProjectStatus.COMPLETED).label("completed"),
            func.count(Project.id).filter(Project.status == ProjectStatus.SUSPENDED).label("suspended"),
            func.count(Project.id).filter(Project.status.in_(INCUBATED_STATUSES)).label("incubated"),
            func.count(Project.id).filter(active).label("active"),
            func.count(Project.id).filter(delayed).label("delayed"),
            func.avg(Project.progress_pct).filter(active).label("avg_progress"),
            func.coalesce(func.sum(Project.planned_budget).filter(not_rejected), 0).label("planned_budget"),
        ).select_from(Project).join(Application, Application.id == Project.application_id).where(*conds)
    ).one()

    fin = db.execute(
        select(
            func.coalesce(func.sum(Funding.amount_requested), 0),
            func.coalesce(func.sum(Funding.amount_granted), 0),
            func.coalesce(func.sum(Funding.amount_received), 0),
            func.count(func.distinct(Funding.project_id)).filter(Funding.amount_granted > 0),
        ).select_from(Funding).join(Project, Project.id == Funding.project_id)
        .join(Application, Application.id == Project.application_id).where(*conds)
    ).one()
    requested, granted, received, funded_projects = (int(fin[0]), int(fin[1]), int(fin[2]), int(fin[3]))

    # Budget des projets sélectionnés et suivants, pour le besoin non couvert
    budget_selected = db.scalar(
        select(func.coalesce(func.sum(Project.planned_budget), 0)).select_from(Project)
        .join(Application, Application.id == Project.application_id)
        .where(*conds, Application.status == ApplicationStatus.ACCEPTED)) or 0

    return {
        "total_projects": r.total_projects,
        "applications": r.applications,
        "selected": r.selected,
        "in_incubation": r.in_incubation,
        "prototypes": r.prototypes,
        "completed": r.completed,
        "delayed": r.delayed,
        "suspended": r.suspended,
        "active": r.active,
        "incubated": r.incubated,
        "funding_requested": requested,
        "funding_granted": granted,
        "funding_received": received,
        "planned_budget": int(r.planned_budget),
        "remaining_to_receive": granted - received,
        "uncovered_need": max(0, int(budget_selected) - granted),
        "selection_rate": _ratio(r.selected, r.selected + r.rejected),
        "completion_rate": _ratio(r.completed, r.incubated),
        "delay_rate": _ratio(r.delayed, r.active),
        "avg_progress": round(float(r.avg_progress), 1) if r.avg_progress is not None else None,
        "avg_funding": round(granted / funded_projects) if funded_projects else None,
    }


def kpi_payload(values: dict) -> list[dict]:
    """Valeurs + libellés + définitions, prêts pour l'API."""
    return [{"key": k, "label": KPI_DEFINITIONS[k][0], "unit": KPI_DEFINITIONS[k][1],
             "definition": KPI_DEFINITIONS[k][2], "value": v} for k, v in values.items() if k in KPI_DEFINITIONS]


def format_value(key: str, value) -> str:
    """Mise en forme française (rapports, assistant)."""
    if value is None:
        return "non calculable"
    unit = KPI_DEFINITIONS[key][1]
    if unit == "rate":
        return f"{value * 100:.1f} %".replace(".", ",")
    if unit == "percent":
        return f"{value:.1f} %".replace(".", ",")
    if unit == "amount":
        return f"{int(value):,} FCFA".replace(",", " ")
    return f"{int(value):,}".replace(",", " ")


# ------------------------------------------------------------------ séries pour les graphiques
def _base(f: Filters):
    return (select().select_from(Project).join(Application, Application.id == Project.application_id)
            .where(*f.conditions()))


def applications_monthly(db: Session, f: Filters) -> list[dict]:
    mois = func.date_trunc("month", Application.submitted_at).label("mois")
    rows = db.execute(_base(f).add_columns(
        mois,
        func.count(Project.id),
        func.count(Project.id).filter(Application.status == ApplicationStatus.ACCEPTED),
        func.count(Project.id).filter(Application.status == ApplicationStatus.REJECTED),
    ).group_by(mois).order_by(mois)).all()
    return [{"month": m.strftime("%Y-%m"), "received": n, "accepted": a, "rejected": rj} for m, n, a, rj in rows]


def projects_by_domain(db: Session, f: Filters) -> list[dict]:
    rows = db.execute(_base(f).join(Domain, Domain.id == Project.domain_id).add_columns(
        Domain.name,
        func.count(Project.id),
        func.count(Project.id).filter(Project.status != ProjectStatus.NOT_RETAINED),
        func.count(Project.id).filter(Project.status == ProjectStatus.COMPLETED),
    ).group_by(Domain.name).order_by(func.count(Project.id).desc())).all()
    return [{"domain": d, "applications": n, "projects": p, "completed": c} for d, n, p, c in rows]


def projects_by_status(db: Session, f: Filters) -> list[dict]:
    rows = dict(db.execute(_base(f).add_columns(Project.status, func.count(Project.id))
                           .group_by(Project.status)).all())
    return [{"status": s.value, "count": rows.get(s.value, 0)} for s in ProjectStatus if rows.get(s.value)]


def fundings_monthly(db: Session, f: Filters) -> list[dict]:
    mois = func.date_trunc("month", Funding.request_date).label("mois")
    rows = db.execute(
        select(mois, func.sum(Funding.amount_requested), func.sum(Funding.amount_granted),
               func.sum(Funding.amount_received))
        .select_from(Funding).join(Project, Project.id == Funding.project_id)
        .join(Application, Application.id == Project.application_id)
        .where(*f.conditions()).group_by(mois).order_by(mois)).all()
    return [{"month": m.strftime("%Y-%m"), "requested": int(a), "granted": int(b), "received": int(c)}
            for m, a, b, c in rows]


def fundings_by(db: Session, f: Filters, dimension: str) -> list[dict]:
    """Montants par source, domaine ou cohorte."""
    col = {"source": Funding.source_type, "domain": Domain.name, "cohort": Cohort.name}[dimension]
    q = (select(col, func.count(Funding.id), func.sum(Funding.amount_requested), func.sum(Funding.amount_granted),
                func.sum(Funding.amount_received))
         .select_from(Funding).join(Project, Project.id == Funding.project_id)
         .join(Application, Application.id == Project.application_id)
         .join(Domain, Domain.id == Project.domain_id).join(Cohort, Cohort.id == Project.cohort_id)
         .where(*f.conditions()).group_by(col).order_by(func.sum(Funding.amount_granted).desc()))
    return [{"label": lab, "count": n, "requested": int(a), "granted": int(b), "received": int(c)}
            for lab, n, a, b, c in db.execute(q).all()]


def progress_distribution(db: Session, f: Filters) -> list[dict]:
    tranche = case((Project.progress_pct < 20, "0–19 %"), (Project.progress_pct < 40, "20–39 %"),
                   (Project.progress_pct < 60, "40–59 %"), (Project.progress_pct < 80, "60–79 %"),
                   else_="80–100 %")
    rows = dict(db.execute(_base(f).where(Project.status.in_(ACTIVE_STATUSES))
                           .add_columns(tranche, func.count(Project.id)).group_by(tranche)).all())
    return [{"range": t, "count": rows.get(t, 0)} for t in ["0–19 %", "20–39 %", "40–59 %", "60–79 %", "80–100 %"]]


def cohorts_comparison(db: Session, f: Filters) -> list[dict]:
    cohorts = db.scalars(select(Cohort).order_by(Cohort.year)).all()
    out = []
    for c in cohorts:
        if f.cohort_ids and c.id not in f.cohort_ids:
            continue
        sub = Filters(f.start_date, f.end_date, [c.id], f.domain_ids, f.statuses)
        k = compute_kpis(db, sub)
        if not k["applications"]:
            continue
        out.append({"cohort_id": c.id, "cohort": c.name, "year": c.year, **k,
                    "success_rate": k["completion_rate"]})
    return out


def delayed_projects(db: Session, f: Filters, limit: int | None = None, include_leader: bool = False,
                     today: date | None = None) -> list[dict]:
    """Projets en retard avec l'ampleur du retard (le plus important d'abord)."""
    today = today or date.today()
    seuil = today - timedelta(days=get_int_setting(db, "delay_tolerance_days"))
    projets = db.scalars(_base(f).add_columns(Project).where(delayed_condition(db, today))).all()
    ids = [p.id for p in projets]
    jalons: dict[int, list[Milestone]] = {}
    if ids:
        for m in db.scalars(select(Milestone).where(Milestone.project_id.in_(ids), Milestone.completed_date.is_(None),
                                                    Milestone.due_date < seuil).order_by(Milestone.due_date)):
            jalons.setdefault(m.project_id, []).append(m)
    out = []
    for p in projets:
        retards = [(today - m.due_date).days for m in jalons.get(p.id, [])]
        if p.deadline and p.deadline < today:
            retards.append((today - p.deadline).days)
        item = {
            "id": p.id, "name": p.name, "domain": p.domain.name, "cohort": p.cohort.name, "status": p.status,
            "progress_pct": p.progress_pct, "deadline": p.deadline.isoformat() if p.deadline else None,
            "deadline_passed": bool(p.deadline and p.deadline < today),
            "late_milestones": len(jalons.get(p.id, [])),
            "first_late_milestone": jalons[p.id][0].title if jalons.get(p.id) else None,
            "days_late": max(retards) if retards else 0,
        }
        if include_leader:
            item["leader"] = p.leader.full_name
        out.append(item)
    out.sort(key=lambda x: x["days_late"], reverse=True)
    return out[:limit] if limit else out
