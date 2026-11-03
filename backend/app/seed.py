"""Données de référence, comptes de démonstration et jeu de données SIMULÉES (cahier des charges § 11).

- Toutes les personnes, projets, partenaires et montants sont INVENTÉS.
- Chaque enregistrement simulé porte `is_simulated = true` : l'administrateur peut tous les purger
  (`purge_simulated`) avant d'importer les données réelles du CIAT.
- Génération reproductible (graine fixe) et cohérente dans le temps : les cohortes sont calculées par rapport
  à la date du jour, les jalons manqués produisent naturellement des projets en retard.

Utilisation en ligne de commande :  python -m app.seed  [--reset]
"""
from __future__ import annotations

import random
import sys
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.constants import DEFAULT_MILESTONES, ApplicationStatus, ProjectStatus, Role
from app.models import (Activity, Alert, Application, Cohort, Domain, Evaluation, Funding, Milestone, Objective,
                        Partner, Project, ProjectLeader, ProjectStatusHistory, Responsable, User)
from app.security import hash_password

GRAINE = 2026

DOMAINES = {
    "Technologies de l'information et du numérique": "Logiciels, plateformes web et mobiles, services numériques.",
    "Intelligence artificielle": "Solutions fondées sur l'apprentissage automatique et l'analyse de données.",
    "Agriculture": "Production, transformation et valorisation agricoles.",
    "Énergie": "Énergies renouvelables, efficacité énergétique, électrification.",
    "Mécanique": "Fabrication, maintenance industrielle, machines et équipements.",
    "Environnement": "Gestion des déchets, de l'eau et préservation des ressources.",
    "Éducation": "Formation, outils pédagogiques et insertion professionnelle.",
    "Santé et biomédical": "Dispositifs médicaux, santé numérique, produits pharmaceutiques.",
}
POIDS = [0.22, 0.12, 0.17, 0.12, 0.08, 0.10, 0.10, 0.09]

IDEES = {
    "Technologies de l'information et du numérique": [
        "Plateforme de gestion des stocks pour boutiques", "Application de paiement des cantines scolaires",
        "Marketplace des artisans locaux", "Application de suivi des transports urbains",
        "Plateforme de recrutement des diplômés", "Logiciel de gestion des GIE"],
    "Intelligence artificielle": [
        "Chatbot en wolof pour les services publics", "Détection des maladies du manguier par image",
        "Prévision de la demande pour les commerçants", "Orientation scolaire assistée par IA",
        "Tri automatique du courrier administratif"],
    "Agriculture": [
        "Transformation de mangues en jus et confitures", "Unité de transformation du mil",
        "Capteurs d'humidité pour l'irrigation goutte-à-goutte", "Séchoir solaire pour produits halieutiques",
        "Production de semences maraîchères certifiées"],
    "Énergie": [
        "Kits solaires pour cases rurales", "Biodigesteur pour exploitations familiales",
        "Audit énergétique pour PME", "Lampadaires solaires intelligents", "Cuiseurs améliorés économes"],
    "Mécanique": [
        "Atelier mobile de réparation de motopompes", "Décortiqueuse d'arachide améliorée",
        "Pièces détachées par impression 3D", "Presse à briques en terre compressée"],
    "Environnement": [
        "Valorisation des déchets plastiques en pavés", "Compost organique à partir des déchets de marché",
        "Collecte intelligente des ordures ménagères", "Filtre à eau à base de matériaux locaux"],
    "Éducation": [
        "Laboratoire mobile de sciences", "Application d'apprentissage du codage",
        "Plateforme de cours en ligne pour artisans", "Programme d'insertion en électricité bâtiment"],
    "Santé et biomédical": [
        "Application de rappel des vaccinations", "Glucomètre connecté à bas coût",
        "Savons et gels à base de plantes locales", "Télé-consultation pour les postes de santé"],
}
LIEUX = ["Diamniadio", "Thiès", "Kaolack", "Saint-Louis", "Ziguinchor", "Touba", "Mbour", "Rufisque", "Louga",
         "Tambacounda", "Fatick", "Kolda"]
