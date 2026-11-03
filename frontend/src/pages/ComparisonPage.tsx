/** Module 3 (V2) – Comparaison des performances (mêmes définitions, même périmètre ; seule la dimension change). */
import { GitCompareArrows, Plus, Search, Trash2, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { CompareResult, Page, ProjectItem } from "../api/types";
import { CompareBars } from "../components/charts";
import { useData } from "../components/DataContext";
import FiltersBar from "../components/FiltersBar";
import { Card, Empty, ErrorBox, InfoTip, Spinner } from "../components/ui";
import { fmtFCFA, fmtKpi, fmtNombre, fmtPct, fmtTaux } from "../lib/format";
import { errMsg, useDebounced } from "../lib/hooks";

type Dim = "domain" | "cohort" | "responsible" | "project" | "period";
const DIMENSIONS: { k: Dim; l: string }[] = [
  { k: "domain", l: "Domaines d'innovation" }, { k: "cohort", l: "Cohortes" }, { k: "responsible", l: "Responsables de suivi" },
  { k: "project", l: "Projets" }, { k: "period", l: "Périodes" },
];
const an = new Date().getFullYear();

export default function ComparisonPage() {
  const { domains, cohorts, responsables, body } = useData();
  const [dim, setDim] = useState<Dim>("domain");
  const [ids, setIds] = useState<number[]>([]);
  const [periodes, setPeriodes] = useState([
    { label: `${an - 1}`, start_date: `${an - 1}-01-01`, end_date: `${an - 1}-12-31` },
    { label: `${an}`, start_date: `${an}-01-01`, end_date: `${an}-12-31` },
  ]);
  const [q, setQ] = useState("");
  const dq = useDebounced(q);
  const [trouves, setTrouves] = useState<ProjectItem[]>([]);
  const [choisis, setChoisis] = useState<ProjectItem[]>([]);
  const [res, setRes] = useState<CompareResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [occupe, setOccupe] = useState(false);

  useEffect(() => { setIds([]); setRes(null); setErr(null); }, [dim]);
  useEffect(() => {
    if (dim !== "project") return;
    api.get<Page<ProjectItem>>("/projects", { q: dq, page_size: 10, sort: "name", order: "asc" })
      .then((r) => setTrouves(r.items.filter((p) => !["En attente", "En évaluation", "Non retenu"].includes(p.status)))).catch(() => setTrouves([]));
  }, [dq, dim]);

  const options = dim === "domain" ? domains.map((d) => ({ id: d.id, l: d.name }))
    : dim === "cohort" ? cohorts.slice().sort((a, b) => a.year - b.year).map((c) => ({ id: c.id, l: c.name }))
      : dim === "responsible" ? responsables.map((r) => ({ id: r.id, l: r.full_name })) : [];
  const toggle = (id: number) => setIds(ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]);
  const nb = dim === "project" ? choisis.length : dim === "period" ? periodes.length : ids.length;

  const comparer = async () => {
    setOccupe(true); setErr(null);
    try {
      setRes(await api.post<CompareResult>("/compare", {
        dimension: dim, filters: body, ids: dim === "project" ? choisis.map((p) => p.id) : ids,
        periods: dim === "period" ? periodes : [],
      }));
    } catch (e) { setErr(errMsg(e)); setRes(null); } finally { setOccupe(false); }
  };

  const series = res?.items.map((i) => i.label) ?? [];
  const lignesTaux = res && res.dimension !== "project" ? [
    { indicateur: "Taux d'achèvement", ...Object.fromEntries(res.items.map((i) => [i.label, i.completion_rate == null ? null : Math.round(i.completion_rate * 1000) / 10])) },
    { indicateur: "Progression moyenne", ...Object.fromEntries(res.items.map((i) => [i.label, i.avg_progress ?? null])) },
    { indicateur: "Taux de retard", ...Object.fromEntries(res.items.map((i) => [i.label, i.delay_rate == null ? null : Math.round(i.delay_rate * 1000) / 10])) },
  ] : [];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="titre-page flex items-center gap-2"><GitCompareArrows className="size-6 text-beige-fonce" /> Comparaison des performances</h1>
        <p className="text-sm text-muted">Les éléments sont comparés avec les mêmes définitions et sur le même périmètre (filtres communs ci-dessous).</p>
      </div>
      <FiltersBar />

      <Card title="1. Que comparer ?">
        <div className="mb-4 flex flex-wrap gap-2" role="radiogroup" aria-label="Dimension">
          {DIMENSIONS.map((d) => (
            <button key={d.k} role="radio" aria-checked={dim === d.k} className={`btn-secondaire !py-1.5 ${dim === d.k ? "!border-brun !bg-beige-pale font-semibold" : ""}`}
              onClick={() => setDim(d.k)}>{d.l}</button>
          ))}
        </div>
        {options.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {options.map((o) => (
              <label key={o.id} className={`cursor-pointer rounded-full border px-3 py-1 text-sm ${ids.includes(o.id) ? "border-brun bg-beige-pale text-profond" : "border-ligne hover:bg-gris"}`}>
                <input type="checkbox" className="sr-only" checked={ids.includes(o.id)} onChange={() => toggle(o.id)} />{o.l}
              </label>
            ))}
          </div>
        )}
        {dim === "project" && (
          <div className="grid gap-4 lg:grid-cols-2">
            <div>
              <div className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
                <input className="champ pl-9" placeholder="Rechercher un projet incubé…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Rechercher un projet" /></div>
              <ul className="mt-2 max-h-56 divide-y divide-ligne overflow-y-auto rounded-md border border-ligne">
                {trouves.map((p) => (
                  <li key={p.id} className="flex items-center justify-between gap-2 px-3 py-1.5 text-sm">
                    <span className="truncate">{p.name}</span>
                    <button className="btn-lien shrink-0" disabled={choisis.some((x) => x.id === p.id) || choisis.length >= 6}
                      onClick={() => setChoisis([...choisis, p])}><Plus className="inline size-4" /> Ajouter</button>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="etiquette">Projets choisis ({choisis.length}/6)</p>
              <ul className="space-y-1">{choisis.map((p) => (
                <li key={p.id} className="flex items-center justify-between rounded-md bg-gris px-3 py-1.5 text-sm">
                  <span className="truncate">{p.name}</span>
                  <button aria-label="Retirer" onClick={() => setChoisis(choisis.filter((x) => x.id !== p.id))}><Trash2 className="size-4 text-danger" /></button>
                </li>))}
              </ul>
            </div>
          </div>
        )}
        {dim === "period" && (
          <div className="space-y-2">
            {periodes.map((p, i) => (
              <div key={i} className="grid grid-cols-[1fr_1fr_1fr_auto] items-end gap-2">
                <input className="champ" aria-label="Libellé" value={p.label} onChange={(e) => setPeriodes(periodes.map((x, j) => j === i ? { ...x, label: e.target.value } : x))} />
                <input type="date" className="champ" aria-label="Début" value={p.start_date} onChange={(e) => setPeriodes(periodes.map((x, j) => j === i ? { ...x, start_date: e.target.value } : x))} />
                <input type="date" className="champ" aria-label="Fin" value={p.end_date} onChange={(e) => setPeriodes(periodes.map((x, j) => j === i ? { ...x, end_date: e.target.value } : x))} />
                <button className="rounded p-2 text-danger hover:bg-red-50 disabled:opacity-30" disabled={periodes.length <= 2} aria-label="Retirer la période"
                  onClick={() => setPeriodes(periodes.filter((_, j) => j !== i))}><Trash2 className="size-4" /></button>
              </div>
            ))}
            <button className="btn-lien" disabled={periodes.length >= 4} onClick={() => setPeriodes([...periodes, { label: "Période", start_date: `${an}-01-01`, end_date: `${an}-06-30` }])}>
              <Plus className="inline size-4" /> Ajouter une période</button>
            <p className="text-xs text-muted">La période porte sur la date de dépôt des candidatures. Comparez des périodes de même durée pour comparer des volumes.</p>
          </div>
        )}
        <div className="mt-4 flex items-center gap-3">
          <button className="btn-principal" onClick={comparer} disabled={occupe || nb < 2}><GitCompareArrows className="size-4" /> {occupe ? "Calcul…" : "Comparer"}</button>
          {nb < 2 && <span className="text-xs text-muted">Choisissez au moins deux éléments.</span>}
        </div>
      </Card>

      {err && <ErrorBox message={err} />}
      {occupe && <Spinner />}
      {res && (
        <Card title="2. Résultats" subtitle={`Périmètre commun : ${res.perimetre}`}>
          {res.warnings.map((w) => <p key={w} className="mb-2 flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-900"><TriangleAlert className="size-4 shrink-0" />{w}</p>)}
          {res.items.length === 0 ? <Empty title="Aucune donnée pour ces éléments" /> : res.dimension === "project" ? (
            <div className="-mx-4 overflow-x-auto">
              <table className="tableau min-w-[880px]">
                <thead><tr><th>Projet</th><th>Statut</th><th className="text-right">Progression</th><th className="text-right">Attendue</th><th className="text-right">Retard</th>
                  <th className="text-right">Financement obtenu</th><th className="text-right">Couverture budget</th><th>Prototype</th><th className="text-right">Risque</th></tr></thead>
                <tbody>{res.items.map((i) => (
                  <tr key={i.id}><td className="max-w-[240px]"><span className="line-clamp-1 font-medium">{i.label}</span><span className="text-xs text-muted">{i.domain} · {i.cohort}</span></td>
                    <td>{i.status}</td><td className="text-right tabular-nums">{fmtPct(i.progress_pct)}</td><td className="text-right tabular-nums">{fmtPct(i.expected_pct)}</td>
                    <td className="text-right tabular-nums">{i.days_late ? `${i.days_late} j` : "—"}</td><td className="text-right tabular-nums">{fmtFCFA(i.funding_granted)}</td>
                    <td className="text-right tabular-nums">{fmtTaux(i.coverage_rate)}</td><td>{i.prototype ? "Oui" : "Non"}</td>
                    <td className="text-right tabular-nums">{i.risk_score == null ? "—" : `${i.risk_score}/100 (${i.risk_level})`}</td></tr>))}
                </tbody>
              </table>
            </div>
          ) : (
            <>
              <div className="-mx-4 overflow-x-auto">
                <table className="tableau min-w-[640px]">
                  <thead><tr><th>Indicateur</th>{res.items.map((i) => <th key={i.id} className="text-right normal-case">{i.label}</th>)}</tr></thead>
                  <tbody>{Object.entries(res.metrics ?? {}).map(([k, m]) => (
                    <tr key={k}><td className="font-medium"><span className="inline-flex items-center gap-1">{m.label} <InfoTip text={m.definition} label={m.label} /></span></td>
                      {res.items.map((i) => {
                        const v = (i as unknown as Record<string, number | null>)[k];
                        const valeurs = res.items.map((x) => (x as unknown as Record<string, number | null>)[k]).filter((x): x is number => x != null);
                        const meilleur = v != null && valeurs.length > 1 && v === (k === "delay_rate" ? Math.min(...valeurs) : Math.max(...valeurs));
                        return <td key={i.id} className={`text-right tabular-nums ${meilleur ? "font-semibold text-emerald-800" : ""}`}>{fmtKpi(v ?? null, m.unit)}</td>;
                      })}</tr>))}
                    <tr><td className="text-xs text-muted">Candidatures (base du périmètre)</td>{res.items.map((i) => <td key={i.id} className="text-right text-xs tabular-nums text-muted">{fmtNombre(i.applications ?? 0)}</td>)}</tr>
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-xs text-muted">En vert : meilleure valeur de chaque ligne (la plus basse pour le taux de retard).</p>
              <div className="mt-4"><CompareBars rows={lignesTaux} series={series} /></div>
            </>
          )}
        </Card>
      )}
    </div>
  );
}
