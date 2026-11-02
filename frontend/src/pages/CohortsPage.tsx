/** Module 5 – Gestion des cohortes : liste, création, modification, comparaison, détail. */
import { Eye, Pencil, Plus } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Cohort, CohortStats, Kpi } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { CohortsBars, RatesLine, StatusDonut } from "../components/charts";
import { useData } from "../components/DataContext";
import KpiCard from "../components/KpiCard";
import { Card, ErrorBox, Field, Modal, ProgressBar, Spinner, StatusBadge, useToast } from "../components/ui";
import { fmtDate, fmtFCFA, fmtPct, fmtTaux, peut } from "../lib/format";
import { errMsg, useApi } from "../lib/hooks";

interface Detail {
  cohort: Cohort; kpis: Kpi[]; by_status: { status: string; count: number }[];
  projects: { id: number; name: string; leader: string; domain: string; status: string; progress_pct: number; is_delayed: boolean }[];
  activities: { id: number; title: string; type: string; date: string; participants: number }[];
}

export default function CohortsPage() {
  const { user } = useAuth();
  const { cohorts, reloadRefs } = useData();
  const toast = useToast();
  const [choix, setChoix] = useState<number[]>([]);
  const comp = useApi(() => api.get<CohortStats[]>("/cohorts/comparison", { cohort_id: choix }), [choix.join(",")]);
  const [detailId, setDetailId] = useState<number | null>(null);
  const detail = useApi(() => (detailId ? api.get<Detail>(`/cohorts/${detailId}`) : Promise.resolve(null)), [detailId]);
  const [form, setForm] = useState<Cohort | "new" | null>(null);
  const [f, setF] = useState({ name: "", year: String(new Date().getFullYear() + 1), start_date: "", end_date: "", description: "" });
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (form && form !== "new") setF({ name: form.name, year: String(form.year), start_date: form.start_date, end_date: form.end_date, description: form.description ?? "" });
    if (form === "new") setF({ name: "", year: String(new Date().getFullYear() + 1), start_date: "", end_date: "", description: "" });
    setErr(null);
  }, [form]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!f.name.trim() || !f.start_date || !f.end_date) return setErr("Nom, date de début et date de fin sont obligatoires.");
    if (f.end_date <= f.start_date) return setErr("La date de fin doit être postérieure à la date de début.");
    try {
      const body = { ...f, year: Number(f.year), description: f.description || null };
      if (form === "new") await api.post("/cohorts", body); else if (form) await api.put(`/cohorts/${form.id}`, body);
      toast("succes", "Cohorte enregistrée.");
      setForm(null);
      reloadRefs();
      comp.reload();
    } catch (x) { setErr(errMsg(x)); }
  };

  const toggle = (id: number) => setChoix(choix.includes(id) ? choix.filter((x) => x !== id) : [...choix, id]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><h1 className="titre-page">Cohortes</h1><p className="text-sm text-muted">Promotions accompagnées par l'incubateur et comparaison de leurs performances.</p></div>
        {peut(user?.role, "modifier") && <button className="btn-principal" onClick={() => setForm("new")}><Plus className="size-4" /> Nouvelle cohorte</button>}
      </div>

      <Card title="Comparer des cohortes" subtitle="Cochez les cohortes à comparer (toutes si aucune)">
        <div className="mb-4 flex flex-wrap gap-2">
          {cohorts.slice().sort((a, b) => a.year - b.year).map((c) => (
            <label key={c.id} className={`btn-secondaire cursor-pointer !py-1 ${choix.includes(c.id) ? "!border-brun !bg-beige-pale" : ""}`}>
              <input type="checkbox" className="sr-only" checked={choix.includes(c.id)} onChange={() => toggle(c.id)} />{c.name}
            </label>
          ))}
        </div>
        {comp.error ? <ErrorBox message={comp.error} /> : !comp.data ? <Spinner /> : (
          <>
            <div className="-mx-4 overflow-x-auto">
              <table className="tableau min-w-[900px]">
                <thead><tr><th>Cohorte</th><th className="text-right">Projets</th><th className="text-right">Terminés</th><th className="text-right">En retard</th>
                  <th className="text-right">Taux de réussite</th><th className="text-right">Taux de sélection</th><th className="text-right">Progression moy.</th><th className="text-right">Financement moyen</th><th /></tr></thead>
                <tbody>{comp.data.map((c) => (
                  <tr key={c.cohort_id}>
                    <td className="font-medium text-profond">{c.cohort}</td>
                    <td className="text-right tabular-nums">{c.total_projects}<span className="text-xs text-muted"> / {c.applications} cand.</span></td>
                    <td className="text-right tabular-nums">{c.completed}</td>
                    <td className={`text-right tabular-nums ${c.delayed ? "font-semibold text-alerte" : ""}`}>{c.delayed}</td>
                    <td className="text-right tabular-nums">{fmtTaux(c.success_rate)}</td>
                    <td className="text-right tabular-nums">{fmtTaux(c.selection_rate)}</td>
                    <td className="text-right tabular-nums">{fmtPct(c.avg_progress)}</td>
                    <td className="text-right tabular-nums">{fmtFCFA(c.avg_funding)}</td>
                    <td className="whitespace-nowrap text-right">
                      <button className="btn-lien mr-3" onClick={() => setDetailId(c.cohort_id)}><Eye className="inline size-4" /> Détail</button>
                      {peut(user?.role, "modifier") && <button className="btn-lien" onClick={() => setForm(cohorts.find((x) => x.id === c.cohort_id) ?? null)}><Pencil className="inline size-4" /></button>}
                    </td>
                  </tr>))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-xs text-muted">Taux de réussite = projets terminés ÷ projets incubés de la cohorte. Financement moyen = montants accordés ÷ projets financés.</p>
            <div className="mt-4 grid gap-5 xl:grid-cols-2"><CohortsBars data={comp.data} /><RatesLine data={comp.data} /></div>
          </>
        )}
      </Card>

      <Modal open={detailId !== null} title={detail.data?.cohort.name ?? "Cohorte"} onClose={() => setDetailId(null)} wide>
        {!detail.data ? <Spinner /> : (
          <div className="space-y-4">
            <p className="text-sm text-muted">Du {fmtDate(detail.data.cohort.start_date)} au {fmtDate(detail.data.cohort.end_date)}{detail.data.cohort.description && ` · ${detail.data.cohort.description}`}</p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {detail.data.kpis.filter((k) => ["total_projects", "completed", "delayed", "completion_rate", "avg_progress", "avg_funding", "selection_rate", "funding_received"].includes(k.key))
                .map((k) => <KpiCard key={k.key} kpi={k} accent={k.key === "delayed" && (k.value ?? 0) > 0} />)}
            </div>
            <StatusDonut data={detail.data.by_status} />
            <div className="-mx-5 overflow-x-auto">
              <table className="tableau min-w-[560px]">
                <thead><tr><th>Projet</th><th>Statut</th><th>Progression</th></tr></thead>
                <tbody>{detail.data.projects.filter((p) => p.status !== "Non retenu").map((p) => (
                  <tr key={p.id}><td><Link className="font-medium text-profond hover:underline" to={`/projets/${p.id}`}>{p.name}</Link><span className="block text-xs text-muted">{p.leader} · {p.domain}</span></td>
                    <td><StatusBadge status={p.status} /></td><td><ProgressBar value={p.progress_pct} late={p.is_delayed} /></td></tr>))}
                </tbody>
              </table>
            </div>
            {detail.data.activities.length > 0 && (
              <div><h3 className="mb-2 text-sm font-semibold text-profond">Activités de la cohorte</h3>
                <ul className="space-y-1 text-sm">{detail.data.activities.map((a) => <li key={a.id}>{fmtDate(a.date)} · <b>{a.type}</b> – {a.title} ({a.participants} participants)</li>)}</ul></div>
            )}
          </div>
        )}
      </Modal>

      <Modal open={form !== null} title={form === "new" ? "Nouvelle cohorte" : "Modifier la cohorte"} onClose={() => setForm(null)}
        footer={<><button className="btn-secondaire" onClick={() => setForm(null)}>Annuler</button><button className="btn-principal" type="submit" form="form-coh">Enregistrer</button></>}>
        <form id="form-coh" onSubmit={save} noValidate className="grid gap-3 sm:grid-cols-2">
          <Field label="Nom *" htmlFor="c-n"><input id="c-n" className="champ" maxLength={60} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Cohorte 2027" /></Field>
          <Field label="Année *" htmlFor="c-a"><input id="c-a" type="number" className="champ" value={f.year} onChange={(e) => setF({ ...f, year: e.target.value })} /></Field>
          <Field label="Date de début *" htmlFor="c-d"><input id="c-d" type="date" className="champ" value={f.start_date} onChange={(e) => setF({ ...f, start_date: e.target.value })} /></Field>
          <Field label="Date de fin *" htmlFor="c-f"><input id="c-f" type="date" className="champ" value={f.end_date} onChange={(e) => setF({ ...f, end_date: e.target.value })} /></Field>
          <div className="sm:col-span-2"><Field label="Description" htmlFor="c-de"><textarea id="c-de" className="champ" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field></div>
          {err && <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-900 sm:col-span-2">{err}</p>}
        </form>
      </Modal>
    </div>
  );
}
