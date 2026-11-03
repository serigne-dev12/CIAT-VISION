"""Importation de données Excel / CSV (cahier des charges § 6.10).

Étapes : lecture → vérification des colonnes → contrôle ligne par ligne → détection des doublons
→ prévisualisation → (confirmation) → insertion en UNE transaction.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime

from fastapi import HTTPException
from openpyxl import Workbook, load_workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import (FUNDING_SOURCES, GENDERS, LEADER_PROFILES, PROJECT_STATUSES, ApplicationStatus,
                           FundingStatus, ProjectStatus)
from app.models import (Application, Cohort, Domain, Funding, ImportBatch, Partner, Project, ProjectLeader, Responsable,
                        User)
from app.services.common import audit

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5000


@dataclass
class Col:
    name: str
    required: bool
    kind: str = "text"  # text | int | date | email | choice
    choices: list[str] | None = None
    example: str = ""


ENTITIES: dict[str, list[Col]] = {
    "projects": [
        Col("nom_projet", True, example="Application de suivi des cultures"),
        Col("description", False, example="Plateforme mobile d'aide à l'irrigation"),
        Col("prenom_porteur", True, example="Awa"),
        Col("nom_porteur", True, example="Diop"),
        Col("genre", False, "choice", GENDERS, "Femme"),
        Col("email", False, "email", example="awa.diop@exemple.sn"),
        Col("telephone", False, example="+221 77 000 00 00"),
        Col("profil", True, "choice", LEADER_PROFILES, "Étudiant ISEP"),
        Col("domaine", True, "domain", example="Agriculture"),
        Col("cohorte", True, "cohort", example="Cohorte 2026"),
        Col("date_depot", True, "date", example="2026-01-15"),
        Col("statut", True, "choice", PROJECT_STATUSES, "En incubation"),
        Col("progression", False, "int", example="40"),
        Col("budget_previsionnel", False, "int", example="5000000"),
        Col("date_limite", False, "date", example="2026-12-15"),
        Col("responsable", False, "responsable", example="Nom d'un responsable de suivi existant"),
    ],
    "fundings": [
        Col("nom_projet", True, example="Application de suivi des cultures"),
        Col("cohorte", True, "cohort", example="Cohorte 2026"),
        Col("source", True, "choice", FUNDING_SOURCES, "Subvention"),
        Col("partenaire", False, example="Fondation Jeunesse Innovante"),
        Col("montant_demande", True, "int", example="3000000"),
        Col("montant_accorde", False, "int", example="2500000"),
        Col("montant_recu", False, "int", example="1000000"),
        Col("date_demande", True, "date", example="2026-03-10"),
        Col("date_accord", False, "date", example="2026-04-20"),
        Col("statut", True, "choice", [s.value for s in FundingStatus], "Partiellement reçu"),
    ],
    "cohorts": [
        Col("nom", True, example="Cohorte 2027"),
        Col("annee", True, "int", example="2027"),
        Col("date_debut", True, "date", example="2027-03-01"),
        Col("date_fin", True, "date", example="2027-12-15"),
        Col("description", False, example="Promotion 2027 de l'incubateur"),
    ],
}
LABELS = {"projects": "Projets et porteurs", "fundings": "Financements", "cohorts": "Cohortes"}


@dataclass
class RowResult:
    line: int
    data: dict
    errors: list[str] = field(default_factory=list)
    duplicate: str | None = None

    @property
    def valid(self) -> bool:
        return not self.errors and not self.duplicate


def _norm(t: str) -> str:
    t = "".join(c for c in unicodedata.normalize("NFD", str(t).strip().lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


# ------------------------------------------------------------------ lecture
def read_file(content: bytes, filename: str) -> list[dict]:
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "Fichier trop volumineux (5 Mo maximum).")
    nom = filename.lower()
    if nom.endswith(".xlsx"):
        try:
            wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        except Exception:
            raise HTTPException(422, "Fichier Excel illisible ou corrompu.") from None
        rows = list(wb.worksheets[0].iter_rows(values_only=True))
    elif nom.endswith(".csv"):
        try:
            texte = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            texte = content.decode("cp1252")
        try:
            delimiter = csv.Sniffer().sniff(texte[:4096], delimiters=";,").delimiter
        except csv.Error:
            delimiter = ";"
        rows = list(csv.reader(io.StringIO(texte), delimiter=delimiter))
    else:
        raise HTTPException(415, "Format non pris en charge : utilisez un fichier .xlsx ou .csv.")
    rows = [r for r in rows if r and any(c not in (None, "") for c in r)]
    if not rows:
        raise HTTPException(422, "Le fichier est vide.")
    if len(rows) - 1 > MAX_ROWS:
        raise HTTPException(422, f"Trop de lignes ({len(rows) - 1}) : {MAX_ROWS} maximum par import.")
    headers = [_norm(h) if h is not None else "" for h in rows[0]]
    return [{headers[i]: (v.strip() if isinstance(v, str) else v) for i, v in enumerate(r) if i < len(headers)}
            for r in rows[1:]]


# ------------------------------------------------------------------ conversion des valeurs
def _date(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError("date invalide (formats acceptés : AAAA-MM-JJ ou JJ/MM/AAAA)")


def _int(v) -> int:
    if isinstance(v, bool):
        raise ValueError("nombre invalide")
    if isinstance(v, (int, float)):
        if float(v) != int(v):
            raise ValueError("nombre entier attendu")
        return int(v)
    s = re.sub(r"[\s  ]", "", str(v))
    if not re.fullmatch(r"-?\d+", s):
        raise ValueError("nombre entier attendu")
    return int(s)


def validate(db: Session, entity: str, raw_rows: list[dict]) -> tuple[list[str], list[RowResult]]:
    if entity not in ENTITIES:
        raise HTTPException(422, "Type de données inconnu.")
    cols = ENTITIES[entity]
    present = set().union(*(r.keys() for r in raw_rows)) if raw_rows else set()
    missing = [c.name for c in cols if c.required and c.name not in present]
    if missing:
        return missing, []

    domains = {_norm(n): i for i, n in db.execute(select(Domain.id, Domain.name)).all()}
    responsables = {_norm(n): i for i, n in db.execute(select(Responsable.id, Responsable.full_name)).all()}
    cohorts = {_norm(n): i for i, n in db.execute(select(Cohort.id, Cohort.name)).all()}
    choice_maps = {c.name: {_norm(x): x for x in c.choices} for c in cols if c.choices}
    results: list[RowResult] = []
    seen: dict[tuple, int] = {}

    for idx, raw in enumerate(raw_rows, start=2):  # ligne 1 = en-têtes
        rr = RowResult(line=idx, data={})
        for c in cols:
            v = raw.get(c.name)
            if v is None or (isinstance(v, str) and not v.strip()):
                if c.required:
                    rr.errors.append(f"« {c.name} » est obligatoire")
                rr.data[c.name] = None
                continue
            try:
                if c.kind == "date":
                    val = _date(v)
                elif c.kind == "int":
                    val = _int(v)
                    if val < 0:
                        raise ValueError("valeur négative")
                elif c.kind == "choice":
                    val = choice_maps[c.name].get(_norm(v))
                    if val is None:
                        raise ValueError(f"valeur « {v} » non autorisée ({', '.join(c.choices)})")
                elif c.kind == "domain":
                    val = domains.get(_norm(v))
                    if val is None:
                        raise ValueError(f"domaine « {v} » inconnu")
                elif c.kind == "responsable":
                    val = responsables.get(_norm(v))
                    if val is None:
                        raise ValueError(f"responsable « {v} » inconnu (créez-le d'abord)")
                elif c.kind == "cohort":
                    val = cohorts.get(_norm(v))
                    if val is None:
                        raise ValueError(f"cohorte « {v} » inconnue (importez d'abord les cohortes)")
                elif c.kind == "email":
                    val = str(v).strip()
                    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", val):
                        raise ValueError("adresse e-mail invalide")
                else:
                    val = str(v).strip()
                    if len(val) > 150 and c.name != "description":
                        raise ValueError("texte trop long (150 caractères maximum)")
                rr.data[c.name] = val
            except ValueError as e:
                rr.errors.append(f"« {c.name} » : {e}")
                rr.data[c.name] = None
        _business_rules(db, entity, rr)
        key = _dup_key(entity, rr.data)
        if key and not rr.errors:
            if key in seen:
                rr.duplicate = f"doublon de la ligne {seen[key]} du fichier"
            elif _exists(db, entity, rr.data):
                rr.duplicate = "existe déjà dans la base"
            else:
                seen[key] = idx
        results.append(rr)
    return [], results


def _business_rules(db: Session, entity: str, rr: RowResult) -> None:
    d = rr.data
    if entity == "projects":
        if d.get("progression") is not None and not 0 <= d["progression"] <= 100:
            rr.errors.append("« progression » doit être entre 0 et 100")
        if d.get("statut") == ProjectStatus.COMPLETED and d.get("progression") not in (None, 100):
            rr.errors.append("un projet « Terminé » doit avoir une progression de 100")
        if d.get("date_depot") and d["date_depot"] > date.today():
            rr.errors.append("« date_depot » ne peut pas être dans le futur")
        if d.get("date_limite") and d.get("date_depot") and d["date_limite"] <= d["date_depot"]:
            rr.errors.append("« date_limite » doit être postérieure à « date_depot »")
    elif entity == "fundings":
        dem, acc, rec = d.get("montant_demande"), d.get("montant_accorde") or 0, d.get("montant_recu") or 0
        if dem is not None and not rec <= acc <= dem:
            rr.errors.append("les montants doivent respecter : reçu ≤ accordé ≤ demandé")
        if d.get("date_accord") and d.get("date_demande") and d["date_accord"] < d["date_demande"]:
            rr.errors.append("« date_accord » antérieure à « date_demande »")
        if d.get("nom_projet") and d.get("cohorte"):
            pid = db.scalar(select(Project.id).where(func.lower(Project.name) == d["nom_projet"].lower(),
                                                     Project.cohort_id == d["cohorte"], Project.is_archived.is_(False)))
            if pid is None:
                rr.errors.append("projet introuvable dans cette cohorte")
            d["_project_id"] = pid
        st = d.get("statut")
        if st and dem is not None:
            ok = {"Demandé": acc == 0, "Refusé": acc == 0, "Accordé": acc > 0 and rec == 0,
                  "Partiellement reçu": 0 < rec < acc, "Reçu": acc > 0 and rec == acc}[st]
            if not ok:
                rr.errors.append(f"le statut « {st} » ne correspond pas aux montants")
    elif entity == "cohorts":
        if d.get("date_debut") and d.get("date_fin") and d["date_fin"] <= d["date_debut"]:
            rr.errors.append("« date_fin » doit être postérieure à « date_debut »")
        if d.get("annee") is not None and not 2000 <= d["annee"] <= 2100:
            rr.errors.append("« annee » invalide")


def _dup_key(entity: str, d: dict) -> tuple | None:
    if entity == "projects" and d.get("nom_projet") and d.get("cohorte"):
        return (d["nom_projet"].lower(), d["cohorte"])
    if entity == "fundings" and d.get("nom_projet"):
        return (d["nom_projet"].lower(), d.get("cohorte"), d.get("source"), d.get("date_demande"),
                d.get("montant_demande"))
    if entity == "cohorts" and d.get("nom"):
        return (d["nom"].lower(),)
    return None


def _exists(db: Session, entity: str, d: dict) -> bool:
    if entity == "projects":
        return db.scalar(select(Project.id).where(func.lower(Project.name) == d["nom_projet"].lower(),
                                                  Project.cohort_id == d["cohorte"],
                                                  Project.is_archived.is_(False))) is not None
    if entity == "fundings":
        return d.get("_project_id") is not None and db.scalar(select(Funding.id).where(
            Funding.project_id == d["_project_id"], Funding.source_type == d["source"],
            Funding.request_date == d["date_demande"], Funding.amount_requested == d["montant_demande"])) is not None
    return db.scalar(select(Cohort.id).where(func.lower(Cohort.name) == d["nom"].lower())) is not None


# ------------------------------------------------------------------ enregistrement
APP_STATUS = {ProjectStatus.PENDING: ApplicationStatus.RECEIVED, ProjectStatus.EVALUATION: ApplicationStatus.EVALUATION,
              ProjectStatus.NOT_RETAINED: ApplicationStatus.REJECTED}


def commit(db: Session, entity: str, results: list[RowResult], user: User, filename: str) -> dict:
    valides = [r for r in results if r.valid]
    for r in valides:
        d = r.data
        if entity == "projects":
            leader = ProjectLeader(first_name=d["prenom_porteur"], last_name=d["nom_porteur"], gender=d["genre"],
                                   email=d["email"], phone=d["telephone"], profile=d["profil"])
            db.add(leader)
            db.flush()
            st = ProjectStatus(d["statut"])
            app_ = Application(leader_id=leader.id, cohort_id=d["cohorte"], domain_id=d["domaine"],
                               project_title=d["nom_projet"], submitted_at=d["date_depot"],
                               status=APP_STATUS.get(st, ApplicationStatus.ACCEPTED),
                               decision_date=None if st in APP_STATUS and st != ProjectStatus.NOT_RETAINED
                               else d["date_depot"])
            db.add(app_)
            db.flush()
            db.add(Project(application_id=app_.id, name=d["nom_projet"], description=d["description"],
                           leader_id=leader.id, domain_id=d["domaine"], cohort_id=d["cohorte"], status=st.value,
                           progress_pct=100 if st == ProjectStatus.COMPLETED else (d["progression"] or 0),
                           planned_budget=d["budget_previsionnel"] or 0, deadline=d["date_limite"],
                           responsible_id=d.get("responsable")))
        elif entity == "fundings":
            partner_id = None
            if d.get("partenaire"):
                partner = db.scalar(select(Partner).where(func.lower(Partner.name) == d["partenaire"].lower()))
                if partner is None:
                    partner = Partner(name=d["partenaire"], type="Financier")
                    db.add(partner)
                    db.flush()
                partner_id = partner.id
            db.add(Funding(project_id=d["_project_id"], partner_id=partner_id, source_type=d["source"],
                           amount_requested=d["montant_demande"], amount_granted=d["montant_accorde"] or 0,
                           amount_received=d["montant_recu"] or 0, request_date=d["date_demande"],
                           grant_date=d["date_accord"], status=d["statut"]))
        else:
            db.add(Cohort(name=d["nom"], year=d["annee"], start_date=d["date_debut"], end_date=d["date_fin"],
                          description=d["description"]))
    ignorees = len(results) - len(valides)
    db.add(ImportBatch(user_id=user.id, entity=entity, filename=filename[:200], rows_imported=len(valides),
                       rows_skipped=ignorees))
    audit(db, user, "IMPORT", entity, None, f"{filename} : {len(valides)} ligne(s) importée(s), {ignorees} ignorée(s)")
    # Rapport final : le sort de chaque ligne du fichier, avec le motif des lignes ignorées
    rapport = [{"line": r.line, "status": "Importée" if r.valid else "Ignorée",
                "reason": "" if r.valid else " ; ".join([*r.errors, *([r.duplicate] if r.duplicate else [])])}
               for r in results]
    return {"imported": len(valides), "skipped": ignorees, "report": rapport}


# ------------------------------------------------------------------ modèles de fichiers
def template(entity: str, fmt: str) -> tuple[bytes, str, str]:
    cols = ENTITIES[entity]
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow([c.name for c in cols])
        w.writerow([c.example for c in cols])
        return ("﻿" + buf.getvalue()).encode("utf-8"), "text/csv; charset=utf-8", f"modele_{entity}.csv"
    wb = Workbook()
    ws = wb.active
    ws.title = LABELS[entity]
    ws.append([c.name for c in cols])
    ws.append([c.example for c in cols])
    aide = wb.create_sheet("Aide")
    aide.append(["Colonne", "Obligatoire", "Format / valeurs autorisées"])
    for c in cols:
        fmt_txt = {"date": "Date AAAA-MM-JJ ou JJ/MM/AAAA", "int": "Nombre entier positif", "email": "Adresse e-mail",
                   "domain": "Nom exact d'un domaine existant", "cohort": "Nom exact d'une cohorte existante",
                   "responsable": "Nom exact d'un responsable de suivi existant"}.get(
            c.kind, ", ".join(c.choices) if c.choices else "Texte")
        aide.append([c.name, "Oui" if c.required else "Non", fmt_txt])
    for sh in (ws, aide):
        for col in sh.columns:
            sh.column_dimensions[col[0].column_letter].width = max(14, max(len(str(x.value or "")) for x in col) + 2)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"modele_{entity}.xlsx"
