/** Carte d'indicateur : valeur calculée par le backend, définition au survol / au focus. */
import { HelpCircle } from "lucide-react";
import type { ReactNode } from "react";
import type { Kpi } from "../api/types";
import { fmtKpi } from "../lib/format";

export default function KpiCard({ kpi, icon, accent = false, onClick }:
  { kpi: Kpi; icon?: ReactNode; accent?: boolean; onClick?: () => void }) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag onClick={onClick} title={kpi.definition}
      className={`carte group animate-apparition flex w-full flex-col gap-2 p-4 text-left transition-shadow ${onClick ? "cursor-pointer hover:shadow-md focus-visible:outline-2 focus-visible:outline-beige" : ""} ${accent ? "border-l-4 border-l-alerte" : "border-l-4 border-l-brun"}`}>
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-medium text-muted">{kpi.label}</span>
        <span className="text-beige-fonce">{icon ?? <HelpCircle className="size-4" aria-hidden />}</span>
      </div>
      <span className={`text-xl font-bold leading-tight tabular-nums sm:text-2xl ${accent ? "text-alerte" : "text-profond"}`}>{fmtKpi(kpi.value, kpi.unit)}</span>
      <span className="sr-only">{kpi.definition}</span>
    </Tag>
  );
}
