/** Module 1 (V2) – Tableau de bord stratégique : 10 indicateurs, alertes, risques, 6 graphiques. */
import {
  Activity, AlarmClock, BellRing, ClipboardList, FlaskConical, FolderKanban, Gauge, Percent, Rocket, ShieldAlert, Target, Wallet,
} from "lucide-react";
import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { AlertSummary, ChartsV2, DelayedProject, Kpi, RiskAnalysis } from "../api/types";
import { DomainPerformance, FundingArea, HBars, ProgressBars, ProjectsMonthlyLine, StatusDonut } from "../components/charts";
import { useData } from "../components/DataContext";
import FiltersBar from "../components/FiltersBar";
import KpiCard from "../components/KpiCard";
import { Card, Empty, ErrorBox, ProgressBar, Spinner, StatusBadge } from "../components/ui";
import { useApi } from "../lib/hooks";

const ICONES: Record<string, ReactNode> = {
  total_projects: <FolderKanban className="size-4" />, active: <Activity className="size-4" />,
  completed: <Rocket className="size-4" />, delayed: <AlarmClock className="size-4" />,
  applications: <ClipboardList className="size-4" />, selection_rate: <Percent className="size-4" />,
  completion_rate: <Target className="size-4" />, avg_progress: <Gauge className="size-4" />,
  funding_received: <Wallet className="size-4" />, prototypes: <FlaskConical className="size-4" />,
};

/** Clic sur un indicateur → liste des projets correspondants. */
const LIENS: Record<string, string> = {
  completed: "/projets?status=Terminé", prototypes: "/projets?status=Prototype réalisé", delayed: "/projets?delayed=1",
  total_projects: "/projets", applications: "/projets",
};
const NIVEAUX_ALERTES = [
  { n: "Critique", c: "bg-red-600" }, { n: "Élevé", c: "bg-orange-500" }, { n: "Moyen", c: "bg-amber-400" },
  { n: "Information", c: "bg-stone-400" },
];

