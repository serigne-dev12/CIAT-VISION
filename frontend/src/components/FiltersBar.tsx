/**
 * Barre de filtres globaux (V2) : période (prédéfinie ou personnalisée), cohorte, domaine, statut, responsable,
 * niveau de performance, niveau de financement. Les choix sont appliqués avec « Appliquer les filtres » ;
 * les filtres actifs sont affichés et peuvent être retirés un par un.
 */
import { Check, Filter, RotateCcw, X } from "lucide-react";
import { useState } from "react";
import { PERIOD_LABELS, useData, type Filters, type PeriodPreset } from "./DataContext";
import { InfoTip } from "./ui";

type Champ = "status" | "responsible" | "performance" | "funding";

export default function FiltersBar({ hide = [] }: { hide?: Champ[] }) {
  const { draft, setDraft, applyFilters, resetFilters, removeFilter, pending, chips, cohorts, domains, responsables, meta } = useData();
  const [ouvert, setOuvert] = useState(false);
  const maj = (k: keyof Filters, v: string) => setDraft({ ...draft, [k]: v });
  const periodeInvalide = draft.period === "custom" && draft.start_date && draft.end_date && draft.end_date < draft.start_date;
  const montre = (c: Champ) => !hide.includes(c);

  return (
    <div className="carte p-3">
      <button className="flex w-full items-center justify-between text-sm font-medium text-profond lg:hidden"
        onClick={() => setOuvert(!ouvert)} aria-expanded={ouvert}>
        <span className="flex items-center gap-2"><Filter className="size-4" /> Filtres {chips.length > 0 && `(${chips.length})`}</span>
        <span className="text-xs text-muted">{ouvert ? "Masquer" : "Afficher"}</span>
      </button>
      <form className={`${ouvert ? "mt-3 grid" : "hidden"} grid-cols-1 gap-3 sm:grid-cols-2 lg:mt-0 lg:grid lg:grid-cols-4 xl:grid-cols-8`}
        onSubmit={(e) => { e.preventDefault(); if (!periodeInvalide) applyFilters(); }}>
        <div className="xl:col-span-2">
          <label className="etiquette" htmlFor="f-periode">Période (dépôt des candidatures)</label>
          <select id="f-periode" className="champ" value={draft.period} onChange={(e) => maj("period", e.target.value as PeriodPreset)}>
            {(Object.keys(PERIOD_LABELS) as PeriodPreset[]).map((p) => <option key={p} value={p}>{PERIOD_LABELS[p]}</option>)}
          </select>
          {draft.period === "custom" && (
            <div className="mt-2 grid grid-cols-2 gap-2">
              <input type="date" className="champ" aria-label="Début" value={draft.start_date} onChange={(e) => maj("start_date", e.target.value)} />
              <input type="date" className="champ" aria-label="Fin" value={draft.end_date} onChange={(e) => maj("end_date", e.target.value)}
                aria-invalid={!!periodeInvalide} />
            </div>
          )}
        </div>
        <div>
          <label className="etiquette" htmlFor="f-cohorte">Cohorte</label>
          <select id="f-cohorte" className="champ" value={draft.cohort_id} onChange={(e) => maj("cohort_id", e.target.value)}>
            <option value="">Toutes</option>{cohorts.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="etiquette" htmlFor="f-domaine">Domaine</label>
          <select id="f-domaine" className="champ" value={draft.domain_id} onChange={(e) => maj("domain_id", e.target.value)}>
            <option value="">Tous</option>{domains.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>
        {montre("status") && (
          <div>
            <label className="etiquette" htmlFor="f-statut">Statut</label>
            <select id="f-statut" className="champ" value={draft.status} onChange={(e) => maj("status", e.target.value)}>
              <option value="">Tous</option>{(meta?.statuses ?? []).map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
        )}
        {montre("responsible") && (
          <div>
            <label className="etiquette" htmlFor="f-resp">Responsable de suivi</label>
            <select id="f-resp" className="champ" value={draft.responsible_id} onChange={(e) => maj("responsible_id", e.target.value)}>
              <option value="">Tous</option>{responsables.map((r) => <option key={r.id} value={r.id}>{r.full_name}</option>)}
            </select>
          </div>
        )}
        {montre("performance") && (
          <div>
            <label className="etiquette flex items-center gap-1" htmlFor="f-perf">Performance {meta && <InfoTip text={meta.performance_definition} />}</label>
            <select id="f-perf" className="champ" value={draft.performance} onChange={(e) => maj("performance", e.target.value)}>
              <option value="">Tous</option>{(meta?.performance_levels ?? []).map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
        )}
        {montre("funding") && (
          <div>
            <label className="etiquette flex items-center gap-1" htmlFor="f-fin">Financement {meta && <InfoTip text={meta.funding_definition} />}</label>
            <select id="f-fin" className="champ" value={draft.funding_level} onChange={(e) => maj("funding_level", e.target.value)}>
              <option value="">Tous</option>{(meta?.funding_levels ?? []).map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
        )}
        <div className="flex flex-wrap items-end gap-2 sm:col-span-2 lg:col-span-4 xl:col-span-8 xl:justify-end">
          {pending && <span className="mr-auto self-center text-xs text-alerte">Modifications non appliquées</span>}
          <button type="button" className="btn-secondaire" onClick={resetFilters} disabled={!chips.length && !pending}>
            <RotateCcw className="size-4" /> Réinitialiser
          </button>
          <button type="submit" className="btn-principal" disabled={!pending || !!periodeInvalide}>
            <Check className="size-4" /> Appliquer les filtres
          </button>
        </div>
      </form>
      {periodeInvalide && <p className="mt-2 text-xs text-danger">La fin de période doit être postérieure au début.</p>}
      {chips.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-ligne pt-3" aria-label="Filtres actifs">
          <span className="text-xs font-medium text-muted">Filtres actifs :</span>
          {chips.map((c) => (
            <span key={c.key} className="inline-flex items-center gap-1 rounded-full bg-beige-pale px-2.5 py-1 text-xs text-profond">
              {c.label}
              <button onClick={() => removeFilter(c.key)} className="rounded-full p-0.5 hover:bg-beige/40" aria-label={`Retirer le filtre ${c.label}`}>
                <X className="size-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
