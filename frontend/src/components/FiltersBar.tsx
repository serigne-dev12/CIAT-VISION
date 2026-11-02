/** Barre de filtres commune : période, cohorte, domaine, statut. */
import { Filter, RotateCcw } from "lucide-react";
import { useState } from "react";
import { EMPTY_FILTERS, useData } from "./DataContext";

export default function FiltersBar({ showStatus = true }: { showStatus?: boolean }) {
  const { filters, setFilters, cohorts, domains, meta } = useData();
  const [ouvert, setOuvert] = useState(false);
  const actifs = Object.values(filters).filter(Boolean).length;
  const maj = (k: keyof typeof filters, v: string) => setFilters({ ...filters, [k]: v });
  const periodeInvalide = filters.start_date && filters.end_date && filters.end_date < filters.start_date;

  return (
    <div className="carte p-3">
      <button className="flex w-full items-center justify-between text-sm font-medium text-profond sm:hidden"
        onClick={() => setOuvert(!ouvert)} aria-expanded={ouvert}>
        <span className="flex items-center gap-2"><Filter className="size-4" /> Filtres {actifs > 0 && `(${actifs})`}</span>
        <span className="text-xs text-muted">{ouvert ? "Masquer" : "Afficher"}</span>
      </button>
      <div className={`${ouvert ? "mt-3 grid" : "hidden"} grid-cols-1 gap-3 sm:mt-0 sm:grid sm:grid-cols-2 lg:grid-cols-[repeat(5,minmax(0,1fr))_auto] lg:items-end`}>
        <div>
          <label className="etiquette" htmlFor="f-debut">Dépôt du</label>
          <input id="f-debut" type="date" className="champ" value={filters.start_date} onChange={(e) => maj("start_date", e.target.value)} />
        </div>
        <div>
          <label className="etiquette" htmlFor="f-fin">au</label>
          <input id="f-fin" type="date" className="champ" value={filters.end_date} onChange={(e) => maj("end_date", e.target.value)}
            aria-invalid={!!periodeInvalide} />
        </div>
        <div>
          <label className="etiquette" htmlFor="f-cohorte">Cohorte</label>
          <select id="f-cohorte" className="champ" value={filters.cohort_id} onChange={(e) => maj("cohort_id", e.target.value)}>
            <option value="">Toutes</option>
            {cohorts.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="etiquette" htmlFor="f-domaine">Domaine</label>
          <select id="f-domaine" className="champ" value={filters.domain_id} onChange={(e) => maj("domain_id", e.target.value)}>
            <option value="">Tous</option>
            {domains.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>
        {showStatus ? (
          <div>
            <label className="etiquette" htmlFor="f-statut">Statut</label>
            <select id="f-statut" className="champ" value={filters.status} onChange={(e) => maj("status", e.target.value)}>
              <option value="">Tous</option>
              {(meta?.statuses ?? []).map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
        ) : <div className="hidden lg:block" />}
        <button className="btn-secondaire" onClick={() => setFilters(EMPTY_FILTERS)} disabled={!actifs}>
          <RotateCcw className="size-4" /> Réinitialiser
        </button>
      </div>
      {periodeInvalide && <p className="mt-2 text-xs text-danger">La fin de période doit être postérieure au début.</p>}
    </div>
  );
}
