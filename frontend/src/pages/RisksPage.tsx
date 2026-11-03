/** Module 6 (V2) – Analyse des risques par règles transparentes (pas une prédiction). */
import { ShieldAlert, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { RiskAnalysis } from "../api/types";
import { HBars } from "../components/charts";
import { useData } from "../components/DataContext";
import FiltersBar from "../components/FiltersBar";
import { Card, Empty, ErrorBox, Spinner, StatusBadge } from "../components/ui";
import { useApi } from "../lib/hooks";

const COULEUR = { "Élevé": "bg-red-600 text-white", "Modéré": "bg-amber-300 text-profond", "Faible": "bg-emerald-100 text-emerald-900" } as Record<string, string>;

export default function RisksPage() {
  const { params, describe } = useData();
  const nav = useNavigate();
  const [niveau, setNiveau] = useState("");
  const [ouvert, setOuvert] = useState<number | null>(null);
  const r = useApi(() => api.get<RiskAnalysis>("/risks", params), [JSON.stringify(params)]);
  const projets = (r.data?.projets ?? []).filter((p) => !niveau || p.level === niveau);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="titre-page flex items-center gap-2"><ShieldAlert className="size-6 text-alerte" /> Analyse des risques</h1>
        <p className="text-sm text-muted">{describe}</p>
      </div>
      <FiltersBar hide={["status"]} />
      {r.error ? <ErrorBox message={r.error} onRetry={r.reload} /> : !r.data ? <Spinner /> : (
        <>
          <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            <TriangleAlert className="mt-0.5 size-5 shrink-0" />
            <div><p className="font-medium">{r.data.avertissement}</p><p className="mt-1 text-xs">Méthode – {r.data.modele.nom} : {r.data.modele.methode}</p></div>
          </div>
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
            <Card title="Répartition par niveau de risque">
              <div className="grid grid-cols-3 gap-2">
                {(["Élevé", "Modéré", "Faible"] as const).map((n) => (
                  <button key={n} onClick={() => setNiveau(niveau === n ? "" : n)} aria-pressed={niveau === n}
                    className={`rounded-lg border p-3 text-left ${niveau === n ? "border-brun bg-beige-pale" : "border-ligne hover:bg-gris"}`}>
                    <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${COULEUR[n]}`}>{n}</span>
                    <span className="mt-2 block text-2xl font-bold tabular-nums text-profond">{r.data!.par_niveau[n] ?? 0}</span>
                    <span className="text-xs text-muted">projet(s)</span>
                  </button>
                ))}
              </div>
              <p className="mt-3 text-xs text-muted">{r.data.total} projets actifs ou suspendus évalués. Cliquez sur un niveau pour filtrer la liste.</p>
            </Card>
            <Card title="Facteurs de risque les plus fréquents">
              <HBars data={r.data.facteurs_frequents} labelKey="facteur" valueKey="projets" unit="projets" />
            </Card>
          </div>
          <Card title={`Projets évalués${niveau ? ` – niveau ${niveau}` : ""} (${projets.length})`} subtitle="Du score le plus élevé au plus faible ; chaque point est expliqué">
            {projets.length === 0 ? <Empty title="Aucun projet à ce niveau de risque" /> : (
              <ul className="divide-y divide-ligne">
                {projets.map((p) => (
                  <li key={p.project_id} className="py-2.5">
                    <div className="flex flex-wrap items-center gap-3">
                      <span className={`w-20 rounded px-2 py-1 text-center text-xs font-semibold ${COULEUR[p.level]}`}>{p.score}/100</span>
                      <button className="min-w-0 flex-1 text-left" onClick={() => setOuvert(ouvert === p.project_id ? null : p.project_id)} aria-expanded={ouvert === p.project_id}>
                        <span className="block truncate text-sm font-medium text-profond">{p.name}</span>
                        <span className="text-xs text-muted">{p.domain} · {p.cohort}{p.responsible ? ` · suivi : ${p.responsible}` : ""} · progression {p.progress_pct} %
                          {p.expected_pct !== null && ` (attendue ${p.expected_pct.toLocaleString("fr-FR")} %)`}</span>
                      </button>
                      <StatusBadge status={p.status} />
                      <button className="btn-lien" onClick={() => nav(`/projets/${p.project_id}`)}>Fiche</button>
                    </div>
                    {ouvert === p.project_id && (
                      <ul className="mt-2 space-y-1 rounded-md bg-gris p-3 text-sm">
                        {p.factors.length === 0 ? <li className="text-muted">Aucun facteur de risque détecté.</li> : p.factors.map((f) => (
                          <li key={f.code}><b className="text-alerte">+{f.points}</b> {f.libelle} – <span className="text-muted">{f.detail}</span></li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
