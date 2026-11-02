/**
 * Référentiels (domaines, cohortes, informations générales) chargés une fois,
 * et filtres d'analyse partagés par toutes les pages (période, cohorte, domaine, statut).
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { Cohort, Domain, Meta } from "../api/types";

export interface Filters { start_date: string; end_date: string; cohort_id: string; domain_id: string; status: string }
export const EMPTY_FILTERS: Filters = { start_date: "", end_date: "", cohort_id: "", domain_id: "", status: "" };

interface DataState {
  domains: Domain[];
  cohorts: Cohort[];
  meta: Meta | null;
  reloadRefs: () => void;
  filters: Filters;
  setFilters: (f: Filters) => void;
  params: Record<string, string>;
  describe: string;
}

const Ctx = createContext<DataState | null>(null);

export function DataProvider({ children }: { children: ReactNode }) {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);

  const reloadRefs = useCallback(() => {
    api.get<Domain[]>("/domains").then(setDomains).catch(() => undefined);
    api.get<Cohort[]>("/cohorts").then(setCohorts).catch(() => undefined);
    api.get<Meta>("/analytics/meta").then(setMeta).catch(() => undefined);
  }, []);
  useEffect(reloadRefs, [reloadRefs]);

  const params = useMemo(() => {
    const p: Record<string, string> = {};
    for (const [k, v] of Object.entries(filters)) if (v) p[k] = v;
    return p;
  }, [filters]);

  const describe = useMemo(() => {
    const parts: string[] = [];
    if (filters.start_date || filters.end_date) parts.push(`Période : ${filters.start_date || "…"} → ${filters.end_date || "…"}`);
    if (filters.cohort_id) parts.push(cohorts.find((c) => String(c.id) === filters.cohort_id)?.name ?? "");
    if (filters.domain_id) parts.push(domains.find((d) => String(d.id) === filters.domain_id)?.name ?? "");
    if (filters.status) parts.push(`Statut : ${filters.status}`);
    return parts.filter(Boolean).join(" · ") || "Toutes les données";
  }, [filters, cohorts, domains]);

  const value = useMemo(() => ({ domains, cohorts, meta, reloadRefs, filters, setFilters, params, describe }),
    [domains, cohorts, meta, reloadRefs, filters, params, describe]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useData(): DataState {
  const c = useContext(Ctx);
  if (!c) throw new Error("useData doit être utilisé dans <DataProvider>");
  return c;
}

/** Convertit les filtres en paramètres de l'API de rapports (format JSON). */
export function filtersToBody(f: Filters) {
  return {
    start_date: f.start_date || null, end_date: f.end_date || null,
    cohort_ids: f.cohort_id ? [Number(f.cohort_id)] : [], domain_ids: f.domain_id ? [Number(f.domain_id)] : [],
    statuses: f.status ? [f.status] : [],
  };
}
