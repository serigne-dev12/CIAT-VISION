/** Module 4 (V2) – Centre d'alertes intelligentes. */
import { Archive, ArchiveRestore, BellRing, CheckCheck, ChevronDown, Eye, EyeOff, RefreshCw, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { AlertItem } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Card, ConfirmDialog, Empty, ErrorBox, Pagination, Spinner, useToast } from "../components/ui";
import { fmtDateHeure, peut } from "../lib/format";
import { errMsg, useApi } from "../lib/hooks";

const STYLE_NIVEAU: Record<string, { pastille: string; bord: string }> = {
  Critique: { pastille: "bg-red-600 text-white", bord: "border-l-red-600" },
  "Élevé": { pastille: "bg-orange-500 text-white", bord: "border-l-orange-500" },
  Moyen: { pastille: "bg-amber-300 text-profond", bord: "border-l-amber-400" },
  Information: { pastille: "bg-stone-200 text-stone-700", bord: "border-l-stone-400" },
};
const ONGLETS = [{ k: "actives", l: "Actives" }, { k: "archivees", l: "Archivées" }, { k: "historique", l: "Historique (résolues)" }] as const;

const PAR_PAGE = 20;

interface Reponse { items: AlertItem[]; total: number; levels: string[]; types: string[]; generated_at: string | null }

