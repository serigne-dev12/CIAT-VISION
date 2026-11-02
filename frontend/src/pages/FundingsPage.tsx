/** Module 6 – Suivi des financements. */
import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Charts, Funding, Kpi } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { FundingArea, HBars } from "../components/charts";
import { useData } from "../components/DataContext";
import FiltersBar from "../components/FiltersBar";
import KpiCard from "../components/KpiCard";
import { Card, ConfirmDialog, Empty, ErrorBox, Pagination, Spinner, useToast } from "../components/ui";
import { fmtDate, fmtFCFA, peut } from "../lib/format";
import { errMsg, useApi, useDebounced } from "../lib/hooks";
import FundingForm from "./FundingForm";

interface Reponse {
  items: Funding[]; total: number; summary: Kpi[];
  by_source: Charts["fundings_by_source"]; by_domain: Charts["fundings_by_domain"]; monthly: Charts["fundings_monthly"];
}

export default function FundingsPage() {
  const { user } = useAuth();
  const { params } = useData();
  const toast = useToast();
  const edit = peut(user?.role, "modifier");
  const [q, setQ] = useState("");
  const [source, setSource] = useState("");
  const [statut, setStatut] = useState("");
  const [page, setPage] = useState(1);
  const [form, setForm] = useState<Funding | "new" | null>(null);
  const [suppr, setSuppr] = useState<Funding | null>(null);
  const dq = useDebounced(q);
  const key = JSON.stringify(params);
  useEffect(() => { setPage(1); }, [dq, source, statut, key]);
  const r = useApi(() => api.get<Reponse>("/fundings", { ...params, q: dq, source, funding_status: statut, page, page_size: 15 }),
    [key, dq, source, statut, page]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><h1 className="titre-page">Financements</h1><p className="text-sm text-muted">Montants demandés, accordés et reçus par les projets.</p></div>
        {edit && <button className="btn-principal" onClick={() => setForm("new")}><Plus className="size-4" /> Enregistrer un financement</button>}
      </div>
      <FiltersBar />
      {r.error ? <ErrorBox message={r.error} onRetry={r.reload} /> : !r.data ? <Spinner /> : (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
            {r.data.summary.filter((k) => k.key !== "avg_funding").map((k) => <KpiCard key={k.key} kpi={k} />)}
          </div>
          <div className="grid gap-5 xl:grid-cols-2">
            <Card title="Évolution des financements"><FundingArea data={r.data.monthly} /></Card>
            <Card title="Montants accordés par source"><HBars data={r.data.by_source} labelKey="label" valueKey="granted" money /></Card>
          </div>
          <Card title="Liste des financements">
            <div className="mb-3 flex flex-wrap gap-2">
              <div className="relative min-w-0 flex-1 basis-56">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
                <input className="champ pl-9" placeholder="Projet ou partenaire…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Rechercher" />
              </div>
              <select className="champ !w-auto" value={source} onChange={(e) => setSource(e.target.value)} aria-label="Source">
                <option value="">Toutes les sources</option>{["Subvention", "Prêt d'honneur", "Prix de concours", "Investisseur", "Fonds propres", "Partenaire"].map((s) => <option key={s}>{s}</option>)}
              </select>
              <select className="champ !w-auto" value={statut} onChange={(e) => setStatut(e.target.value)} aria-label="Statut du financement">
                <option value="">Tous les statuts</option>{["Demandé", "Accordé", "Partiellement reçu", "Reçu", "Refusé"].map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
            {r.data.items.length === 0 ? <Empty title="Aucun financement" /> : (
              <div className="-mx-4 overflow-x-auto">
                <table className="tableau min-w-[900px]">
                  <thead><tr><th>Projet</th><th>Source</th><th>Statut</th><th className="text-right">Demandé</th><th className="text-right">Accordé</th>
                    <th className="text-right">Reçu</th><th className="text-right">Reste à recevoir</th><th>Demande</th>{edit && <th />}</tr></thead>
                  <tbody>{r.data.items.map((x) => (
                    <tr key={x.id}>
                      <td className="max-w-[240px]"><Link to={`/projets/${x.project_id}`} className="line-clamp-1 font-medium text-profond hover:underline">{x.project_name}</Link><span className="text-xs text-muted">{x.cohort}</span></td>
                      <td>{x.source_type}{x.partner && <span className="block max-w-[180px] truncate text-xs text-muted">{x.partner}</span>}</td>
                      <td className="whitespace-nowrap">{x.status}</td>
                      <td className="text-right tabular-nums">{fmtFCFA(x.amount_requested)}</td>
                      <td className="text-right tabular-nums">{fmtFCFA(x.amount_granted)}</td>
                      <td className="text-right tabular-nums">{fmtFCFA(x.amount_received)}</td>
                      <td className={`text-right tabular-nums ${x.remaining > 0 ? "font-medium text-alerte" : ""}`}>{fmtFCFA(x.remaining)}</td>
                      <td className="whitespace-nowrap">{fmtDate(x.request_date)}</td>
                      {edit && <td className="whitespace-nowrap text-right">
                        <button className="rounded p-1 hover:bg-gris" onClick={() => setForm(x)} aria-label="Modifier"><Pencil className="size-4" /></button>
                        <button className="rounded p-1 text-danger hover:bg-red-50" onClick={() => setSuppr(x)} aria-label="Supprimer"><Trash2 className="size-4" /></button>
                      </td>}
                    </tr>))}
                  </tbody>
                </table>
              </div>
            )}
            <Pagination page={page} pageSize={15} total={r.data.total} onChange={setPage} />
          </Card>
        </>
      )}
      <FundingForm open={form !== null} funding={form === "new" ? null : form} onClose={() => setForm(null)} onSaved={() => { setForm(null); r.reload(); }} />
      <ConfirmDialog open={!!suppr} title="Supprimer le financement" danger confirmLabel="Supprimer"
        message={<>Supprimer définitivement ce financement de <b>{suppr && fmtFCFA(suppr.amount_requested)}</b> ({suppr?.project_name}) ?</>}
        onCancel={() => setSuppr(null)}
        onConfirm={async () => {
          try { await api.del(`/fundings/${suppr!.id}`); toast("succes", "Financement supprimé."); setSuppr(null); r.reload(); } catch (e) { toast("erreur", errMsg(e)); }
        }} />
    </div>
  );
}