PRENOMS_F = ["Awa", "Fatou", "Aminata", "Mariama", "Khady", "Ndeye", "Astou", "Coumba", "Aïssatou", "Bineta",
             "Seynabou", "Adja", "Rokhaya", "Dieynaba", "Yacine", "Marème", "Sokhna", "Oumou"]
PRENOMS_H = ["Mamadou", "Moussa", "Ibrahima", "Cheikh", "Abdoulaye", "Ousmane", "Serigne", "Modou", "Pape", "Alioune",
             "Babacar", "Lamine", "Omar", "Saliou", "Malick", "Assane", "Daouda", "Elhadji"]
NOMS = ["Diop", "Ndiaye", "Fall", "Sow", "Diallo", "Gueye", "Faye", "Sarr", "Ba", "Cissé", "Mbaye", "Thiam", "Kane",
        "Seck", "Ndao", "Diouf", "Sy", "Camara", "Wade", "Touré", "Niang", "Dieng", "Sène", "Badji"]
PARTENAIRES = [("Fondation Jeunesse Innovante (fictif)", "Financier"), ("SénéTech Solutions (fictif)", "Technique"),
               ("Agence régionale de développement (fictif)", "Institutionnel"),
               ("Université partenaire (fictif)", "Académique"), ("Coopérative agricole de Thiès (fictif)", "Commercial"),
               ("Banque solidaire du Sahel (fictif)", "Financier"), ("FabLab Dakar Sud (fictif)", "Technique"),
               ("Programme d'appui aux PME (fictif)", "Financier"), ("Réseau des incubateurs (fictif)", "Institutionnel"),
               ("Groupe industriel Atlantique (fictif)", "Commercial"), ("Fonds vert local (fictif)", "Financier"),
               ("Centre de recherche agronomique (fictif)", "Académique")]
RESPONSABLES = [("Aïda Mbengue (fictif)", "Chargée d'incubation"), ("Ibrahima Ndour (fictif)", "Chargé d'incubation"),
                ("Ndèye Fatou Sarr (fictif)", "Coach entrepreneuriat"), ("Mamadou Lamine Ba (fictif)", "Expert technique"),
                ("Khadija Diallo (fictif)", "Chargée de partenariats"), ("Ousmane Faye (fictif)", "Coach financement")]
EVALUATEURS = ["Comité CIAT – membre A", "Comité CIAT – membre B", "Comité CIAT – membre C", "Expert externe"]
ACTIVITES = [("Formation", "Modèle économique et plan d'affaires"), ("Atelier", "Prototypage rapide au FabLab"),
             ("Mentorat", "Séances de mentorat individuel"), ("Événement", "Journée de présentation aux investisseurs"),
             ("Formation", "Gestion financière d'une jeune entreprise"), ("Atelier", "Propriété intellectuelle"),
             ("Événement", "Concours d'innovation de l'ISEP"), ("Formation", "Marketing digital")]

COMPTES_DEMO = [("admin", "Administrateur CIAT", "admin@ciat-vision.exemple", Role.ADMIN, "Admin@2026"),
                ("coordo", "Coordonnateur du CIAT", "coordo@ciat-vision.exemple", Role.COORDINATOR, "Coordo@2026"),
                ("analyste", "Analyste de données", "analyste@ciat-vision.exemple", Role.ANALYST, "Analyste@2026")]


# ------------------------------------------------------------------ référentiels et comptes
def ensure_reference_data(db: Session) -> None:
    existants = set(db.scalars(select(Domain.name)))
    for nom, desc in DOMAINES.items():
        if nom not in existants:
            db.add(Domain(name=nom, description=desc))
    db.commit()