export default function DashboardPage() {
  const { params, describe, chips } = useData();
  const nav = useNavigate();
  const key = JSON.stringify(params);
  const kpis = useApi(() => api.get<{ dashboard: Kpi[]; all: Kpi[]; perimetre: string }>("/analytics/kpis", params), [key]);
  const charts = useApi(() => api.get<ChartsV2>("/analytics/charts", params), [key]);
  const retards = useApi(() => api.get<{ total: number; items: DelayedProject[] }>("/analytics/delayed", { ...params, limit: 5 }), [key]);
  const alertes = useApi(() => api.get<AlertSummary>("/alerts/summary"), []);
  const risques = useApi(() => api.get<RiskAnalysis>("/risks", params), [key]);
  const all = Object.fromEntries((kpis.data?.all ?? []).map((k) => [k.key, k]));
  const vide = kpis.data && (all.applications?.value ?? 0) === 0;
  const c = charts.data;
  const resumeAlertes = alertes.data;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="titre-page">Tableau de bord stratégique</h1>
        <p className="text-sm text-muted">Vue d'ensemble des activités du CIAT · {describe}</p>
      </div>
      <FiltersBar />

      {kpis.error ? <ErrorBox message={kpis.error} onRetry={kpis.reload} /> : !kpis.data ? <Spinner /> : vide ? (
        <div className="carte"><Empty title="Aucune donnée ne correspond aux filtres">Élargissez la période ou retirez un filtre actif.</Empty></div>
      ) : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
          {kpis.data.dashboard.map((k) => (
            <KpiCard key={k.key} kpi={k} icon={ICONES[k.key]} accent={k.key === "delayed" && (k.value ?? 0) > 0}
              onClick={LIENS[k.key] ? () => nav(LIENS[k.key]) : undefined} />
          ))}
        </div>
      )}

      {!vide && (
        <>
          <div className="grid gap-5 lg:grid-cols-2">
            <Card title={<span className="flex items-center gap-2"><BellRing className="size-4 text-alerte" /> Alertes actives</span>}
              subtitle={chips.length ? "Ensemble de la plateforme – non concerné par les filtres" : undefined}
              actions={<Link to="/alertes" className="btn-lien">Centre d'alertes</Link>}>
              {!alertes.data ? <Spinner /> : (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {NIVEAUX_ALERTES.map(({ n, c: couleur }) => (
                    <Link key={n} to={`/alertes?level=${encodeURIComponent(n)}`} className="rounded-md border border-ligne p-3 hover:bg-gris">
                      <span className="flex items-center gap-1.5 text-xs text-muted"><span className={`size-2 rounded-full ${couleur}`} />{n}</span>
                      <span className="mt-1 block text-xl font-bold tabular-nums text-profond">{resumeAlertes!.by_level[n]?.total ?? 0}</span>
                      <span className="text-[11px] text-muted">{resumeAlertes!.by_level[n]?.unread ?? 0} non lue(s)</span>
                    </Link>
                  ))}
                </div>
              )}
            </Card>
            <Card title={<span className="flex items-center gap-2"><ShieldAlert className="size-4 text-alerte" /> Niveau de risque des projets</span>}
              subtitle="Règles transparentes – pas une prédiction" actions={<Link to="/risques" className="btn-lien">Analyse des risques</Link>}>
              {!risques.data ? <Spinner /> : (
                <div className="space-y-2">
                  {(["Élevé", "Modéré", "Faible"] as const).map((n) => {
                    const v = risques.data!.par_niveau[n] ?? 0;
                    const pct = risques.data!.total ? (v / risques.data!.total) * 100 : 0;
                    return (
                      <div key={n} className="flex items-center gap-3 text-sm">
                        <span className="w-16 text-muted">{n}</span>
                        <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-ligne">
                          <div className={`h-full rounded-full ${n === "Élevé" ? "bg-red-600" : n === "Modéré" ? "bg-amber-400" : "bg-emerald-500"}`} style={{ width: `${pct}%` }} />
                        </div>
                        <span className="w-20 text-right tabular-nums">{v} projet{v > 1 ? "s" : ""}</span>
                      </div>
                    );
                  })}
                  <p className="pt-1 text-xs text-muted">{risques.data.total} projets actifs ou suspendus évalués.</p>
                </div>
              )}
            </Card>
          </div>

          {charts.error ? <ErrorBox message={charts.error} onRetry={charts.reload} /> : !c ? <Spinner /> : (
            <div className="grid gap-5 xl:grid-cols-2">
              <Card title="Répartition des projets par domaine" subtitle="Hors candidatures non retenues">
                <HBars data={c.by_domain} labelKey="domain" valueKey="projects" />
              </Card>
              <Card title="Évolution des projets par mois" subtitle="Par mois de dépôt de la candidature">
                <ProjectsMonthlyLine data={c.projects_monthly} />
              </Card>
              <Card title="Comparaison des performances par domaine" subtitle="Taux d'achèvement, progression moyenne, taux de retard">
                <DomainPerformance data={c.domain_performance} />
              </Card>
              <Card title="Répartition des projets par statut"><StatusDonut data={c.by_status} /></Card>
              <Card title="Évolution des financements" subtitle="Montants par mois de demande (FCFA)"><FundingArea data={c.fundings_monthly} /></Card>
              <Card title="Progression des projets actifs" subtitle="Nombre de projets par tranche"><ProgressBars data={c.progress_distribution} /></Card>
            </div>
          )}

          <Card title={`Projets en retard${retards.data ? ` (${retards.data.total})` : ""}`} subtitle="Date limite dépassée ou jalon non atteint à temps"
            actions={<Link to="/projets?delayed=1" className="btn-lien">Voir tous</Link>}>
            {retards.error ? <ErrorBox message={retards.error} /> : !retards.data ? <Spinner /> : retards.data.items.length === 0 ? (
              <p className="text-sm text-muted">Aucun projet en retard sur ce périmètre.</p>
            ) : (
              <div className="-mx-4 overflow-x-auto">
                <table className="tableau min-w-[640px]">
                  <thead><tr><th>Projet</th><th>Cohorte</th><th>Statut</th><th>Progression</th><th className="text-right">Retard</th></tr></thead>
                  <tbody>
                    {retards.data.items.map((p) => (
                      <tr key={p.id} className="cursor-pointer" onClick={() => nav(`/projets/${p.id}`)}>
                        <td className="max-w-xs"><span className="line-clamp-1 font-medium text-profond">{p.name}</span>
                          <span className="text-xs text-muted">{p.first_late_milestone ? `Jalon : ${p.first_late_milestone}` : "Date limite dépassée"}</span></td>
                        <td className="whitespace-nowrap">{p.cohort}</td>
                        <td><StatusBadge status={p.status} /></td>
                        <td><ProgressBar value={p.progress_pct} late /></td>
                        <td className="whitespace-nowrap text-right font-semibold text-alerte">{p.days_late} j</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
