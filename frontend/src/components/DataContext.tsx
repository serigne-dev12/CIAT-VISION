/**
 * Référentiels (domaines, cohortes, responsables, informations générales) chargés une fois,
 * et FILTRES GLOBAUX partagés par toutes les pages (V2) :
 * - un brouillon (`draft`) modifié dans la barre de filtres et des filtres APPLIQUÉS (`filters`) ;
 * - « Appliquer les filtres » copie le brouillon ; les KPI et graphiques se recalculent côté serveur ;
 * - les filtres appliqués sont conservés pendant la navigation et la session (sessionStorage).
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { Cohort, Domain, MetaV2, Responsable } from "../api/types";
import { todayISO } from "../lib/format";

export type PeriodPreset = "" | "today" | "7d" | "30d" | "quarter" | "year" | "custom";

export interface Filters {
  period: PeriodPreset; start_date: string; end_date: string; cohort_id: string; domain_id: string; status: string;
  responsible_id: string; performance: string; funding_level: string;
}
export const EMPTY_FILTERS: Filters = {
  period: "", start_date: "", end_date: "", cohort_id: "", domain_id: "", status: "", responsible_id: "",
  performance: "", funding_level: "",
};
export const PERIOD_LABELS: Record<PeriodPreset, string> = {
  "": "Toute la période", today: "Aujourd'hui", "7d": "7 derniers jours", "30d": "30 derniers jours",
  quarter: "Trimestre en cours", year: "Année en cours", custom: "Période personnalisée",
};

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

/** Bornes d'une période prédéfinie (dates de dépôt des candidatures). */
export function periodBounds(p: PeriodPreset, custom: { start: string; end: string }): { start: string; end: string } {
  const now = new Date();
  const jours = (n: number) => { const d = new Date(now); d.setDate(d.getDate() - n); return iso(d); };
  switch (p) {
    case "today": return { start: todayISO(), end: todayISO() };
    case "7d": return { start: jours(6), end: todayISO() };
    case "30d": return { start: jours(29), end: todayISO() };
    case "quarter": {
      const q = Math.floor(now.getMonth() / 3);
      return { start: iso(new Date(now.getFullYear(), q * 3, 1)), end: iso(new Date(now.getFullYear(), q * 3 + 3, 0)) };
    }
    case "year": return { start: `${now.getFullYear()}-01-01`, end: `${now.getFullYear()}-12-31` };
    case "custom": return custom;
    default: return { start: "", end: "" };
  }
}

/** Paramètres de l'API (requêtes GET) correspondant aux filtres. */
export function filtersToParams(f: Filters): Record<string, string> {
  const { start, end } = periodBounds(f.period, { start: f.start_date, end: f.end_date });
  const p: Record<string, string> = {};
  if (start) p.start_date = start;
  if (end) p.end_date = end;
  for (const k of ["cohort_id", "domain_id", "status", "responsible_id", "performance", "funding_level"] as const) {
    if (f[k]) p[k] = f[k];
  }
  return p;
}

/** Même périmètre au format JSON (rapports, assistant, comparaisons). */
export function filtersToBody(f: Filters) {
  const { start, end } = periodBounds(f.period, { start: f.start_date, end: f.end_date });
  return {
    start_date: start || null, end_date: end || null,
    cohort_ids: f.cohort_id ? [Number(f.cohort_id)] : [], domain_ids: f.domain_id ? [Number(f.domain_id)] : [],
    statuses: f.status ? [f.status] : [], responsible_ids: f.responsible_id ? [Number(f.responsible_id)] : [],
    performance_levels: f.performance ? [f.performance] : [], funding_levels: f.funding_level ? [f.funding_level] : [],
  };
}

export interface Chip { key: keyof Filters | "period"; label: string }

interface DataState {
  domains: Domain[];
  cohorts: Cohort[];
  responsables: Responsable[];
  meta: MetaV2 | null;
  reloadRefs: () => void;
  filters: Filters;            // filtres appliqués
  draft: Filters;              // brouillon de la barre de filtres
  setDraft: (f: Filters) => void;
  applyFilters: (f?: Filters) => void;
  resetFilters: () => void;
  removeFilter: (k: Chip["key"]) => void;
  pending: boolean;            // le brouillon diffère des filtres appliqués
  params: Record<string, string>;
  body: ReturnType<typeof filtersToBody>;
  chips: Chip[];
  describe: string;
}