def create_demo_accounts(db: Session) -> None:
    if db.scalar(select(User.id).limit(1)) is not None:
        return
    for username, nom, email, role, mdp in COMPTES_DEMO:
        db.add(User(username=username, full_name=nom, email=email, role=role.value, password_hash=hash_password(mdp)))
    db.commit()


# ------------------------------------------------------------------ données simulées
def _ts(d: date) -> datetime:
    return datetime.combine(d, time(10, 0), tzinfo=UTC)


def seed_simulated(db: Session, today: date | None = None) -> bool:
    """Peuple la base si elle ne contient aucun projet. Renvoie True si des données ont été créées."""
    if db.scalar(select(Project.id).limit(1)) is not None:
        return False
    ensure_reference_data(db)
    today = today or date.today()
    rnd = random.Random(GRAINE)
    domaines = {d.name: d for d in db.scalars(select(Domain))}
    partenaires = []
    for nom, typ in PARTENAIRES:
        p = Partner(name=nom, type=typ, is_simulated=True)
        db.add(p)
        partenaires.append(p)
    db.flush()
    responsables = []
    for nom, fonction in RESPONSABLES:
        responsables.append(Responsable(full_name=nom, function=fonction, is_simulated=True))
        db.add(responsables[-1])
    db.flush()

    # Les 4 dernières cohortes démarrées + la prochaine (candidatures en cours d'examen)
    derniere = today.year if today >= date(today.year, 3, 1) else today.year - 1
    plan = [(derniere - 3, 45, 0.30), (derniere - 2, 55, 0.34), (derniere - 1, 65, 0.38), (derniere, 80, 0.42)]
    for rang, (annee, nb, part_f) in enumerate(plan):
        _cohorte(db, rnd, annee, nb, part_f, today, domaines, partenaires, prochaine=False, rang=rang,
                 responsables=responsables)
    _cohorte(db, rnd, derniere + 1, 24, 0.45, today, domaines, partenaires, prochaine=True, rang=4,
             responsables=responsables)
    _objectifs(db, today)
    db.commit()
    return True


def _objectifs(db: Session, today: date) -> None:
    """Objectifs d'exemple pour l'année en cours (SIMULÉS)."""
    debut, fin = date(today.year, 1, 1), date(today.year, 12, 31)
    for label, indicateur, cible in [
        ("Projets à accompagner en " + str(today.year), "projets_accompagnes", 50),
        ("Projets à terminer en " + str(today.year), "projets_termines", 30),
        ("Financements à mobiliser en " + str(today.year) + " (FCFA)", "financements_mobilises", 120_000_000),
        ("Prototypes à réaliser en " + str(today.year), "prototypes", 40),
    ]:
        db.add(Objective(label=label, indicator=indicateur, target_value=cible, start_date=debut, end_date=fin,
                         is_simulated=True))
    precedente = db.scalar(select(Cohort).where(Cohort.year == today.year - 1))
    if precedente:  # le taux d'achèvement se juge sur une cohorte dont l'incubation est terminée
        db.add(Objective(label=f"Taux d'achèvement visé – {precedente.name}", indicator="taux_achevement",
                         target_value=80, start_date=debut, end_date=fin, cohort_id=precedente.id,
                         is_simulated=True))