export default function AlertsPage() {
  const { user } = useAuth();
  const toast = useToast();
  const [sp] = useSearchParams();
  const [statut, setStatut] = useState<(typeof ONGLETS)[number]["k"]>("actives");
  const [niveau, setNiveau] = useState(sp.get("level") ?? "");
  const [type, setType] = useState("");
  const [nonLues, setNonLues] = useState(false);
  const [ouverte, setOuverte] = useState<number | null>(null);
  const [suppr, setSuppr] = useState<AlertItem | null>(null);
  const [page, setPage] = useState(1);
  useEffect(() => setPage(1), [statut, niveau, type, nonLues]);
  const editeur = peut(user?.role, "modifier");
  const r = useApi(() => api.get<Reponse>("/alerts", { statut, level: niveau || undefined, type: type || undefined, unread_only: nonLues || undefined }),
    [statut, niveau, type, nonLues]);
  const tous = useApi(() => api.get<Reponse>("/alerts", { statut }), [statut]);

  const action = async (fn: () => Promise<unknown>, ok?: string) => {
    try { await fn(); if (ok) toast("succes", ok); r.reload(); tous.reload(); } catch (e) { toast("erreur", errMsg(e)); }
  };
  // Page bornée : archiver ou supprimer la dernière alerte d'une page ne doit pas laisser une page vide
  const nbPages = Math.max(1, Math.ceil((r.data?.items.length ?? 0) / PAR_PAGE));
  const pageEff = Math.min(page, nbPages);
  const compte = (n: string) => (tous.data?.items ?? []).filter((a) => a.level === n).length;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="titre-page flex items-center gap-2"><BellRing className="size-6 text-alerte" /> Centre d'alertes</h1>
          <p className="text-sm text-muted">Alertes détectées automatiquement par des règles appliquées aux données réelles de la plateforme.
            {r.data?.generated_at && <> Dernière analyse : {fmtDateHeure(r.data.generated_at)}.</>}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-secondaire" onClick={() => action(() => api.post("/alerts/read-all"), "Toutes les alertes actives sont marquées comme lues.")}>
            <CheckCheck className="size-4" /> Tout marquer comme lu
          </button>
          {editeur && <button className="btn-principal" onClick={() => action(() => api.post("/alerts/refresh"), "Alertes recalculées.")}>
            <RefreshCw className="size-4" /> Recalculer
          </button>}
        </div>
      </div>

      <div className="flex gap-1 overflow-x-auto border-b border-ligne" role="tablist">
        {ONGLETS.map(({ k, l }) => (
          <button key={k} role="tab" aria-selected={statut === k} onClick={() => setStatut(k)}
            className={`whitespace-nowrap border-b-2 px-4 py-2 text-sm ${statut === k ? "border-brun font-semibold text-profond" : "border-transparent text-muted hover:text-texte"}`}>{l}</button>
        ))}
      </div>

      <Card>
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <button className={`btn-secondaire !py-1 ${niveau === "" ? "!border-brun !bg-beige-pale" : ""}`} onClick={() => setNiveau("")}>Toutes ({tous.data?.total ?? "…"})</button>
          {(tous.data?.levels ?? ["Critique", "Élevé", "Moyen", "Information"]).map((n) => (
            <button key={n} className={`btn-secondaire !py-1 ${niveau === n ? "!border-brun !bg-beige-pale" : ""}`} onClick={() => setNiveau(n)}>
              <span className={`size-2 rounded-full ${STYLE_NIVEAU[n]?.pastille.split(" ")[0]}`} /> {n} ({compte(n)})
            </button>
          ))}
          <select className="champ !w-auto !py-1" value={type} onChange={(e) => setType(e.target.value)} aria-label="Type d'alerte">
            <option value="">Tous les types</option>{(tous.data?.types ?? []).map((t) => <option key={t}>{t}</option>)}
          </select>
          {statut === "actives" && (
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={nonLues} onChange={(e) => setNonLues(e.target.checked)} /> Non lues seulement</label>
          )}
        </div>

        {r.error ? <ErrorBox message={r.error} onRetry={r.reload} /> : !r.data ? <Spinner /> : r.data.items.length === 0 ? (
          <Empty title="Aucune alerte">{statut === "actives" ? "Aucune situation ne déclenche d'alerte sur ces critères." : "Rien dans cette catégorie."}</Empty>
        ) : (
          <>
          <ul className="space-y-2">
            {r.data.items.slice((pageEff - 1) * PAR_PAGE, pageEff * PAR_PAGE).map((a) => (
              <li key={a.id} className={`rounded-lg border border-ligne border-l-4 ${STYLE_NIVEAU[a.level]?.bord ?? ""} ${a.is_read ? "bg-white" : "bg-beige-pale/40"}`}>
                <div className="flex flex-wrap items-start gap-3 p-3">
                  <span className={`rounded px-2 py-0.5 text-xs font-semibold ${STYLE_NIVEAU[a.level]?.pastille ?? ""}`}>{a.level}</span>
                  <div className="min-w-0 flex-[1_1_14rem]">
                    <p className={`text-sm ${a.is_read ? "" : "font-semibold"} text-profond`}>{a.title}</p>
                    <p className="text-xs text-muted">{a.type} · détectée le {fmtDateHeure(a.detected_at)}
                      {a.resolved_at && <> · résolue le {fmtDateHeure(a.resolved_at)}</>}
                      {a.project_id && <> · <Link className="btn-lien !text-xs" to={`/projets/${a.project_id}`}>voir le projet</Link></>}
                      {a.objective_id && <> · <Link className="btn-lien !text-xs" to="/objectifs">voir les objectifs</Link></>}</p>
                  </div>
                  <div className="ml-auto flex items-center gap-1">
                    {statut === "actives" && (a.is_read
                      ? <button className="rounded p-1.5 hover:bg-gris" title="Marquer comme non lue" aria-label="Marquer comme non lue" onClick={() => action(() => api.post(`/alerts/${a.id}/unread`))}><EyeOff className="size-4" /></button>
                      : <button className="rounded p-1.5 hover:bg-gris" title="Marquer comme lue" aria-label="Marquer comme lue" onClick={() => action(() => api.post(`/alerts/${a.id}/read`))}><Eye className="size-4" /></button>)}
                    {editeur && statut === "actives" && <button className="rounded p-1.5 hover:bg-gris" title="Archiver" aria-label="Archiver" onClick={() => action(() => api.post(`/alerts/${a.id}/archive`), "Alerte archivée.")}><Archive className="size-4" /></button>}
                    {editeur && statut === "archivees" && <button className="rounded p-1.5 hover:bg-gris" title="Désarchiver" aria-label="Désarchiver" onClick={() => action(() => api.post(`/alerts/${a.id}/unarchive`), "Alerte réactivée.")}><ArchiveRestore className="size-4" /></button>}
                    {user?.role === "admin" && <button className="rounded p-1.5 text-danger hover:bg-red-50" title="Supprimer" aria-label="Supprimer" onClick={() => setSuppr(a)}><Trash2 className="size-4" /></button>}
                    <button className="rounded p-1.5 hover:bg-gris" aria-expanded={ouverte === a.id} aria-label="Détails"
                      onClick={() => { setOuverte(ouverte === a.id ? null : a.id); if (!a.is_read && statut === "actives") action(() => api.post(`/alerts/${a.id}/read`)); }}>
                      <ChevronDown className={`size-4 transition-transform ${ouverte === a.id ? "rotate-180" : ""}`} />
                    </button>
                  </div>
                </div>
                {ouverte === a.id && (
                  <dl className="grid gap-2 border-t border-ligne px-3 py-3 text-sm sm:grid-cols-3">
                    <div><dt className="text-xs font-semibold text-muted">Problème détecté</dt><dd>{a.problem}</dd></div>
                    <div><dt className="text-xs font-semibold text-muted">Explication</dt><dd>{a.explanation}</dd></div>
                    <div><dt className="text-xs font-semibold text-muted">Action recommandée</dt><dd>{a.recommended_action}</dd></div>
                  </dl>
                )}
              </li>
            ))}
          </ul>
          <Pagination page={pageEff} pageSize={PAR_PAGE} total={r.data.items.length} onChange={setPage} />
          </>
        )}
      </Card>
      <ConfirmDialog open={!!suppr} title="Supprimer l'alerte" danger confirmLabel="Supprimer" onCancel={() => setSuppr(null)}
        message={<>Supprimer définitivement l'alerte « {suppr?.title} » ? Si la situation persiste, elle sera de nouveau détectée.</>}
        onConfirm={() => { const a = suppr!; setSuppr(null); action(() => api.del(`/alerts/${a.id}`), "Alerte supprimée."); }} />
    </div>
  );
}
