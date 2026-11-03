/** Module 7 (V2) – Suivi des objectifs : cible, réalisé, % de réalisation, écart, statut. */
import { Pencil, Plus, Target, Trash2 } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { ObjectiveItem } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useData } from "../components/DataContext";
import { Card, ConfirmDialog, Empty, ErrorBox, Field, InfoTip, Modal, Spinner, useToast } from "../components/ui";
import { fmtDate, fmtFCFA, fmtNombre, fmtTaux, peut } from "../lib/format";
import { errMsg, useApi } from "../lib/hooks";

interface Reponse { items: ObjectiveItem[]; indicators: { key: string; label: string; unit: string; definition: string }[] }
const STATUT: Record<string, string> = {
  Atteint: "bg-emerald-50 text-emerald-800", "En bonne voie": "bg-blue-50 text-blue-800", "En retard": "bg-amber-50 text-amber-900",
  "Non atteint": "bg-red-50 text-red-800", "En dessous de la cible": "bg-orange-50 text-orange-800", "Non calculable": "bg-gris text-muted",
};
const an = new Date().getFullYear();
const VIDE = { label: "", indicator: "projets_termines", target_value: "", start_date: `${an}-01-01`, end_date: `${an}-12-31`, cohort_id: "", domain_id: "" };

function valeur(o: ObjectiveItem, v: number | null) {
  if (v === null) return "—";
  return o.unit === "amount" ? fmtFCFA(v) : o.unit === "percent" ? `${v.toLocaleString("fr-FR")} %` : fmtNombre(v);
}

