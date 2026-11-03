/** Formulaire de création / modification d'un projet (validation côté client + côté serveur). */
import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { Leader, ProjectDetail } from "../api/types";
import { useData } from "../components/DataContext";
import { Field, Modal, useToast } from "../components/ui";
import { todayISO } from "../lib/format";
import { errMsg, useDebounced } from "../lib/hooks";

interface Props { open: boolean; onClose: () => void; onSaved: (p: ProjectDetail) => void; project?: ProjectDetail | null }

const VIDE = { name: "", description: "", domain_id: "", cohort_id: "", planned_budget: "", deadline: "", submitted_at: todayISO(), responsible_id: "" };
const PORTEUR = { first_name: "", last_name: "", gender: "", email: "", phone: "", profile: "Étudiant ISEP" };

export default function ProjectForm({ open, onClose, onSaved, project }: Props) {
  const { domains, cohorts, responsables } = useData();
  const toast = useToast();
  const [f, setF] = useState(VIDE);
  const [porteur, setPorteur] = useState(PORTEUR);
  const [modePorteur, setModePorteur] = useState<"nouveau" | "existant">("nouveau");
  const [recherche, setRecherche] = useState("");
  const [porteurs, setPorteurs] = useState<Leader[]>([]);
  const [porteurId, setPorteurId] = useState<number | null>(null);
  const [erreurs, setErreurs] = useState<Record<string, string>>({});
  const [envoi, setEnvoi] = useState(false);
  const q = useDebounced(recherche);

  useEffect(() => {
    if (!open) return;
    setErreurs({});
    if (project) {
      setF({ name: project.name, description: project.description ?? "", domain_id: String(project.domain.id),
        cohort_id: String(project.cohort.id), planned_budget: String(project.planned_budget), deadline: project.deadline ?? "",
        submitted_at: project.application.submitted_at, responsible_id: project.responsible ? String(project.responsible.id) : "" });
    } else { setF(VIDE); setPorteur(PORTEUR); setPorteurId(null); setRecherche(""); setModePorteur("nouveau"); }
  }, [open, project]);

  useEffect(() => {
    if (modePorteur !== "existant" || !open) return;
    api.get<Leader[]>("/leaders", { q }).then(setPorteurs).catch(() => setPorteurs([]));
  }, [q, modePorteur, open]);

  const valider = () => {
    const e: Record<string, string> = {};
    if (f.name.trim().length < 2) e.name = "Le nom doit contenir au moins 2 caractères.";
    if (!f.domain_id) e.domain_id = "Choisissez un domaine.";
    if (!f.cohort_id) e.cohort_id = "Choisissez une cohorte.";
    if (f.planned_budget && (Number.isNaN(Number(f.planned_budget)) || Number(f.planned_budget) < 0)) e.planned_budget = "Montant positif attendu.";
    if (f.deadline && f.submitted_at && f.deadline <= f.submitted_at) e.deadline = "La date limite doit suivre la date de dépôt.";
    if (!project) {
      if (f.submitted_at > todayISO()) e.submitted_at = "La date de dépôt ne peut pas être dans le futur.";
      if (modePorteur === "existant" && !porteurId) e.leader = "Sélectionnez un porteur.";
      if (modePorteur === "nouveau") {
        if (!porteur.first_name.trim()) e.first_name = "Prénom obligatoire.";
        if (!porteur.last_name.trim()) e.last_name = "Nom obligatoire.";
        if (porteur.email && !/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i.test(porteur.email)) e.email = "Adresse e-mail invalide.";
      }
    }
    setErreurs(e);
    return Object.keys(e).length === 0;
  };

  const submit = async (ev: FormEvent) => {
    ev.preventDefault();
    if (!valider()) return;
    setEnvoi(true);
    const commun = { name: f.name.trim(), description: f.description.trim() || null, domain_id: Number(f.domain_id),
      cohort_id: Number(f.cohort_id), planned_budget: Number(f.planned_budget || 0), deadline: f.deadline || null,
      responsible_id: f.responsible_id ? Number(f.responsible_id) : null };
    try {
      const res = project
        ? await api.put<ProjectDetail>(`/projects/${project.id}`, commun)
        : await api.post<ProjectDetail>("/projects", {
          ...commun, submitted_at: f.submitted_at,
          ...(modePorteur === "existant" ? { leader_id: porteurId } : {
            leader: { ...porteur, gender: porteur.gender || null, email: porteur.email || null, phone: porteur.phone || null },
          }),
        });
      toast("succes", project ? "Projet modifié." : "Projet créé (statut « En attente »).");
      onSaved(res);
    } catch (e) { toast("erreur", errMsg(e)); } finally { setEnvoi(false); }
  };

  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const setP = (k: keyof typeof porteur) => (e: { target: { value: string } }) => setPorteur({ ...porteur, [k]: e.target.value });

  return (
    <Modal open={open} onClose={onClose} title={project ? "Modifier le projet" : "Nouveau projet"} wide
      footer={<><button className="btn-secondaire" onClick={onClose}>Annuler</button>
        <button className="btn-principal" form="form-projet" type="submit" disabled={envoi}>{envoi ? "Enregistrement…" : "Enregistrer"}</button></>}>
      <form id="form-projet" onSubmit={submit} noValidate className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2"><Field label="Nom du projet *" htmlFor="p-nom" error={erreurs.name}>
          <input id="p-nom" className="champ" maxLength={150} value={f.name} onChange={set("name")} /></Field></div>
        <div className="sm:col-span-2"><Field label="Description" htmlFor="p-desc">
          <textarea id="p-desc" className="champ min-h-20" maxLength={4000} value={f.description} onChange={set("description")} /></Field></div>
        <Field label="Domaine d'activité *" htmlFor="p-dom" error={erreurs.domain_id}>
          <select id="p-dom" className="champ" value={f.domain_id} onChange={set("domain_id")}>
            <option value="">Choisir…</option>{domains.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select></Field>
        <Field label="Cohorte *" htmlFor="p-coh" error={erreurs.cohort_id}>
          <select id="p-coh" className="champ" value={f.cohort_id} onChange={set("cohort_id")}>
            <option value="">Choisir…</option>{cohorts.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select></Field>
        <Field label="Responsable de suivi (CIAT)" htmlFor="p-resp">
          <select id="p-resp" className="champ" value={f.responsible_id} onChange={set("responsible_id")}>
            <option value="">Non attribué</option>{responsables.filter((r) => r.is_active).map((r) => <option key={r.id} value={r.id}>{r.full_name}</option>)}
          </select></Field>
        <Field label="Budget prévisionnel (FCFA)" htmlFor="p-bud" error={erreurs.planned_budget}>
          <input id="p-bud" className="champ" inputMode="numeric" value={f.planned_budget} onChange={set("planned_budget")} placeholder="0" /></Field>
        <Field label="Date limite" htmlFor="p-dl" error={erreurs.deadline}>
          <input id="p-dl" type="date" className="champ" value={f.deadline} onChange={set("deadline")} /></Field>
        {!project && <Field label="Date de dépôt de la candidature" htmlFor="p-dep" error={erreurs.submitted_at}>
          <input id="p-dep" type="date" className="champ" max={todayISO()} value={f.submitted_at} onChange={set("submitted_at")} /></Field>}

        {!project && (
          <fieldset className="rounded-lg border border-ligne p-3 sm:col-span-2">
            <legend className="px-1 text-sm font-semibold text-profond">Porteur de projet</legend>
            <div className="mb-3 flex gap-4 text-sm">
              {(["nouveau", "existant"] as const).map((m) => (
                <label key={m} className="flex items-center gap-2"><input type="radio" checked={modePorteur === m} onChange={() => setModePorteur(m)} />
                  {m === "nouveau" ? "Nouveau porteur" : "Porteur existant"}</label>
              ))}
            </div>
            {modePorteur === "existant" ? (
              <div className="space-y-2">
                <input className="champ" placeholder="Rechercher par nom…" value={recherche} onChange={(e) => setRecherche(e.target.value)} aria-label="Rechercher un porteur" />
                <select className="champ" size={5} value={porteurId ?? ""} onChange={(e) => setPorteurId(Number(e.target.value))} aria-label="Porteurs">
                  {porteurs.map((p) => <option key={p.id} value={p.id}>{p.first_name} {p.last_name} – {p.profile}</option>)}
                </select>
                {erreurs.leader && <p className="text-xs text-danger">{erreurs.leader}</p>}
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Prénom *" htmlFor="l-pre" error={erreurs.first_name}><input id="l-pre" className="champ" maxLength={60} value={porteur.first_name} onChange={setP("first_name")} /></Field>
                <Field label="Nom *" htmlFor="l-nom" error={erreurs.last_name}><input id="l-nom" className="champ" maxLength={60} value={porteur.last_name} onChange={setP("last_name")} /></Field>
                <Field label="Genre" htmlFor="l-gen"><select id="l-gen" className="champ" value={porteur.gender} onChange={setP("gender")}>
                  <option value="">Non renseigné</option><option>Femme</option><option>Homme</option></select></Field>
                <Field label="Profil *" htmlFor="l-pro"><select id="l-pro" className="champ" value={porteur.profile} onChange={setP("profile")}>
                  <option>Étudiant ISEP</option><option>Diplômé ISEP</option><option>Externe</option></select></Field>
                <Field label="E-mail" htmlFor="l-mail" error={erreurs.email}><input id="l-mail" type="email" className="champ" value={porteur.email} onChange={setP("email")} /></Field>
                <Field label="Téléphone" htmlFor="l-tel"><input id="l-tel" className="champ" placeholder="+221 7x xxx xx xx" value={porteur.phone} onChange={setP("phone")} /></Field>
              </div>
            )}
          </fieldset>
        )}
      </form>
    </Modal>
  );
}
