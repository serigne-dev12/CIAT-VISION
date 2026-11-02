/** Module 8 – Rapports et exportations (PDF, Excel, CSV). */
import { FileSpreadsheet, FileText, FileType2, Sparkles } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client";
import { filtersToBody, useData } from "../components/DataContext";
import FiltersBar from "../components/FiltersBar";
import { Card, useToast } from "../components/ui";
import { errMsg } from "../lib/hooks";

const TYPES = [
  { key: "global", title: "Rapport global des activités", desc: "Indicateurs clés, statuts, domaines, candidatures, cohortes et retards." },
  { key: "projects", title: "Rapport des projets", desc: "Liste détaillée des projets avec statut, progression, budget et financement." },
  { key: "cohorts", title: "Rapport des cohortes", desc: "Comparaison des cohortes : sélection, réussite, retards, financement moyen." },
  { key: "fundings", title: "Rapport des financements", desc: "Montants demandés, accordés, reçus par source et par domaine." },
  { key: "performance", title: "Rapport des performances", desc: "Taux de sélection, d'achèvement et de retard ; progression des projets." },
  { key: "delays", title: "Rapport des retards", desc: "Projets en retard, ampleur du retard et jalons manqués." },
];

export default function ReportsPage() {
  const { filters, describe } = useData();
  const toast = useToast();
  const [type, setType] = useState("global");
  const [commentaire, setCommentaire] = useState("");
  const [mode, setMode] = useState<string | null>(null);
  const [occupe, setOccupe] = useState<string | null>(null);

  const proposer = async () => {
    setOccupe("commentaire");
    try {
      const r = await api.post<{ commentary: string; mode: string }>("/reports/commentary", { report_type: type, filters: filtersToBody(filters) });
      setCommentaire(r.commentary);
      setMode(r.mode);
    } catch (e) { toast("erreur", errMsg(e)); } finally { setOccupe(null); }
  };

  const exporter = async (format: "pdf" | "xlsx" | "csv") => {
    setOccupe(format);
    try {
      await api.download("/reports/generate", { report_type: type, format, filters: filtersToBody(filters), commentary: commentaire.trim() || null }, `rapport.${format}`);
      toast("succes", `Rapport ${format.toUpperCase()} généré.`);
    } catch (e) { toast("erreur", errMsg(e)); } finally { setOccupe(null); }
  };

  return (
    <div className="space-y-5">
      <div><h1 className="titre-page">Rapports et exportations</h1><p className="text-sm text-muted">Les rapports reprennent exactement le périmètre filtré : {describe}.</p></div>
      <FiltersBar />
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card title="1. Type de rapport">
          <div className="grid gap-2 sm:grid-cols-2">
            {TYPES.map((t) => (
              <label key={t.key} className={`cursor-pointer rounded-lg border p-3 transition-colors ${type === t.key ? "border-brun bg-beige-pale" : "border-ligne hover:bg-gris"}`}>
                <input type="radio" name="type" className="sr-only" checked={type === t.key} onChange={() => setType(t.key)} />
                <p className="text-sm font-semibold text-profond">{t.title}</p>
                <p className="mt-0.5 text-xs text-muted">{t.desc}</p>
              </label>
            ))}
          </div>
        </Card>
        <Card title="2. Commentaire analytique (facultatif)"
          actions={<button className="btn-accent !py-1" onClick={proposer} disabled={!!occupe}><Sparkles className="size-4" /> {occupe === "commentaire" ? "Rédaction…" : "Proposer un commentaire"}</button>}>
          <textarea className="champ min-h-48" value={commentaire} onChange={(e) => setCommentaire(e.target.value)} maxLength={6000}
            placeholder="Rédigez votre analyse ou demandez une proposition, puis relisez-la avant l'export." aria-label="Commentaire analytique" />
          <p className="mt-1 text-xs text-muted">{mode ? `Proposition ${mode === "IA" ? "rédigée par l'IA" : "générée automatiquement à partir des indicateurs"} : relisez et corrigez avant l'export. ` : ""}
            Le commentaire figure dans les rapports PDF et Excel.</p>
        </Card>
      </div>
      <Card title="3. Exporter">
        <div className="flex flex-wrap gap-3">
          <button className="btn-principal" onClick={() => exporter("pdf")} disabled={!!occupe}><FileText className="size-4" /> {occupe === "pdf" ? "Génération…" : "PDF"}</button>
          <button className="btn-secondaire" onClick={() => exporter("xlsx")} disabled={!!occupe}><FileSpreadsheet className="size-4" /> {occupe === "xlsx" ? "Génération…" : "Excel"}</button>
          <button className="btn-secondaire" onClick={() => exporter("csv")} disabled={!!occupe}><FileType2 className="size-4" /> {occupe === "csv" ? "Génération…" : "CSV"}</button>
        </div>
        <p className="mt-3 text-xs text-muted">Le PDF contient le logo CIAT VISION, le titre, la période analysée, les indicateurs, les graphiques, le commentaire et la date de génération.</p>
      </Card>
    </div>
  );
}
