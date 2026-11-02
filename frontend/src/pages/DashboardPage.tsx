/** Module 2 – Tableau de bord général. */
import { AlarmClock, CheckCircle2, ClipboardList, FlaskConical, FolderKanban, Rocket, Sprout, Wallet } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { Charts, DelayedProject, Kpi } from "../api/types";
import { ApplicationsLine, StatusDonut } from "../components/charts";
import { useData } from "../components/DataContext";
import FiltersBar from "../components/FiltersBar";
import KpiCard from "../components/KpiCard";
import { Card, ErrorBox, ProgressBar, Spinner, StatusBadge } from "../components/ui";
import { fmtKpi } from "../lib/format";
import { useApi } from "../lib/hooks";

const ICONES: Record<string, ReactNode> = {
  total_projects: <FolderKanban className="size-4" />, applications: <ClipboardList className="size-4" />,
  selected: <CheckCircle2 className="size-4" />, in_incubation: <Sprout className="size-4" />,
  prototypes: <FlaskConical className="size-4" />, completed: <Rocket className="size-4" />,
  delayed: <AlarmClock className="size-4" />, funding_received: <Wallet className="size-4" />,
};

/** Clic sur un indicateur → liste des projets correspondants. */
const LIENS: Record<string, string> = {
  in_incubation: "status=En incubation", prototypes: "status=Prototype réalisé", completed: "status=Terminé",
  delayed: "delayed=1", selected: "", total_projects: "", applications: "",
};

export default function DashboardPage() {
  const { params, describe } = useData();
  const nav = useNavigate();
  const key = JSON.stringify(params);
  const kpis = useApi(() => api.get<{ dashboard: Kpi[]; all: Kpi[]; perimetre: string }>("/analytics/kpis", params), [key]);
  const charts = useApi(() => api.get<Charts>("/analytics/charts", params), [key]);
  const retards = useApi(() => api.get<{ total: number; items: DelayedProject[] }>("/analytics/delayed", { ...params, limit: 6 }), [key]);
  const all = Object.fromEntries((kpis.data?.all ?? []).map((k) => [k.key, k]));

  return (
    <div className="space-y-5">
      <div>
        <h1 className="titre-page">Tableau de bord</h1>
        <p className="text-sm text-muted">Vue d'ensemble des activités du CIAT · {describe}</p>
      </div>
      <FiltersBar />

      {kpis.error ? <ErrorBox message={kpis.error} onRetry={kpis.reload} /> : !kpis.data ? <Spinner /> : (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {kpis.data.dashboard.map((k) => (
              <KpiCard key={k.key} kpi={k} icon={ICONES[k.key]} accent={k.key === "delayed" && (k.value ?? 0) > 0}
                onClick={k.key in LIENS ? () => nav(`/projets${LIENS[k.key] ? `?${LIENS[k.key]}` : ""}`) : undefined} />
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            {["selection_rate", "completion_rate", "delay_rate", "avg_progress"].map((k) => all[k] && (
              <div key={k} className="carte flex flex-col gap-0.5 px-4 py-3 sm:flex-row sm:items-center sm:justify-between" title={all[k].definition}>
                <span className="text-xs text-muted sm:text-sm">{all[k].label}</span>
                <span className="whitespace-nowrap font-semibold tabular-nums text-profond">{fmtKpi(all[k].value, all[k].unit)}</span>
              </div>
            ))}
          </div>
        </>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        <Card title="Évolution mensuelle des candidatures" subtitle="Par mois de dépôt">
          {charts.error ? <ErrorBox message={charts.error} /> : charts.data ? <ApplicationsLine data={charts.data.applications_monthly} /> : <Spinner />}
        </Card>
        <Card title="Répartition des dossiers par statut">
          {charts.data ? <StatusDonut data={charts.data.by_status} /> : <Spinner />}
        </Card>
      </div>

      <Card title={`Projets en retard${retards.data ? ` (${retards.data.total})` : ""}`}
        subtitle="Date limite dépassée ou jalon non atteint à temps"
        actions={<Link to="/projets?delayed=1" className="btn-lien">Voir tous</Link>}>
        {retards.error ? <ErrorBox message={retards.error} /> : !retards.data ? <Spinner /> : retards.data.items.length === 0 ? (
          <p className="text-sm text-muted">Aucun projet en retard sur ce périmètre. 👍</p>
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
    </div>
  );
}
