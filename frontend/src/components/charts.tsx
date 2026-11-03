/**
 * Graphiques interactifs (Recharts). Toutes les données viennent de l'API : ces composants ne calculent rien.
 */
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import type { Charts, CohortStats } from "../api/types";
import { AXE, BEIGE, BRUN, GRILLE, SERIES, STATUT_COULEURS } from "../lib/colors";
import { fmtFCFA, fmtMillions, fmtMois, fmtNombre } from "../lib/format";
import { Empty } from "./ui";

/** Animations discrètes, désactivées si l'utilisateur a demandé à réduire les animations (accessibilité). */
const ANIMER = typeof window === "undefined" || !window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

const axe = { tick: { fill: AXE, fontSize: 11 }, axisLine: { stroke: GRILLE }, tickLine: false } as const;
const tooltipStyle = { contentStyle: { borderRadius: 8, borderColor: "#E8E1DA", fontSize: 12 }, cursor: { fill: "rgba(202,152,113,0.12)" } };

function vide(n: number) {
  return n === 0 ? <Empty title="Aucune donnée sur ce périmètre">Modifiez les filtres pour élargir l'analyse.</Empty> : null;
}

/** Barres horizontales triées (une seule série : couleur unique). */
export function HBars({ data, labelKey, valueKey, unit = "projets", money = false, height }:
  { data: Record<string, unknown>[]; labelKey: string; valueKey: string; unit?: string; money?: boolean; height?: number }) {
  if (vide(data.length)) return vide(0);
  const rows = [...data].sort((a, b) => Number(b[valueKey]) - Number(a[valueKey]));
  return (
    <ResponsiveContainer width="100%" height={height ?? Math.max(220, rows.length * 34 + 30)}>
      <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 48, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke={GRILLE} />
        <XAxis type="number" {...axe} tickFormatter={money ? fmtMillions : fmtNombre} />
        <YAxis type="category" dataKey={labelKey} {...axe} width={150} tick={{ fill: "#2B211B", fontSize: 11 }} />
        <Tooltip {...tooltipStyle} formatter={(v) => [money ? fmtFCFA(Number(v)) : `${fmtNombre(Number(v))} ${unit}`, ""]} separator="" />
        <Bar isAnimationActive={ANIMER} dataKey={valueKey} fill={BRUN} radius={[0, 4, 4, 0]} maxBarSize={22}
          label={{ position: "right", fill: "#2B211B", fontSize: 11, formatter: (v: unknown) => (money ? fmtMillions(Number(v)) : fmtNombre(Number(v))) }} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Anneau de répartition par statut (couleur fixe par statut). */
export function StatusDonut({ data }: { data: Charts["by_status"] }) {
  const total = data.reduce((s, d) => s + d.count, 0);
  if (vide(total)) return vide(0);
  return (
    <div className="grid items-center gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie isAnimationActive={ANIMER} data={data} dataKey="count" nameKey="status" innerRadius="58%" outerRadius="90%" paddingAngle={1.5} stroke="#fff" strokeWidth={2}>
            {data.map((d) => <Cell key={d.status} fill={STATUT_COULEURS[d.status] ?? AXE} />)}
          </Pie>
          <Tooltip {...tooltipStyle} formatter={(v, n) => [`${fmtNombre(Number(v))} (${Math.round((Number(v) / total) * 100)} %)`, String(n)]} />
          <text x="50%" y="48%" textAnchor="middle" className="fill-profond text-2xl font-bold">{total}</text>
          <text x="50%" y="58%" textAnchor="middle" className="fill-muted text-xs">dossiers</text>
        </PieChart>
      </ResponsiveContainer>
      <ul className="space-y-1.5 text-sm">
        {data.map((d) => (
          <li key={d.status} className="flex items-center gap-2">
            <span className="size-3 shrink-0 rounded-sm" style={{ background: STATUT_COULEURS[d.status] ?? AXE }} />
            <span className="flex-1 truncate">{d.status}</span>
            <span className="tabular-nums text-muted">{d.count}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Évolution mensuelle des candidatures (courbes). */
export function ApplicationsLine({ data }: { data: Charts["applications_monthly"] }) {
  if (vide(data.length)) return vide(0);
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ left: -10, right: 12, top: 8 }}>
        <CartesianGrid vertical={false} stroke={GRILLE} />
        <XAxis dataKey="month" {...axe} tickFormatter={fmtMois} minTickGap={12} />
        <YAxis {...axe} allowDecimals={false} />
        <Tooltip {...tooltipStyle} labelFormatter={(m) => fmtMois(String(m))} />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
        <Line isAnimationActive={ANIMER} type="monotone" dataKey="received" name="Reçues" stroke={BRUN} strokeWidth={2} dot={{ r: 3 }} />
        <Line isAnimationActive={ANIMER} type="monotone" dataKey="accepted" name="Acceptées" stroke={SERIES[3]} strokeWidth={2} dot={{ r: 3 }} />
        <Line isAnimationActive={ANIMER} type="monotone" dataKey="rejected" name="Rejetées" stroke={SERIES[1]} strokeWidth={2} dot={{ r: 3 }} strokeDasharray="4 3" />
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Comparaison des cohortes (barres groupées). */
export function CohortsBars({ data }: { data: CohortStats[] }) {
  if (vide(data.length)) return vide(0);
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ left: -10, right: 8, top: 8 }} barGap={3}>
        <CartesianGrid vertical={false} stroke={GRILLE} />
        <XAxis dataKey="cohort" {...axe} />
        <YAxis {...axe} allowDecimals={false} />
        <Tooltip {...tooltipStyle} />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
        <Bar isAnimationActive={ANIMER} dataKey="applications" name="Candidatures" fill={SERIES[1]} radius={[4, 4, 0, 0]} maxBarSize={28} />
        <Bar isAnimationActive={ANIMER} dataKey="selected" name="Sélectionnés" fill={SERIES[0]} radius={[4, 4, 0, 0]} maxBarSize={28} />
        <Bar isAnimationActive={ANIMER} dataKey="completed" name="Terminés" fill={SERIES[3]} radius={[4, 4, 0, 0]} maxBarSize={28} />
        <Bar isAnimationActive={ANIMER} dataKey="delayed" name="En retard" fill="#E34948" radius={[4, 4, 0, 0]} maxBarSize={28} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Taux par cohorte (courbes en %). */
export function RatesLine({ data }: { data: CohortStats[] }) {
  if (vide(data.length)) return vide(0);
  const rows = data.map((c) => ({
    cohort: c.cohort,
    selection: c.selection_rate === null ? null : Math.round(c.selection_rate * 1000) / 10,
    achevement: c.completion_rate === null ? null : Math.round(c.completion_rate * 1000) / 10,
    retard: c.delay_rate === null ? null : Math.round(c.delay_rate * 1000) / 10,
  }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={rows} margin={{ left: -10, right: 12, top: 8 }}>
        <CartesianGrid vertical={false} stroke={GRILLE} />
        <XAxis dataKey="cohort" {...axe} />
        <YAxis {...axe} unit=" %" domain={[0, 100]} />
        <Tooltip {...tooltipStyle} formatter={(v) => (v === null ? "non calculable" : `${String(v).replace(".", ",")} %`)} />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
        <Line isAnimationActive={ANIMER} dataKey="selection" name="Taux de sélection" stroke={SERIES[0]} strokeWidth={2} connectNulls={false} />
        <Line isAnimationActive={ANIMER} dataKey="achevement" name="Taux d'achèvement" stroke={SERIES[3]} strokeWidth={2} connectNulls={false} />
        <Line isAnimationActive={ANIMER} dataKey="retard" name="Taux de retard" stroke="#E34948" strokeWidth={2} strokeDasharray="4 3" connectNulls={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Évolution des financements (aires). */
export function FundingArea({ data }: { data: Charts["fundings_monthly"] }) {
  if (vide(data.length)) return vide(0);
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} margin={{ left: 0, right: 12, top: 8 }}>
        <CartesianGrid vertical={false} stroke={GRILLE} />
        <XAxis dataKey="month" {...axe} tickFormatter={fmtMois} minTickGap={16} />
        <YAxis {...axe} tickFormatter={fmtMillions} width={56} />
        <Tooltip {...tooltipStyle} labelFormatter={(m) => fmtMois(String(m))} formatter={(v, n) => [fmtFCFA(Number(v)), String(n)]} />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
        <Area isAnimationActive={ANIMER} type="monotone" dataKey="requested" name="Demandé" stroke={AXE} fill={AXE} fillOpacity={0.08} strokeDasharray="4 3" />
        <Area isAnimationActive={ANIMER} type="monotone" dataKey="granted" name="Accordé" stroke={BEIGE} fill={BEIGE} fillOpacity={0.25} />
        <Area isAnimationActive={ANIMER} type="monotone" dataKey="received" name="Reçu" stroke={BRUN} fill={BRUN} fillOpacity={0.25} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/** Histogramme de progression des projets actifs. */
export function ProgressBars({ data }: { data: Charts["progress_distribution"] }) {
  if (vide(data.reduce((s, d) => s + d.count, 0))) return vide(0);
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ left: -10, right: 8, top: 16 }}>
        <CartesianGrid vertical={false} stroke={GRILLE} />
        <XAxis dataKey="range" {...axe} />
        <YAxis {...axe} allowDecimals={false} />
        <Tooltip {...tooltipStyle} formatter={(v) => [`${v} projets actifs`, ""]} separator="" />
        <Bar isAnimationActive={ANIMER} dataKey="count" fill={BRUN} radius={[4, 4, 0, 0]} maxBarSize={56} label={{ position: "top", fill: "#2B211B", fontSize: 11 }} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ------------------------------------------------------------------ V2
/** Évolution des projets par mois de dépôt (projets, sélectionnés, terminés). */
export function ProjectsMonthlyLine({ data }: { data: { month: string; projects: number; selected: number; completed: number }[] }) {
  if (vide(data.length)) return vide(0);
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ left: -10, right: 12, top: 8 }}>
        <CartesianGrid vertical={false} stroke={GRILLE} />
        <XAxis dataKey="month" {...axe} tickFormatter={fmtMois} minTickGap={12} />
        <YAxis {...axe} allowDecimals={false} />
        <Tooltip {...tooltipStyle} labelFormatter={(m) => fmtMois(String(m))} />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
        <Line isAnimationActive={ANIMER} type="monotone" dataKey="projects" name="Projets" stroke={BRUN} strokeWidth={2} dot={{ r: 3 }} />
        <Line isAnimationActive={ANIMER} type="monotone" dataKey="selected" name="Sélectionnés" stroke={SERIES[1]} strokeWidth={2} dot={{ r: 3 }} />
        <Line isAnimationActive={ANIMER} type="monotone" dataKey="completed" name="Terminés" stroke={SERIES[3]} strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Comparaison des performances par domaine : taux d'achèvement, taux de retard, progression moyenne (en %). */
export function DomainPerformance({ data }: { data: { domain: string; completion_rate: number | null; delay_rate: number | null; avg_progress: number | null }[] }) {
  if (vide(data.length)) return vide(0);
  const rows = data.map((d) => ({
    domaine: d.domain,
    achevement: d.completion_rate === null ? null : Math.round(d.completion_rate * 1000) / 10,
    retard: d.delay_rate === null ? null : Math.round(d.delay_rate * 1000) / 10,
    progression: d.avg_progress,
  }));
  return (
    <ResponsiveContainer width="100%" height={Math.max(300, rows.length * 46 + 60)}>
      <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 24, top: 4 }} barGap={2}>
        <CartesianGrid horizontal={false} stroke={GRILLE} />
        <XAxis type="number" {...axe} domain={[0, 100]} unit=" %" />
        <YAxis type="category" dataKey="domaine" {...axe} width={150} tick={{ fill: "#2B211B", fontSize: 11 }} />
        <Tooltip {...tooltipStyle} formatter={(v) => (v === null ? "non calculable" : `${String(v).replace(".", ",")} %`)} />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
        <Bar isAnimationActive={ANIMER} dataKey="achevement" name="Taux d'achèvement" fill={SERIES[3]} radius={[0, 3, 3, 0]} maxBarSize={10} />
        <Bar isAnimationActive={ANIMER} dataKey="progression" name="Progression moyenne" fill={BRUN} radius={[0, 3, 3, 0]} maxBarSize={10} />
        <Bar isAnimationActive={ANIMER} dataKey="retard" name="Taux de retard" fill="#E34948" radius={[0, 3, 3, 0]} maxBarSize={10} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Barres groupées génériques : une série par élément comparé, une catégorie par indicateur (valeurs en %). */
export function CompareBars({ rows, series }: { rows: Record<string, string | number | null>[]; series: string[] }) {
  if (vide(rows.length)) return vide(0);
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={rows} margin={{ left: -10, right: 8, top: 8 }} barGap={3}>
        <CartesianGrid vertical={false} stroke={GRILLE} />
        <XAxis dataKey="indicateur" {...axe} interval={0} tick={{ fill: AXE, fontSize: 11 }} />
        <YAxis {...axe} unit=" %" domain={[0, 100]} />
        <Tooltip {...tooltipStyle} formatter={(v) => (v === null ? "non calculable" : `${String(v).replace(".", ",")} %`)} />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
        {series.map((s, i) => <Bar isAnimationActive={ANIMER} key={s} dataKey={s} name={s} fill={SERIES[i % SERIES.length]} radius={[4, 4, 0, 0]} maxBarSize={36} />)}
      </BarChart>
    </ResponsiveContainer>
  );
}
