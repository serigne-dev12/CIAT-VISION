"""Test de charge : peuple une base DÉDIÉE avec ~1 000 projets simulés puis mesure les temps de réponse de l'API.

Usage (depuis backend/), l'API devant tourner sur cette même base :
    set DATABASE_URL=postgresql+psycopg://…/ciat_vision_perf      (base vide, migrée avec « alembic upgrade head »)
    python -m scripts.mesurer_performances peupler
    uvicorn app.main:app --port 8001
    python -m scripts.mesurer_performances mesurer http://127.0.0.1:8001

Ne JAMAIS lancer « peupler » sur la base de production.
"""
from __future__ import annotations

import random
import statistics
import sys
import time
from datetime import date


def peupler() -> None:
    from sqlalchemy import func, select

    from app import seed
    from app.database import SessionLocal
    from app.models import Domain, Partner, Project

    with SessionLocal() as db:
        if db.scalar(select(func.count(Project.id))):
            sys.exit("La base contient déjà des projets : utilisez une base vide dédiée aux mesures.")
        seed.ensure_reference_data(db)
        seed.create_demo_accounts(db)
        rnd, today = random.Random(seed.GRAINE), date.today()
        domaines = {d.name: d for d in db.scalars(select(Domain))}
        partenaires = []
        for nom, typ in seed.PARTENAIRES:
            partenaires.append(Partner(name=nom, type=typ, is_simulated=True))
            db.add(partenaires[-1])
        db.flush()
        for rang, (annee, nb) in enumerate([(today.year - 3, 200), (today.year - 2, 230), (today.year - 1, 260),
                                            (today.year, 300)]):
            seed._cohorte(db, rnd, annee, nb, 0.4, today, domaines, partenaires, prochaine=False, rang=rang)
        seed._cohorte(db, rnd, today.year + 1, 40, 0.45, today, domaines, partenaires, prochaine=True, rang=4)
        db.commit()
        print("Projets créés :", db.scalar(select(func.count(Project.id))))


def mesurer(base: str) -> None:
    import httpx

    api = base.rstrip("/") + "/api"
    c = httpx.Client(timeout=120)
    h = {"Authorization": "Bearer " + c.post(api + "/auth/login", json={"username": "admin", "password": "Admin@2026"})
         .json()["access_token"]}

    def m(nom: str, f, n: int = 20) -> None:
        d = []
        for _ in range(n):
            t = time.perf_counter()
            r = f()
            d.append((time.perf_counter() - t) * 1000)
            r.raise_for_status()
        d.sort()
        print(f"{nom:34s} médiane {statistics.median(d):6.0f} ms   p95 {d[max(0, int(len(d) * 0.95) - 1)]:6.0f} ms")

    m("Indicateurs (tableau de bord)", lambda: c.get(api + "/analytics/kpis", headers=h))
    m("Séries des graphiques", lambda: c.get(api + "/analytics/charts", headers=h))
    m("Liste des projets", lambda: c.get(api + "/projects", headers=h))
    m("Recherche de projets", lambda: c.get(api + "/projects?q=solaire", headers=h))
    m("Projets en retard", lambda: c.get(api + "/analytics/delayed", headers=h))
    m("Financements", lambda: c.get(api + "/fundings", headers=h))
    m("Assistant (mode dégradé)", lambda: c.post(api + "/assistant/ask", headers=h,
                                                 json={"question": "Quels projets nécessitent une attention particulière ?"}), 5)
    for t, fmt in (("global", "pdf"), ("projects", "pdf"), ("projects", "xlsx")):
        m(f"Rapport {t} {fmt.upper()}", lambda t=t, fmt=fmt: c.post(api + "/reports/generate", headers=h,
                                                                  json={"report_type": t, "format": fmt}), 3)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "peupler":
        peupler()
    elif len(sys.argv) >= 3 and sys.argv[1] == "mesurer":
        mesurer(sys.argv[2])
    else:
        print(__doc__)