def _cohorte(db, rnd, annee, nb, part_f, today, domaines, partenaires, prochaine: bool, rang: int,
             responsables: list | None = None) -> None:
    debut, fin = date(annee, 3, 1), date(annee, 12, 15)
    c = Cohort(name=f"Cohorte {annee}", year=annee, start_date=debut, end_date=fin, is_simulated=True,
               description=f"Promotion {annee} de l'incubateur (données simulées).")
    db.add(c)
    db.flush()

    if not prochaine:
        for typ, titre in rnd.sample(ACTIVITES, 6):
            jour = debut + timedelta(days=rnd.randint(10, (fin - debut).days - 10))
            if jour <= today:
                db.add(Activity(title=titre, type=typ, activity_date=jour, cohort_id=c.id, is_simulated=True,
                                participants_count=rnd.randint(12, 60)))

    for _ in range(nb):
        femme = rnd.random() < part_f
        prenom = rnd.choice(PRENOMS_F if femme else PRENOMS_H)
        nom = rnd.choice(NOMS)
        ascii_ = (prenom + "." + nom).lower().translate(str.maketrans("ïëéèçâ", "ieeeca"))
        leader = ProjectLeader(first_name=prenom, last_name=nom, gender="Femme" if femme else "Homme",
                               email=f"{ascii_}{rnd.randint(1, 99)}@exemple.sn",
                               phone=f"+221 7{rnd.choice('0678')} {rnd.randint(100, 999)} {rnd.randint(10, 99)} "
                                     f"{rnd.randint(10, 99)}",
                               profile=rnd.choices(["Étudiant ISEP", "Diplômé ISEP", "Externe"], [0.5, 0.3, 0.2])[0],
                               is_simulated=True)
        db.add(leader)
        db.flush()

        nom_dom = rnd.choices(list(DOMAINES), POIDS)[0]
        titre = f"{rnd.choice(IDEES[nom_dom])} – {rnd.choice(LIEUX)}"
        if prochaine:
            depot = today - timedelta(days=rnd.randint(1, 45))
        else:
            depot = date(annee, 1, 5) + timedelta(days=rnd.randint(0, 45))
        app_ = Application(leader_id=leader.id, cohort_id=c.id, domain_id=domaines[nom_dom].id, project_title=titre,
                           submitted_at=depot, status=ApplicationStatus.RECEIVED.value, is_simulated=True)
        db.add(app_)
        db.flush()

        budget = int(round(rnd.uniform(1.0, 9.0) * 1_000_000, -5))
        p = Project(application_id=app_.id, name=titre, leader_id=leader.id, domain_id=domaines[nom_dom].id,
                    cohort_id=c.id, status=ProjectStatus.PENDING.value, progress_pct=0, planned_budget=budget,
                    deadline=fin, description=f"Projet d'incubation dans le domaine « {nom_dom} » (données simulées).",
                    is_simulated=True, created_at=_ts(depot))
        db.add(p)
        db.flush()
        hist = [(None, ProjectStatus.PENDING, depot)]

        # --- candidature : en attente / en évaluation (prochaine cohorte) ou décision
        niveau = rnd.gauss(10.9 + rang * 0.3, 2.6)  # qualité des dossiers en légère hausse
        nb_eval = 0 if (prochaine and rnd.random() < 0.45) else rnd.randint(2, 3)
        decision = date(annee, 2, 25)
        # L'évaluation précède toujours la décision du comité (cohérence de l'historique)
        jour_eval = (min(today, depot + timedelta(days=rnd.randint(3, 20))) if prochaine
                     else min(decision - timedelta(days=1), depot + timedelta(days=rnd.randint(3, 15))))
        notes = []
        for k in range(nb_eval):
            note = round(min(19.5, max(4, rnd.gauss(niveau, 1.3))), 1)
            notes.append(note)
            db.add(Evaluation(application_id=app_.id, evaluator=EVALUATEURS[k], score=note, evaluated_at=jour_eval,
                              recommendation="Favorable" if note >= 12 else ("Réservé" if note >= 10 else "Défavorable"),
                              comment="Évaluation simulée.", is_simulated=True))
        if prochaine:
            if nb_eval:
                app_.status, p.status = ApplicationStatus.EVALUATION.value, ProjectStatus.EVALUATION.value
                hist.append((ProjectStatus.PENDING, ProjectStatus.EVALUATION, jour_eval))
            for a, b, d in hist:
                db.add(ProjectStatusHistory(project_id=p.id, old_status=a.value if a else None, new_status=b.value,
                                            changed_at=_ts(d), comment="Historique simulé"))
            continue

        hist.append((ProjectStatus.PENDING, ProjectStatus.EVALUATION, jour_eval))
        if sum(notes) / len(notes) < 12:
            app_.status, app_.decision_date = ApplicationStatus.REJECTED.value, decision
            p.status, p.planned_budget = ProjectStatus.NOT_RETAINED.value, 0
            hist.append((ProjectStatus.EVALUATION, ProjectStatus.NOT_RETAINED, decision))
        else:
            app_.status, app_.decision_date = ApplicationStatus.ACCEPTED.value, decision
            hist.append((ProjectStatus.EVALUATION, ProjectStatus.SELECTED, decision))
            # Entrées en incubation échelonnées et durées variables : parcours plus réalistes
            debut_p = debut + timedelta(days=rnd.randint(0, 90))
            p.deadline = debut_p + timedelta(days=rnd.randint(250, 330))
            hist += _parcours(db, rnd, p, debut_p, p.deadline, today)
            _financements(db, rnd, p, debut, fin, today, partenaires, ancienne=fin < today)
            if responsables:
                p.responsible_id = rnd.choices(responsables, [5, 4, 3, 2, 2, 1])[0].id
        for a, b, d in hist:
            db.add(ProjectStatusHistory(project_id=p.id, old_status=a.value if a else None, new_status=b.value,
                                        changed_at=_ts(d), comment="Historique simulé"))
        # Dernière mise à jour réaliste : dernier événement connu (changement de statut ou jalon atteint)
        evenements = [d for _, _, d in hist] + [m.completed_date for m in p.milestones if m.completed_date]
        p.updated_at = _ts(min(today, max(evenements)))


