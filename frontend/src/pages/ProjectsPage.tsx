/** Module 3 – Liste des projets : recherche, filtres, tri, pagination, création. */
import { AlarmClock, ArrowDownUp, Plus, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { Page, ProjectItem } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useData } from "../components/DataContext";
import FiltersBar from "../components/FiltersBar";
import { Card, Empty, ErrorBox, Pagination, ProgressBar, Spinner, StatusBadge } from "../components/ui";
import { fmtDate, fmtFCFA, peut } from "../lib/format";
import { useApi, useDebounced } from "../lib/hooks";
import ProjectForm from "./ProjectForm";

const TRIS = [
  { v: "updated_at", l: "Dernière mise à jour" }, { v: "name", l: "Nom" }, { v: "progress", l: "Progression" },
  { v: "deadline", l: "Date limite" }, { v: "budget", l: "Budget" },
];

export default function ProjectsPage() {
  const { user } = useAuth();
  const { params, filters, setFilters } = useData();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("updated_at");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [retard, setRetard] = useState(sp.get("delayed") === "1");
  const [form, setForm] = useState(false);
  const dq = useDebounced(q);

  // Liens depuis le tableau de bord : ?status=… ou ?delayed=1
  useEffect(() => {
    const s = sp.get("status");
    if (s && s !== filters.status) setFilters({ ...filters, status: s });
    if (s || sp.get("delayed")) setSp({}, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => { setPage(1); }, [dq, retard, JSON.stringify(params), sort, order]);

  const liste = useApi(() => api.get<Page<ProjectItem>>("/projects", {
    ...params, q: dq, delayed_only: retard || undefined, sort, order, page, page_size: 20,
  }), [JSON.stringify(params), dq, retard, sort, order, page]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="titre-page">Projets</h1>
          <p className="text-sm text-muted">Suivi des candidatures et des projets accompagnés par le CIAT.</p>
        </div>
        {peut(user?.role, "modifier") && <button className="btn-principal" onClick={() => setForm(true)}><Plus className="size-4" /> Nouveau projet</button>}
      </div>
      <FiltersBar />

      <Card>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <div className="relative min-w-0 flex-1 basis-60">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
            <input className="champ pl-9" placeholder="Rechercher un projet, une description, un porteur…" value={q}
              onChange={(e) => setQ(e.target.value)} aria-label="Rechercher" maxLength={100} />
          </div>
          <label className={`btn-secondaire cursor-pointer ${retard ? "!border-alerte !text-alerte" : ""}`}>
            <input type="checkbox" className="sr-only" checked={retard} onChange={(e) => setRetard(e.target.checked)} />
            <AlarmClock className="size-4" /> En retard uniquement
          </label>
          <select className="champ !w-auto" value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Trier par">
            {TRIS.map((t) => <option key={t.v} value={t.v}>{t.l}</option>)}
          </select>
          <button className="btn-secondaire !px-2.5" onClick={() => setOrder(order === "asc" ? "desc" : "asc")}
            aria-label={`Ordre ${order === "asc" ? "croissant" : "décroissant"}`} title="Inverser l'ordre"><ArrowDownUp className="size-4" /></button>
        </div>

        {liste.error ? <ErrorBox message={liste.error} onRetry={liste.reload} /> : !liste.data ? <Spinner /> :
          liste.data.items.length === 0 ? <Empty title="Aucun projet trouvé">Modifiez la recherche ou les filtres.</Empty> : (
            <>
              {/* Tableau (ordinateur) */}
              <div className="-mx-4 hidden overflow-x-auto md:block">
                <table className="tableau">
                  <thead><tr><th>Projet</th><th>Domaine</th><th>Cohorte</th><th>Statut</th><th>Progression</th>
                    <th className="text-right">Budget</th><th className="text-right">Financement obtenu</th><th>Date limite</th></tr></thead>
                  <tbody>
                    {liste.data.items.map((p) => (
                      <tr key={p.id} className="cursor-pointer" onClick={() => nav(`/projets/${p.id}`)}>
                        <td className="max-w-[280px]">
                          <span className="line-clamp-1 font-medium text-profond">{p.name}</span>
                          <span className="text-xs text-muted">{p.leader}</span>
                        </td>
                        <td className="max-w-[160px] truncate text-xs">{p.domain}</td>
                        <td className="whitespace-nowrap">{p.cohort}</td>
                        <td><StatusBadge status={p.status} />{p.is_delayed && <span className="ml-1 text-xs font-semibold text-alerte">· retard</span>}</td>
                        <td><ProgressBar value={p.progress_pct} late={p.is_delayed} /></td>
                        <td className="whitespace-nowrap text-right tabular-nums">{fmtFCFA(p.planned_budget)}</td>
                        <td className="whitespace-nowrap text-right tabular-nums">{fmtFCFA(p.funding_obtained)}</td>
                        <td className={`whitespace-nowrap ${p.is_delayed ? "text-alerte" : ""}`}>{fmtDate(p.deadline)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {/* Cartes (téléphone) */}
              <ul className="space-y-2 md:hidden">
                {liste.data.items.map((p) => (
                  <li key={p.id}>
                    <button className="w-full rounded-lg border border-ligne p-3 text-left" onClick={() => nav(`/projets/${p.id}`)}>
                      <div className="flex items-start justify-between gap-2">
                        <span className="font-medium text-profond">{p.name}</span>
                        <StatusBadge status={p.status} />
                      </div>
                      <p className="mt-1 text-xs text-muted">{p.leader} · {p.cohort} · {p.domain}</p>
                      <div className="mt-2 flex items-center justify-between">
                        <ProgressBar value={p.progress_pct} late={p.is_delayed} />
                        {p.is_delayed && <span className="text-xs font-semibold text-alerte">En retard</span>}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
              <Pagination page={page} pageSize={20} total={liste.data.total} onChange={setPage} />
            </>
          )}
      </Card>

      <ProjectForm open={form} onClose={() => setForm(false)} onSaved={(p) => { setForm(false); nav(`/projets/${p.id}`); }} />
    </div>
  );
}
