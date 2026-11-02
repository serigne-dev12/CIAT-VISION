/** Module 4 – Analyse des performances : tous les graphiques sont alimentés par l'API et suivent les filtres. */
import { api } from "../api/client";
import type { Charts, Kpi } from "../api/types";
import { ApplicationsLine, CohortsBars, FundingArea, HBars, ProgressBars, RatesLine, StatusDonut } from "../components/charts";
import { useData } from "../components/DataContext";
import FiltersBar from "../components/FiltersBar";
import KpiCard from "../components/KpiCard";
import { Card, ErrorBox, Spinner } from "../components/ui";
import { useApi } from "../lib/hooks";

export default function AnalysisPage() {
  const { params, describe } = useData();
  const key = JSON.stringify(params);
  const charts = useApi(() => api.get<Charts>("/analytics/charts", params), [key]);
  const kpis = useApi(() => api.get<{ all: Kpi[] }>("/analytics/kpis", params), [key]);
  const k = Object.fromEntries((kpis.data?.all ?? []).map((x) => [x.key, x]));
  const c = charts.data;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="titre-page">Analyse des performances</h1>
        <p className="text-sm text-muted">{describe}</p>
      </div>
      <FiltersBar />
      {kpis.data && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {["selection_rate", "completion_rate", "delay_rate", "avg_progress"].map((x) => k[x] && <KpiCard key={x} kpi={k[x]} accent={x === "delay_rate"} />)}
        </div>
      )}
      {charts.error ? <ErrorBox message={charts.error} onRetry={charts.reload} /> : !c ? <Spinner /> : (
        <div className="grid gap-5 xl:grid-cols-2">
          <Card title="1. Évolution mensuelle des candidatures" subtitle="Reçues, acceptées et rejetées par mois de dépôt"><ApplicationsLine data={c.applications_monthly} /></Card>
          <Card title="2. Répartition des projets par domaine" subtitle="Hors candidatures non retenues"><HBars data={c.by_domain} labelKey="domain" valueKey="projects" /></Card>
          <Card title="3. Répartition par statut"><StatusDonut data={c.by_status} /></Card>
          <Card title="4. Comparaison des cohortes"><CohortsBars data={c.cohorts} /></Card>
          <Card title="5. Évolution des financements" subtitle="Montants par mois de demande (FCFA)"><FundingArea data={c.fundings_monthly} /></Card>
          <Card title="6–8. Taux de sélection, d'achèvement et de retard par cohorte"
            subtitle="Une cohorte en cours a naturellement un taux d'achèvement faible"><RatesLine data={c.cohorts} /></Card>
          <Card title="9. Progression des projets actifs" subtitle="Nombre de projets par tranche de progression"><ProgressBars data={c.progress_distribution} /></Card>
          <Card title="Financements reçus par domaine"><HBars data={c.fundings_by_domain} labelKey="label" valueKey="received" money /></Card>
          <Card title="Financements accordés par source"><HBars data={c.fundings_by_source} labelKey="label" valueKey="granted" money /></Card>
          <Card title="Projets terminés par domaine"><HBars data={c.by_domain} labelKey="domain" valueKey="completed" unit="terminés" /></Card>
        </div>
      )}
    </div>
  );
}