def _parcours(db, rnd, p: Project, debut: date, fin: date, today: date) -> list:
    """Jalons + statut cohérents : un projet « à l'heure » a atteint tous ses jalons échus."""
    n = len(DEFAULT_MILESTONES)
    pas = (fin - debut) / n
    echeances = [debut + pas * (i + 1) for i in range(n)]
    dus = sum(1 for e in echeances if e <= today)
    tirage = rnd.random()
    if tirage < 0.07:
        profil = "suspendu"
        faits = max(1, min(dus, rnd.randint(1, 3)))
    elif tirage < 0.07 + (0.24 if fin >= today else 0.16):
        profil = "retard"
        faits = max(0, dus - rnd.randint(1, 2))
    elif tirage > 0.93 and dus < n:
        profil = "avance"
        faits = min(n, dus + 1)
    else:
        profil = "normal"
        faits = dus

    for i, (titre, ech) in enumerate(zip(DEFAULT_MILESTONES, echeances)):
        fait = None
        if i < faits:
            glissement = rnd.randint(5, 35) if profil == "retard" else rnd.randint(-12, 6)
            fait = min(today, ech + timedelta(days=glissement))
        p.milestones.append(Milestone(title=titre, position=i + 1, due_date=ech, completed_date=fait, is_simulated=True))

    chemin = [ProjectStatus.INCUBATION]
    if faits >= 2:
        chemin.append(ProjectStatus.DEVELOPMENT)
    if faits >= 3:
        chemin.append(ProjectStatus.PROTOTYPE)
    if faits == n:
        chemin.append(ProjectStatus.COMPLETED)
    hist, precedent = [], ProjectStatus.SELECTED
    for k, st in enumerate(chemin):
        jour = debut if k == 0 else (p.milestones[[1, 2, 4][k - 1]].completed_date or debut)
        hist.append((precedent, st, jour))
        precedent = st
    if profil == "suspendu":
        jour = min(today, (p.milestones[faits - 1].completed_date or debut) + timedelta(days=rnd.randint(10, 40)))
        hist.append((precedent, ProjectStatus.SUSPENDED, jour))
        precedent = ProjectStatus.SUSPENDED
    p.status = precedent.value
    p.progress_pct = 100 if precedent == ProjectStatus.COMPLETED else min(95, faits * 20 + rnd.randint(0, 15))
    if profil == "retard" and rnd.random() < 0.3:
        p.deadline = fin + timedelta(days=rnd.randint(30, 90))  # date limite repoussée, mais jalons en retard
    return hist