const Ctx = createContext<DataState | null>(null);
const STORAGE_KEY = "ciat_vision_filtres";

function lireFiltres(): Filters {
  try {
    const brut = sessionStorage.getItem(STORAGE_KEY);
    return brut ? { ...EMPTY_FILTERS, ...JSON.parse(brut) } : EMPTY_FILTERS;
  } catch { return EMPTY_FILTERS; }
}

export function DataProvider({ children }: { children: ReactNode }) {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [responsables, setResponsables] = useState<Responsable[]>([]);
  const [meta, setMeta] = useState<MetaV2 | null>(null);
  const [filters, setFilters] = useState<Filters>(lireFiltres);
  const [draft, setDraft] = useState<Filters>(filters);

  const reloadRefs = useCallback(() => {
    api.get<Domain[]>("/domains").then(setDomains).catch(() => undefined);
    api.get<Cohort[]>("/cohorts").then(setCohorts).catch(() => undefined);
    api.get<Responsable[]>("/responsables").then(setResponsables).catch(() => undefined);
    api.get<MetaV2>("/analytics/meta").then(setMeta).catch(() => undefined);
  }, []);
  useEffect(() => { reloadRefs(); }, [reloadRefs]);
  useEffect(() => { try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(filters)); } catch { /* indisponible */ } }, [filters]);

  const applyFilters = useCallback((f?: Filters) => {
    const cible = f ?? draft;
    setFilters(cible);
    setDraft(cible);
  }, [draft]);
  const resetFilters = useCallback(() => { setFilters(EMPTY_FILTERS); setDraft(EMPTY_FILTERS); }, []);
  const removeFilter = useCallback((k: Chip["key"]) => {
    const f = { ...filters, [k]: "" } as Filters;
    if (k === "period") { f.start_date = ""; f.end_date = ""; }
    setFilters(f);
    setDraft(f);
  }, [filters]);

  const params = useMemo(() => filtersToParams(filters), [filters]);
  const body = useMemo(() => filtersToBody(filters), [filters]);
  const pending = JSON.stringify(draft) !== JSON.stringify(filters);

  const chips = useMemo(() => {
    const c: Chip[] = [];
    if (filters.period) {
      const { start, end } = periodBounds(filters.period, { start: filters.start_date, end: filters.end_date });
      c.push({ key: "period", label: filters.period === "custom" ? `Période : ${start || "…"} → ${end || "…"}` : PERIOD_LABELS[filters.period] });
    }
    if (filters.cohort_id) {
      c.push({ key: "cohort_id", label: cohorts.find((x) => String(x.id) === filters.cohort_id)?.name ?? "Cohorte" });
    }
    if (filters.domain_id) {
      c.push({ key: "domain_id", label: domains.find((x) => String(x.id) === filters.domain_id)?.name ?? "Domaine" });
    }
    if (filters.status) c.push({ key: "status", label: `Statut : ${filters.status}` });
    if (filters.responsible_id) {
      const r = responsables.find((x) => String(x.id) === filters.responsible_id);
      c.push({ key: "responsible_id", label: `Responsable : ${r?.full_name ?? "?"}` });
    }
    if (filters.performance) c.push({ key: "performance", label: `Performance : ${filters.performance}` });
    if (filters.funding_level) c.push({ key: "funding_level", label: `Financement : ${filters.funding_level}` });
    return c;
  }, [filters, cohorts, domains, responsables]);

  const describe = chips.map((x) => x.label).join(" · ") || "Toutes les données";

  const value = useMemo(() => ({
    domains, cohorts, responsables, meta, reloadRefs, filters, draft, setDraft, applyFilters, resetFilters, removeFilter,
    pending, params, body, chips, describe,
  }), [domains, cohorts, responsables, meta, reloadRefs, filters, draft, applyFilters, resetFilters, removeFilter,
    pending, params, body, chips, describe]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useData(): DataState {
  const c = useContext(Ctx);
  if (!c) throw new Error("useData doit être utilisé dans <DataProvider>");
  return c;
}
