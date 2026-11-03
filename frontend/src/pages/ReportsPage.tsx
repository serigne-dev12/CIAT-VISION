/** Module 8 – Rapports et exportations (PDF, Excel, CSV). */
import { FileSpreadsheet, FileText, FileType2, Sparkles } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client";
import { useData } from "../components/DataContext";
import type { Page, ProjectItem } from "../api/types";
import { errMsg, useApi, useDebounced } from "../lib/hooks";
import FiltersBar from "../components/FiltersBar";
import { Card, useToast } from "../components/ui";

const TYPES = [
  { key: "global", title: "Rapport général du CIAT", desc: "Indicateurs clés, statuts, domaines, candidatures, cohortes, retards et risques." },
  { key: "domains", title: "Rapport par domaine", desc: "Performances comparées des domaines d'innovation." },
  { key: "cohorts", title: "Rapport par cohorte", desc: "Comparaison des cohortes : sélection, réussite, retards, financement moyen." },
  { key: "project", title: "Rapport par projet", desc: "Fiche détaillée d'un projet : jalons, financements, risques, alertes, historique." },
  { key: "fundings", title: "Rapport financier", desc: "Montants demandés, accordés, reçus par source et par domaine." },
  { key: "alerts", title: "Rapport des alertes", desc: "Alertes actives par niveau et par type, avec les actions recommandées." },
  { key: "performance", title: "Rapport de performance", desc: "Taux de sélection, d'achèvement et de retard ; progression ; risques." },
  { key: "projects", title: "Liste des projets", desc: "Tous les projets du périmètre avec statut, progression, budget et financement." },
  { key: "delays", title: "Rapport des retards", desc: "Projets en retard, ampleur du retard et jalons manqués." },
];

export default function ReportsPage() {
  const { body, describe } = useData();
  const [projetId, setProjetId] = useState("");
  const [rech, setRech] = useState("");
  const dRech = useDebounced(rech);
  const projets = useApi(() => api.get<Page<ProjectItem>>("/projects", { q: dRech, page_size: 15, sort: "name", order: "asc" }), [dRech]);
  const toast = useToast();
  const [type, setType] = useState("global");
  const [commentaire, setCommentaire] = useState("");
  const [mode, setMode] = useState<string | null>(null);
  const [occupe, setOccupe] = useState<string | null>(null);

  const proposer = async () => {
    setOccupe("commentaire");
    try {
      const r = await api.post<{ commentary: string; mode: string }>("/reports/commentary", { report_type: type, filters: body, project_id: type === "project" && projetId ? Number(projetId) : null });
      setCommentaire(r.commentary);
      setMode(r.mode);
    } catch (e) { toast("erreur", errMsg(e)); } finally { setOccupe(null); }
  };

  const exporter = async (format: "pdf" | "xlsx" | "csv") => {
    if (type === "project" && !projetId) { toast("erreur", "Choisissez le projet du rapport."); return; }
    setOccupe(format);
    try {
      await api.download("/reports/generate", { report_type: type, format, filters: body, project_id: type === "project" && projetId ? Number(projetId) : null, commentary: commentaire.trim() || null }, `rapport.${format}`);
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
      {type === "project" && (
        <Card title="Projet du rapport">
          <div className="grid gap-2 sm:grid-cols-2">
            <input className="champ" placeholder="Rechercher un projet…" value={rech} onChange={(e) => setRech(e.target.value)} aria-label="Rechercher un projet" />
            <select className="champ" value={projetId} onChange={(e) => setProjetId(e.target.value)} aria-label="Projet">
              <option value="">Choisir un projet…</option>
              {(projets.data?.items ?? []).map((p) => <option key={p.id} value={p.id}>{p.name} ({p.cohort})</option>)}
            </select>
          </div>
        </Card>
      )}
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
