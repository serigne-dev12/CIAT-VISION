"""Tests : importation (colonnes, formats, doublons, confirmation) et administration."""
from __future__ import annotations

import io

from openpyxl import Workbook, load_workbook

ENTETE = ("nom_projet;description;prenom_porteur;nom_porteur;genre;email;telephone;profil;domaine;cohorte;"
          "date_depot;statut;progression;budget_previsionnel;date_limite")


def _csv(lignes: list[str]) -> bytes:
    return ("\n".join([ENTETE, *lignes]) + "\n").encode("utf-8")


def _cohorte(client, h) -> str:
    return client.get("/api/cohorts", headers=h).json()[1]["name"]


def test_modeles_telechargeables(client, coordo):
    r = client.get("/api/imports/template/projects?format=xlsx", headers=coordo)
    assert r.status_code == 200
    wb = load_workbook(io.BytesIO(r.content))
    assert wb.worksheets[0]["A1"].value == "nom_projet" and "Aide" in wb.sheetnames
    assert client.get("/api/imports/template/fundings?format=csv", headers=coordo).status_code == 200


def test_colonne_manquante(client, coordo):
    contenu = b"nom_projet;domaine\nTest;Agriculture\n"
    r = client.post("/api/imports/preview", headers=coordo, data={"entity": "projects"},
                    files={"file": ("p.csv", contenu, "text/csv")})
    assert r.status_code == 200 and "cohorte" in r.json()["missing_columns"]


def test_previsualisation_erreurs_et_doublons(client, coordo):
    c = _cohorte(client, coordo)
    contenu = _csv([
        f"Import valide A;Desc;Awa;Diop;Femme;awa@exemple.sn;;Étudiant ISEP;Agriculture;{c};2025-01-10;En incubation;30;3000000;2026-12-01",
        f"Import date invalide;Desc;Ali;Sow;Homme;;;Externe;Énergie;{c};32/13/2025;En attente;;;",
        f"Import valide A;Desc;Awa;Diop;Femme;;;Étudiant ISEP;Agriculture;{c};2025-01-10;En incubation;30;3000000;",
        f"Import statut faux;Desc;Ali;Sow;Homme;;;Externe;Énergie;{c};2025-01-10;Brouillon;;;",
        f"Import domaine faux;Desc;Ali;Sow;Homme;;;Externe;Astronomie;{c};2025-01-10;En attente;;;",
    ])
    r = client.post("/api/imports/preview", headers=coordo, data={"entity": "projects"},
                    files={"file": ("projets.csv", contenu, "text/csv")})
    d = r.json()
    assert d["total_rows"] == 5 and d["valid_rows"] == 1 and d["error_rows"] == 3 and d["duplicate_rows"] == 1
    erreurs = " ".join(" ".join(x["errors"]) for x in d["rows"])
    assert "date invalide" in erreurs and "non autorisée" in erreurs and "inconnu" in erreurs
    assert "doublon de la ligne 2" in d["rows"][2]["duplicate"]
    # Rien n'a été enregistré par la prévisualisation
    assert client.get("/api/projects?q=Import valide A", headers=coordo).json()["total"] == 0

    # Sans confirmation : refus
    r = client.post("/api/imports/commit", headers=coordo, data={"entity": "projects"},
                    files={"file": ("projets.csv", contenu, "text/csv")})
    assert r.status_code == 422
    # Confirmé mais lignes invalides non acceptées : refus (tout ou rien)
    r = client.post("/api/imports/commit", headers=coordo, data={"entity": "projects", "confirm": "true"},
                    files={"file": ("projets.csv", contenu, "text/csv")})
    assert r.status_code == 422
    # Confirmé en acceptant d'ignorer les lignes invalides
    r = client.post("/api/imports/commit", headers=coordo,
                    data={"entity": "projects", "confirm": "true", "ignore_invalid": "true"},
                    files={"file": ("projets.csv", contenu, "text/csv")})
    assert r.status_code == 200 and r.json() == {"imported": 1, "skipped": 4}
    assert client.get("/api/projects?q=Import valide A", headers=coordo).json()["total"] == 1
    # Ré-import : détecté comme existant
    r = client.post("/api/imports/preview", headers=coordo, data={"entity": "projects"},
                    files={"file": ("projets.csv", contenu, "text/csv")})
    assert r.json()["rows"][0]["duplicate"] == "existe déjà dans la base"


def test_import_excel_cohortes(client, coordo):
    wb = Workbook()
    ws = wb.active
    ws.append(["nom", "annee", "date_debut", "date_fin", "description"])
    ws.append(["Cohorte importée 2031", 2031, "2031-03-01", "2031-12-15", "Test"])
    buf = io.BytesIO()
    wb.save(buf)
    r = client.post("/api/imports/commit", headers=coordo, data={"entity": "cohorts", "confirm": "true"},
                    files={"file": ("cohortes.xlsx", buf.getvalue(),
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert r.status_code == 200 and r.json()["imported"] == 1
    assert any(c["name"] == "Cohorte importée 2031" for c in client.get("/api/cohorts", headers=coordo).json())


def test_format_refuse(client, coordo):
    r = client.post("/api/imports/preview", headers=coordo, data={"entity": "projects"},
                    files={"file": ("x.pdf", b"%PDF", "application/pdf")})
    assert r.status_code == 415


def test_parametres_et_journal(client, admin):
    r = client.put("/api/admin/settings", headers=admin, json={"institution_name": "ISEP Amadou Trawaré de Diamniadio",
                                                               "ai_daily_limit": 40})
    assert r.status_code == 200 and r.json()["ai_daily_limit"] == "40"
    assert client.put("/api/admin/settings", headers=admin, json={"session_minutes": 5}).status_code == 422
    j = client.get("/api/admin/audit-logs?action=CONNEXION", headers=admin).json()
    assert j["total"] > 0 and all(x["action"] == "CONNEXION" for x in j["items"])
    assert "IMPORT" in client.get("/api/admin/audit-logs", headers=admin).json()["actions"]


def test_admin_ne_peut_pas_se_retirer_ses_droits(client, admin):
    moi = client.get("/api/auth/me", headers=admin).json()
    r = client.put(f"/api/admin/users/{moi['id']}", headers=admin, json={"role": "analyst"})
    assert r.status_code == 422
