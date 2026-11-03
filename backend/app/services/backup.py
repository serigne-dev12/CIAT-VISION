"""Module 10 (V2) – Sauvegarde et restauration de la base depuis l'application (administrateur uniquement).

Format : JSON compressé (gzip) contenant toutes les tables, la version du schéma (révision Alembic) et la date.
- La restauration vérifie le format et la compatibilité du schéma, puis remplace TOUTES les données en UNE
  transaction (tout ou rien) et réinitialise les compteurs d'identifiants.
- Complément de `pg_dump` (guide d'installation § 7) quand l'outil n'est pas disponible sur l'hébergement.
"""
from __future__ import annotations

import gzip
import json
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import JSON, Date, DateTime, Integer, Numeric, inspect, select, text
from sqlalchemy.orm import Session

from app.database import Base

FORMAT = "ciat-vision-sauvegarde"
VERSION_FORMAT = 1


def _revision(db: Session) -> str | None:
    if not inspect(db.get_bind()).has_table("alembic_version"):
        return None
    return db.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))


def _serialiser(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return str(v)
    return v


def exporter(db: Session) -> tuple[bytes, dict]:
    tables, compte = {}, {}
    for t in Base.metadata.sorted_tables:
        colonnes = [c.name for c in t.columns]
        lignes = [[_serialiser(v) for v in row] for row in db.execute(select(*t.columns)).all()]
        tables[t.name] = {"columns": colonnes, "rows": lignes}
        compte[t.name] = len(lignes)
    contenu = {"format": FORMAT, "version": VERSION_FORMAT, "schema_revision": _revision(db),
               "created_at": datetime.now(UTC).isoformat(), "tables": tables}
    return gzip.compress(json.dumps(contenu, ensure_ascii=False).encode("utf-8")), compte


def _convertir(col, v):
    if v is None:
        return None
    if isinstance(col.type, DateTime):
        return datetime.fromisoformat(v)
    if isinstance(col.type, Date):
        return date.fromisoformat(v)
    if isinstance(col.type, Numeric) and not isinstance(col.type, Integer):
        return Decimal(v)
    if isinstance(col.type, JSON):
        return v
    return v


def lire(contenu: bytes) -> dict:
    try:
        data = json.loads(gzip.decompress(contenu).decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        raise HTTPException(422, "Fichier de sauvegarde illisible (fichier .json.gz produit par CIAT VISION attendu).") \
            from None
    if data.get("format") != FORMAT or data.get("version") != VERSION_FORMAT:
        raise HTTPException(422, "Ce fichier n'est pas une sauvegarde CIAT VISION compatible.")
    return data


def restaurer(db: Session, contenu: bytes) -> dict:
    data = lire(contenu)
    revision = _revision(db)
    if revision and data.get("schema_revision") and data["schema_revision"] != revision:
        raise HTTPException(422, f"Sauvegarde d'une autre version du schéma ({data['schema_revision']}) : version "
                                 f"actuelle {revision}. Restaurez avec la même version de l'application.")
    connues = {t.name for t in Base.metadata.sorted_tables}
    inconnues = set(data["tables"]) - connues
    if inconnues:
        raise HTTPException(422, f"Tables inconnues dans la sauvegarde : {', '.join(sorted(inconnues))}.")
    compte = {}
    # Suppression dans l'ordre inverse des dépendances, puis insertion dans l'ordre des dépendances
    for t in reversed(Base.metadata.sorted_tables):
        db.execute(t.delete())
    for t in Base.metadata.sorted_tables:
        bloc = data["tables"].get(t.name, {"columns": [], "rows": []})
        cols = [t.columns[c] for c in bloc["columns"] if c in t.columns]
        lignes = [{c.name: _convertir(c, v) for c, v in zip(cols, row)} for row in bloc["rows"]]
        if lignes:
            db.execute(t.insert(), lignes)
        compte[t.name] = len(lignes)
        pk = list(t.primary_key.columns)
        if len(pk) == 1 and isinstance(pk[0].type, Integer) and pk[0].autoincrement in (True, "auto"):
            db.execute(text(f"SELECT setval(pg_get_serial_sequence('{t.name}', '{pk[0].name}'), "
                            f"COALESCE((SELECT MAX({pk[0].name}) FROM {t.name}), 0) + 1, false)"))
    return {"tables": compte, "schema_revision": data.get("schema_revision"), "created_at": data.get("created_at")}
