"""Test de sauvegarde / restauration (exécuté avant la purge finale) : aller-retour complet sans perte."""
from __future__ import annotations

from sqlalchemy import func, select

from app.models import AuditLog, Project, User


def test_sauvegarde_puis_restauration(client, admin, coordo, db):
    assert client.get("/api/admin/backup", headers=coordo).status_code == 403
    r = client.get("/api/admin/backup", headers=admin)
    assert r.status_code == 200 and r.content[:2] == b"\x1f\x8b"  # gzip
    sauvegarde = r.content
    nb_projets = db.scalar(select(func.count(Project.id)))
    nb_users = db.scalar(select(func.count(User.id)))

    # Modification après la sauvegarde : elle doit disparaître à la restauration
    pid = db.scalar(select(Project.id).where(Project.is_archived.is_(False)).limit(1))
    assert client.delete(f"/api/projects/{pid}", headers=coordo).status_code == 204

    fichier = {"file": ("sauvegarde.json.gz", sauvegarde, "application/gzip")}
    assert client.post("/api/admin/restore", headers=admin, data={"confirmation": "oui"},
                       files=fichier).status_code == 422
    assert client.post("/api/admin/restore", headers=admin, data={"confirmation": "RESTAURER"},
                       files={"file": ("x.json.gz", b"pas une sauvegarde", "application/gzip")}).status_code == 422
    r = client.post("/api/admin/restore", headers=admin, data={"confirmation": "RESTAURER"}, files=fichier)
    assert r.status_code == 200, r.text
    db.expire_all()
    assert db.scalar(select(func.count(Project.id))) == nb_projets
    assert db.scalar(select(func.count(User.id))) == nb_users
    assert db.get(Project, pid).is_archived is False  # la suppression postérieure est annulée
    assert db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action == "RESTAURATION")) == 1
    # Les compteurs d'identifiants sont réinitialisés : une création fonctionne après restauration
    nouveau = client.post("/api/responsables", headers=coordo, json={"full_name": "Après restauration"})
    assert nouveau.status_code == 201
