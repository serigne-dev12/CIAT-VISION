/** Carte d'indicateur : valeur calculée par le backend ; définition / formule dans une infobulle. */
import type { ReactNode } from "react";
import type { Kpi } from "../api/types";
import { fmtKpi } from "../lib/format";
import { InfoTip } from "./ui";

export default function KpiCard({ kpi, icon, accent = false, onClick }:
  { kpi: Kpi; icon?: ReactNode; accent?: boolean; onClick?: () => void }) {
  const contenu = (
    <>
      <span className="block text-xs font-medium text-muted">{kpi.label}</span>
      <span className={`mt-2 block text-xl font-bold leading-tight tabular-nums sm:text-2xl ${accent ? "text-alerte" : "text-profond"}`}>
        {fmtKpi(kpi.value, kpi.unit)}
      </span>
    </>
  );
  return (
    <div className={`carte animate-apparition relative flex w-full flex-col p-4 transition-shadow ${onClick ? "hover:shadow-md" : ""} ${accent ? "border-l-4 border-l-alerte" : "border-l-4 border-l-brun"}`}>
      <span className="absolute right-3 top-3 flex items-center gap-1.5 text-beige-fonce">
        {icon}
        <InfoTip text={kpi.definition} label={kpi.label} />
      </span>
      {onClick ? (
        <button onClick={onClick} className="pr-10 text-left focus-visible:outline-2 focus-visible:outline-beige" title="Voir les projets concernés">
          {contenu}
        </button>
      ) : <div className="pr-10">{contenu}</div>}
    </div>
  );
}