def _financements(db, rnd, p: Project, debut: date, fin: date, today: date, partenaires, ancienne: bool) -> None:
    for _ in range(rnd.choices([0, 1, 2, 3], [0.15, 0.4, 0.3, 0.15])[0]):
        source = rnd.choices(["Subvention", "Prêt d'honneur", "Prix de concours", "Investisseur", "Fonds propres",
                              "Partenaire"], [0.3, 0.15, 0.15, 0.1, 0.1, 0.2])[0]
        partenaire = rnd.choice([x for x in partenaires if x.type == "Financier"]) if source in (
            "Subvention", "Partenaire", "Investisseur") else None
        demande = int(round(p.planned_budget * rnd.uniform(0.2, 0.7), -4)) or 500_000
        jour = min(today - timedelta(days=5), debut + timedelta(days=rnd.randint(15, 200)))
        delai = rnd.randint(20, 75)
        decide = jour + timedelta(days=delai) <= today
        tirage = rnd.random()
        if not decide:
            st, accorde, recu, date_acc = "Demandé", 0, 0, None
        elif tirage < 0.22:
            st, accorde, recu, date_acc = "Refusé", 0, 0, None
        else:
            accorde = int(round(demande * rnd.uniform(0.6, 1.0), -4))
            date_acc = jour + timedelta(days=delai)
            t2 = rnd.random()
            if ancienne or t2 < 0.45:
                st, recu = "Reçu", accorde
            elif t2 < 0.8:
                st, recu = "Partiellement reçu", int(round(accorde * rnd.uniform(0.3, 0.8), -4))
            else:
                st, recu = "Accordé", 0
        db.add(Funding(project_id=p.id, partner_id=partenaire.id if partenaire else None, source_type=source,
                       amount_requested=demande, amount_granted=accorde, amount_received=recu, request_date=jour,
                       grant_date=date_acc, status=st, is_simulated=True, notes="Financement simulé."))


# ------------------------------------------------------------------ purge
def purge_simulated(db: Session) -> dict:
    """Supprime toutes les données simulées (les comptes, domaines et paramètres sont conservés)."""
    compte = {}
    ids = list(db.scalars(select(Project.id).where(Project.is_simulated.is_(True))))
    compte["projets"] = len(ids)
    if ids:
        db.execute(delete(Alert).where(Alert.project_id.in_(ids)))
    db.execute(delete(Objective).where(Objective.is_simulated.is_(True)))
    for model in (Funding, Milestone):
        db.execute(delete(model).where(model.is_simulated.is_(True)))
    if ids:
        db.execute(delete(ProjectStatusHistory).where(ProjectStatusHistory.project_id.in_(ids)))
    db.execute(delete(Project).where(Project.is_simulated.is_(True)))
    db.execute(delete(Evaluation).where(Evaluation.is_simulated.is_(True)))
    db.execute(delete(Application).where(Application.is_simulated.is_(True)))
    for model in (ProjectLeader, Activity, Partner, Responsable):
        db.execute(delete(model).where(model.is_simulated.is_(True)))
    # Cohortes simulées : supprimées seulement si aucune donnée réelle ne s'y rattache
    for c in db.scalars(select(Cohort).where(Cohort.is_simulated.is_(True))).all():
        if db.scalar(select(Application.id).where(Application.cohort_id == c.id).limit(1)) is None:
            db.delete(c)
    return compte


if __name__ == "__main__":
    from app.database import SessionLocal

    with SessionLocal() as s:
        if "--reset" in sys.argv:
            print("Purge des données simulées :", purge_simulated(s))
            s.commit()
        ensure_reference_data(s)
        create_demo_accounts(s)
        print("Données simulées créées." if seed_simulated(s) else "La base contient déjà des projets : rien à faire.")