export default function ObjectivesPage() {
  const { user } = useAuth();
  const { cohorts, domains } = useData();
  const toast = useToast();
  const edit = peut(user?.role, "modifier");
  const r = useApi(() => api.get<Reponse>("/objectives"), []);
  const [form, setForm] = useState<ObjectiveItem | "new" | null>(null);
  const [f, setF] = useState(VIDE);
  const [err, setErr] = useState<string | null>(null);
  const [suppr, setSuppr] = useState<ObjectiveItem | null>(null);

  useEffect(() => {
    setErr(null);
    if (form === "new") setF(VIDE);
    else if (form) setF({ label: form.label, indicator: form.indicator, target_value: String(form.target), start_date: form.start_date,
      end_date: form.end_date, cohort_id: form.cohort_id ? String(form.cohort_id) : "", domain_id: form.domain_id ? String(form.domain_id) : "" });
  }, [form]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    const cible = Number(f.target_value);
    if (!f.label.trim() || !cible || cible <= 0) return setErr("Un intitulé et une cible strictement positive sont obligatoires.");
    if (f.end_date <= f.start_date) return setErr("La fin de la période doit être postérieure au début.");
    const corps = { ...f, target_value: cible, cohort_id: f.cohort_id ? Number(f.cohort_id) : null, domain_id: f.domain_id ? Number(f.domain_id) : null };
    try {
      if (form === "new") await api.post("/objectives", corps); else if (form) await api.put(`/objectives/${form.id}`, corps);
      toast("succes", "Objectif enregistré.");
      setForm(null);
      r.reload();
    } catch (x) { setErr(errMsg(x)); }
  };
  const indic = r.data?.indicators.find((i) => i.key === f.indicator);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><h1 className="titre-page flex items-center gap-2"><Target className="size-6 text-beige-fonce" /> Suivi des objectifs</h1>
          <p className="text-sm text-muted">Les valeurs réalisées sont mesurées automatiquement à partir des données, sur la période de chaque objectif.</p></div>
        {edit && <button className="btn-principal" onClick={() => setForm("new")}><Plus className="size-4" /> Nouvel objectif</button>}
      </div>
      {r.error ? <ErrorBox message={r.error} onRetry={r.reload} /> : !r.data ? <Spinner /> : r.data.items.length === 0 ? (
        <div className="carte"><Empty title="Aucun objectif défini">{edit ? "Créez un premier objectif." : "Les coordonnateurs peuvent définir des objectifs."}</Empty></div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {r.data.items.map((o) => {
            const taux = o.realization_rate ?? 0;
            return (
              <Card key={o.id} title={<span className="flex items-center gap-1">{o.label} <InfoTip text={o.definition} label={o.indicator_label} /></span>}
                subtitle={`${fmtDate(o.start_date)} → ${fmtDate(o.end_date)}${o.cohort ? ` · ${o.cohort}` : ""}${o.domain ? ` · ${o.domain}` : ""}`}
                actions={edit ? <div className="flex gap-1">
                  <button className="rounded p-1 hover:bg-gris" aria-label="Modifier" onClick={() => setForm(o)}><Pencil className="size-4" /></button>
                  <button className="rounded p-1 text-danger hover:bg-red-50" aria-label="Supprimer" onClick={() => setSuppr(o)}><Trash2 className="size-4" /></button></div> : undefined}>
                <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                  <span className={`${o.unit === "amount" ? "text-xl" : "text-2xl"} font-bold tabular-nums text-profond`}>{valeur(o, o.current)}</span>
                  <span className="text-right text-sm text-muted">cible {valeur(o, o.target)}</span>
                </div>
                <div className="relative mt-2 h-2.5 overflow-hidden rounded-full bg-ligne" aria-label={`Réalisation ${fmtTaux(o.realization_rate)}`}>
                  <div className={`h-full rounded-full ${taux >= 1 ? "bg-emerald-500" : "bg-brun"}`} style={{ width: `${Math.min(100, taux * 100)}%` }} />
                  {o.unit !== "percent" && <span className="absolute top-0 h-full w-0.5 bg-beige" style={{ left: `${o.elapsed_rate * 100}%` }} title="Part de la période écoulée" />}
                </div>
                <dl className="mt-3 grid grid-cols-3 gap-2 text-xs">
                  <div><dt className="text-muted">Réalisation</dt><dd className="font-semibold">{fmtTaux(o.realization_rate)}</dd></div>
                  <div><dt className="text-muted">Écart</dt><dd className={`font-semibold ${(o.gap ?? 0) < 0 ? "text-alerte" : "text-emerald-800"}`}>{o.gap === null ? "—" : (o.gap > 0 ? "+" : "") + valeur(o, o.gap)}</dd></div>
                  <div><dt className="text-muted">Statut</dt><dd><span className={`rounded px-1.5 py-0.5 font-medium ${STATUT[o.status] ?? ""}`}>{o.status}</span></dd></div>
                </dl>
                {o.unit !== "percent" && <p className="mt-2 text-[11px] text-muted">Repère beige : {fmtTaux(o.elapsed_rate)} de la période écoulée.</p>}
              </Card>
            );
          })}
        </div>
      )}

      <Modal open={form !== null} title={form === "new" ? "Nouvel objectif" : "Modifier l'objectif"} onClose={() => setForm(null)}
        footer={<><button className="btn-secondaire" onClick={() => setForm(null)}>Annuler</button><button className="btn-principal" type="submit" form="form-obj">Enregistrer</button></>}>
        <form id="form-obj" onSubmit={save} noValidate className="grid gap-3 sm:grid-cols-2">
          <div className="sm:col-span-2"><Field label="Intitulé *" htmlFor="o-l"><input id="o-l" className="champ" maxLength={150} value={f.label} onChange={(e) => setF({ ...f, label: e.target.value })} /></Field></div>
          <Field label="Indicateur *" htmlFor="o-i" hint={indic?.definition}>
            <select id="o-i" className="champ" value={f.indicator} onChange={(e) => setF({ ...f, indicator: e.target.value })}>
              {r.data?.indicators.map((i) => <option key={i.key} value={i.key}>{i.label}</option>)}
            </select></Field>
          <Field label={`Cible *${indic?.unit === "amount" ? " (FCFA)" : indic?.unit === "percent" ? " (%)" : ""}`} htmlFor="o-c">
            <input id="o-c" className="champ" inputMode="decimal" value={f.target_value} onChange={(e) => setF({ ...f, target_value: e.target.value })} /></Field>
          <Field label="Début *" htmlFor="o-d"><input id="o-d" type="date" className="champ" value={f.start_date} onChange={(e) => setF({ ...f, start_date: e.target.value })} /></Field>
          <Field label="Fin *" htmlFor="o-f"><input id="o-f" type="date" className="champ" value={f.end_date} onChange={(e) => setF({ ...f, end_date: e.target.value })} /></Field>
          <Field label="Cohorte (facultatif)" htmlFor="o-co"><select id="o-co" className="champ" value={f.cohort_id} onChange={(e) => setF({ ...f, cohort_id: e.target.value })}>
            <option value="">Toutes</option>{cohorts.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
          <Field label="Domaine (facultatif)" htmlFor="o-do"><select id="o-do" className="champ" value={f.domain_id} onChange={(e) => setF({ ...f, domain_id: e.target.value })}>
            <option value="">Tous</option>{domains.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></Field>
          {err && <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-900 sm:col-span-2">{err}</p>}
        </form>
      </Modal>
      <ConfirmDialog open={!!suppr} title="Supprimer l'objectif" danger confirmLabel="Supprimer" onCancel={() => setSuppr(null)}
        message={<>Supprimer l'objectif « {suppr?.label} » ?</>}
        onConfirm={async () => { try { await api.del(`/objectives/${suppr!.id}`); toast("succes", "Objectif supprimé."); setSuppr(null); r.reload(); } catch (e) { toast("erreur", errMsg(e)); } }} />
    </div>
  );
}
