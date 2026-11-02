/** Formulaire d'enregistrement / modification d'un financement (contrôle reçu ≤ accordé ≤ demandé). */
import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { Funding, Page, Partner, ProjectItem } from "../api/types";
import { Field, Modal, useToast } from "../components/ui";
import { todayISO } from "../lib/format";
import { errMsg, useDebounced } from "../lib/hooks";

const SOURCES = ["Subvention", "Prêt d'honneur", "Prix de concours", "Investisseur", "Fonds propres", "Partenaire"];
const STATUTS = ["Demandé", "Accordé", "Partiellement reçu", "Reçu", "Refusé"];

interface Props {
  open: boolean; onClose: () => void; onSaved: () => void; funding?: Funding | null;
  project?: { id: number; name: string } | null;
}

export default function FundingForm({ open, onClose, onSaved, funding, project }: Props) {
  const toast = useToast();
  const [partners, setPartners] = useState<Partner[]>([]);
  const [recherche, setRecherche] = useState("");
  const [projets, setProjets] = useState<ProjectItem[]>([]);
  const dq = useDebounced(recherche);
  const [f, setF] = useState({
    project_id: "", partner_id: "", source_type: "Subvention", amount_requested: "", amount_granted: "0",
    amount_received: "0", request_date: todayISO(), grant_date: "", status: "Demandé", notes: "",
  });
  const [err, setErr] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => { if (open) api.get<Partner[]>("/partners").then(setPartners).catch(() => undefined); }, [open]);
  useEffect(() => {
    if (!open || project || funding) return;
    api.get<Page<ProjectItem>>("/projects", { q: dq, page_size: 15, sort: "name", order: "asc" })
      .then((r) => setProjets(r.items.filter((p) => !["En attente", "En évaluation", "Non retenu"].includes(p.status))))
      .catch(() => setProjets([]));
  }, [dq, open, project, funding]);
  useEffect(() => {
    if (!open) return;
    setErr(null);
    if (funding) {
      setF({ project_id: String(funding.project_id), partner_id: funding.partner_id ? String(funding.partner_id) : "",
        source_type: funding.source_type, amount_requested: String(funding.amount_requested),
        amount_granted: String(funding.amount_granted), amount_received: String(funding.amount_received),
        request_date: funding.request_date, grant_date: funding.grant_date ?? "", status: funding.status, notes: funding.notes ?? "" });
    } else {
      setF((x) => ({ ...x, project_id: project ? String(project.id) : "", amount_requested: "", amount_granted: "0",
        amount_received: "0", status: "Demandé", grant_date: "", notes: "", partner_id: "" }));
    }
  }, [open, funding, project]);

  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const dem = Number(f.amount_requested || 0), acc = Number(f.amount_granted || 0), rec = Number(f.amount_received || 0);
  const reste = acc - rec;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!f.project_id) return setErr("Choisissez le projet concerné.");
    if ([dem, acc, rec].some((x) => Number.isNaN(x) || x < 0)) return setErr("Les montants doivent être des nombres positifs.");
    if (!(rec <= acc && acc <= dem)) return setErr("Les montants doivent respecter : reçu ≤ accordé ≤ demandé.");
    if (f.grant_date && f.grant_date < f.request_date) return setErr("La date d'accord ne peut pas précéder la demande.");
    setEnvoi(true);
    const body = { ...f, project_id: Number(f.project_id), partner_id: f.partner_id ? Number(f.partner_id) : null,
      amount_requested: dem, amount_granted: acc, amount_received: rec, grant_date: f.grant_date || null, notes: f.notes || null };
    try {
      if (funding) await api.put(`/fundings/${funding.id}`, body); else await api.post("/fundings", body);
      toast("succes", funding ? "Financement modifié." : "Financement enregistré.");
      onSaved();
    } catch (x) { setErr(errMsg(x)); } finally { setEnvoi(false); }
  };

  return (
    <Modal open={open} onClose={onClose} title={funding ? "Modifier le financement" : "Enregistrer un financement"} wide
      footer={<><button className="btn-secondaire" onClick={onClose}>Annuler</button>
        <button className="btn-principal" type="submit" form="form-fin" disabled={envoi}>{envoi ? "Enregistrement…" : "Enregistrer"}</button></>}>
      <form id="form-fin" onSubmit={submit} noValidate className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          {project || funding ? (
            <p className="text-sm">Projet : <b>{project?.name ?? funding?.project_name}</b></p>
          ) : (
            <Field label="Projet concerné *" htmlFor="fi-proj">
              <input className="champ mb-2" placeholder="Rechercher un projet sélectionné…" value={recherche} onChange={(e) => setRecherche(e.target.value)} aria-label="Rechercher un projet" />
              <select id="fi-proj" className="champ" value={f.project_id} onChange={set("project_id")}>
                <option value="">Choisir…</option>{projets.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.cohort})</option>)}
              </select>
            </Field>
          )}
        </div>
        <Field label="Source *" htmlFor="fi-src"><select id="fi-src" className="champ" value={f.source_type} onChange={set("source_type")}>
          {SOURCES.map((s) => <option key={s}>{s}</option>)}</select></Field>
        <Field label="Partenaire / bailleur" htmlFor="fi-par"><select id="fi-par" className="champ" value={f.partner_id} onChange={set("partner_id")}>
          <option value="">Aucun</option>{partners.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></Field>
        <Field label="Montant demandé (FCFA) *" htmlFor="fi-dem"><input id="fi-dem" className="champ" inputMode="numeric" value={f.amount_requested} onChange={set("amount_requested")} /></Field>
        <Field label="Montant accordé (FCFA)" htmlFor="fi-acc"><input id="fi-acc" className="champ" inputMode="numeric" value={f.amount_granted} onChange={set("amount_granted")} /></Field>
        <Field label="Montant reçu (FCFA)" htmlFor="fi-rec"><input id="fi-rec" className="champ" inputMode="numeric" value={f.amount_received} onChange={set("amount_received")} /></Field>
        <Field label="Statut *" htmlFor="fi-st" hint="Doit correspondre aux montants saisis."><select id="fi-st" className="champ" value={f.status} onChange={set("status")}>
          {STATUTS.map((s) => <option key={s}>{s}</option>)}</select></Field>
        <Field label="Date de la demande *" htmlFor="fi-dd"><input id="fi-dd" type="date" className="champ" max={todayISO()} value={f.request_date} onChange={set("request_date")} /></Field>
        <Field label="Date d'accord" htmlFor="fi-da"><input id="fi-da" type="date" className="champ" value={f.grant_date} onChange={set("grant_date")} /></Field>
        <div className="sm:col-span-2"><Field label="Notes" htmlFor="fi-no"><textarea id="fi-no" className="champ" maxLength={4000} value={f.notes} onChange={set("notes")} /></Field></div>
        <p className="text-sm text-muted sm:col-span-2">Reste à recevoir : <b className="text-profond">{Number.isNaN(reste) ? "—" : `${reste.toLocaleString("fr-FR")} FCFA`}</b></p>
        {err && <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-900 sm:col-span-2">{err}</p>}
      </form>
    </Modal>
  );
}
