/** Module 10 – Importation de données : modèle, dépôt, prévisualisation, confirmation. */
import { CheckCircle2, Download, FileUp, XCircle } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client";
import { useData } from "../components/DataContext";
import { Card, ConfirmDialog, ErrorBox, Spinner, useToast } from "../components/ui";
import { errMsg, useApi } from "../lib/hooks";

interface Entite { key: string; label: string; columns: { name: string; required: boolean; kind: string; choices: string[] | null }[] }
interface Bilan { imported: number; skipped: number; fichier: string; report: { line: number; status: string; reason: string }[] }
interface Apercu {
  missing_columns: string[]; total_rows: number; valid_rows: number; error_rows: number; duplicate_rows: number;
  rows: { line: number; valid: boolean; errors: string[]; duplicate: string | null; data: Record<string, unknown> }[];
}

export default function ImportPage() {
  const toast = useToast();
  const { reloadRefs } = useData();
  const entites = useApi(() => api.get<Entite[]>("/imports/entities"), []);
  const [entite, setEntite] = useState("projects");
  const [fichier, setFichier] = useState<File | null>(null);
  const [apercu, setApercu] = useState<Apercu | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [occupe, setOccupe] = useState(false);
  const [confirmer, setConfirmer] = useState(false);
  const [bilan, setBilan] = useState<Bilan | null>(null);
  const def = entites.data?.find((e) => e.key === entite);

  const analyser = async (f: File) => {
    setFichier(f); setApercu(null); setErreur(null); setOccupe(true); setBilan(null);
    const fd = new FormData();
    fd.append("entity", entite);
    fd.append("file", f);
    try { setApercu(await api.form<Apercu>("/imports/preview", fd)); } catch (e) { setErreur(errMsg(e)); } finally { setOccupe(false); }
  };

  const importer = async () => {
    if (!fichier || !apercu) return;
    setOccupe(true);
    const fd = new FormData();
    fd.append("entity", entite);
    fd.append("confirm", "true");
    fd.append("ignore_invalid", String(apercu.valid_rows < apercu.total_rows));
    fd.append("file", fichier);
    try {
      const r = await api.form<Omit<Bilan, "fichier">>("/imports/commit", fd);
      toast("succes", `${r.imported} ligne(s) importée(s), ${r.skipped} ignorée(s).`);
      setBilan({ ...r, fichier: fichier.name });
      setApercu(null); setFichier(null); setConfirmer(false);
      reloadRefs();
    } catch (e) { toast("erreur", errMsg(e)); setConfirmer(false); } finally { setOccupe(false); }
  };

  const colonnes = def?.columns.map((c) => c.name) ?? [];

  return (
    <div className="space-y-5">
      <div><h1 className="titre-page">Importation des données</h1>
        <p className="text-sm text-muted">Intégrez des fichiers Excel (.xlsx) ou CSV. Rien n'est enregistré avant votre confirmation.</p></div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        <Card title="1. Type de données et modèle">
          {entites.error ? <ErrorBox message={entites.error} /> : !entites.data ? <Spinner /> : (
            <div className="space-y-3">
              <select className="champ" value={entite} onChange={(e) => { setEntite(e.target.value); setApercu(null); setFichier(null); }} aria-label="Type de données">
                {entites.data.map((e) => <option key={e.key} value={e.key}>{e.label}</option>)}
              </select>
              <div className="flex flex-wrap gap-2">
                <button className="btn-secondaire" onClick={() => api.download(`/imports/template/${entite}?format=xlsx`).catch((e) => toast("erreur", errMsg(e)))}><Download className="size-4" /> Modèle Excel</button>
                <button className="btn-secondaire" onClick={() => api.download(`/imports/template/${entite}?format=csv`).catch((e) => toast("erreur", errMsg(e)))}><Download className="size-4" /> Modèle CSV</button>
              </div>
              <div className="text-xs text-muted">
                <p className="mb-1 font-medium text-texte">Colonnes attendues (* obligatoire) :</p>
                <ul className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">{def?.columns.map((c) => <li key={c.name}><code>{c.name}</code>{c.required && " *"}</li>)}</ul>
                {entite === "fundings" && <p className="mt-2">Le projet doit déjà exister dans la cohorte indiquée.</p>}
                {entite === "projects" && <p className="mt-2">Le domaine et la cohorte doivent exister (importez d'abord les cohortes).</p>}
              </div>
            </div>
          )}
        </Card>

        <Card title="2. Fichier à importer">
          <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-ligne p-8 text-center hover:border-beige hover:bg-beige-pale/40"
            onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) analyser(f); }}>
            <FileUp className="size-8 text-beige-fonce" />
            <span className="text-sm font-medium">{fichier ? fichier.name : "Déposez un fichier ici ou cliquez pour choisir"}</span>
            <span className="text-xs text-muted">.xlsx ou .csv · 5 Mo et 5 000 lignes maximum</span>
            <input type="file" className="sr-only" accept=".xlsx,.csv" onChange={(e) => { const f = e.target.files?.[0]; if (f) analyser(f); e.target.value = ""; }} />
          </label>
          {occupe && !confirmer && <Spinner label="Analyse du fichier…" />}
          {erreur && <div className="mt-3"><ErrorBox message={erreur} /></div>}
        </Card>
      </div>

      {apercu && (
        <Card title="3. Prévisualisation et contrôle"
          actions={apercu.valid_rows > 0 && !apercu.missing_columns.length ? <button className="btn-principal" onClick={() => setConfirmer(true)}>Importer {apercu.valid_rows} ligne(s) valide(s)</button> : undefined}>
          {apercu.missing_columns.length > 0 ? (
            <ErrorBox message={`Colonnes obligatoires manquantes : ${apercu.missing_columns.join(", ")}. Utilisez le modèle fourni.`} />
          ) : (
            <>
              <div className="mb-3 flex flex-wrap gap-3 text-sm">
                <span className="rounded-md bg-gris px-3 py-1.5">Lignes : <b>{apercu.total_rows}</b></span>
                <span className="rounded-md bg-emerald-50 px-3 py-1.5 text-emerald-900">Valides : <b>{apercu.valid_rows}</b></span>
                <span className="rounded-md bg-red-50 px-3 py-1.5 text-red-900">En erreur : <b>{apercu.error_rows}</b></span>
                <span className="rounded-md bg-amber-50 px-3 py-1.5 text-amber-900">Doublons : <b>{apercu.duplicate_rows}</b></span>
              </div>
              <div className="-mx-4 max-h-[480px] overflow-auto">
                <table className="tableau min-w-[900px]">
                  <thead className="sticky top-0"><tr><th>Ligne</th><th>Contrôle</th>{colonnes.slice(0, 7).map((c) => <th key={c}>{c}</th>)}</tr></thead>
                  <tbody>{apercu.rows.map((r) => (
                    <tr key={r.line} className={r.valid ? "" : r.errors.length ? "bg-red-50/60" : "bg-amber-50/60"}>
                      <td className="tabular-nums">{r.line}</td>
                      <td className="min-w-[220px] text-xs">{r.valid ? <span className="inline-flex items-center gap-1 text-emerald-800"><CheckCircle2 className="size-4" /> Valide</span>
                        : <span className="inline-flex items-start gap-1 text-red-900"><XCircle className="mt-0.5 size-4 shrink-0" /> {[...r.errors, r.duplicate].filter(Boolean).join(" ; ")}</span>}</td>
                      {colonnes.slice(0, 7).map((c) => <td key={c} className="max-w-[180px] truncate text-xs">{r.data[c] === null || r.data[c] === undefined ? "—" : String(r.data[c])}</td>)}
                    </tr>))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Card>
      )}

      {bilan && (
        <Card title="4. Rapport final d'importation" subtitle={`Fichier « ${bilan.fichier} » – ${bilan.imported} ligne(s) importée(s), ${bilan.skipped} ignorée(s)`}
          actions={<button className="btn-secondaire !py-1" onClick={() => {
            const lignes = ["Ligne;Statut;Motif", ...bilan.report.map((x) => `${x.line};${x.status};"${x.reason.replace(/"/g, '""')}"`)];
            const csv = "﻿" + lignes.join("\n");  // BOM : accents corrects à l'ouverture dans Excel
            const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
            const a = document.createElement("a"); a.href = url; a.download = `rapport_import_${bilan.fichier.replace(/\.[^.]+$/, "")}.csv`; a.click();
            setTimeout(() => URL.revokeObjectURL(url), 2000);
          }}><Download className="size-4" /> Télécharger (CSV)</button>}>
          <div className="-mx-4 max-h-80 overflow-auto">
            <table className="tableau"><thead><tr><th>Ligne</th><th>Statut</th><th>Motif</th></tr></thead>
              <tbody>{bilan.report.map((x) => (
                <tr key={x.line}><td className="tabular-nums">{x.line}</td>
                  <td className={x.status === "Importée" ? "text-emerald-800" : "text-red-900"}>{x.status}</td>
                  <td className="text-xs">{x.reason || "—"}</td></tr>))}
              </tbody></table>
          </div>
        </Card>
      )}

      <ConfirmDialog open={confirmer} title="Confirmer l'importation" confirmLabel="Importer" busy={occupe} onCancel={() => setConfirmer(false)} onConfirm={importer}
        message={apercu && <>Vous allez importer <b>{apercu.valid_rows}</b> ligne(s) valide(s).
          {apercu.valid_rows < apercu.total_rows && <> Les <b>{apercu.total_rows - apercu.valid_rows}</b> ligne(s) en erreur ou en double seront ignorées.</>} L'opération est enregistrée en une seule fois et tracée dans le journal.</>} />
    </div>
  );
}
