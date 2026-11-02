/** Module 3 – Fiche projet : informations, statut, progression, évaluations, jalons, financements, historique. */
import { AlarmClock, ArrowLeft, Check, Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { ProjectDetail } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Card, ConfirmDialog, ErrorBox, Field, Modal, ProgressBar, Spinner, StatusBadge, useToast } from "../components/ui";
import { fmtDate, fmtDateHeure, fmtFCFA, peut, todayISO } from "../lib/format";
import { errMsg, useApi } from "../lib/hooks";
import FundingForm from "./FundingForm";
import ProjectForm from "./ProjectForm";

export default function ProjectDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const nav = useNavigate();
  const toast = useToast();
  const edit = peut(user?.role, "modifier");
  const { data: p, error, reload, setData } = useApi(() => api.get<ProjectDetail>(`/projects/${id}`), [id]);
  const [modal, setModal] = useState<null | "edit" | "status" | "progress" | "eval" | "milestone" | "delete" | "funding">(null);
  const [statut, setStatut] = useState("");
  const [commentaire, setCommentaire] = useState("");
  const [progression, setProgression] = useState(0);
  const [evalF, setEvalF] = useState({ evaluator: "", score: "", recommendation: "Favorable", comment: "", evaluated_at: todayISO() });
  const [jalon, setJalon] = useState({ title: "", due_date: "" });
  const [occupe, setOccupe] = useState(false);

  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!p) return <Spinner />;

  const action = async (fn: () => Promise<ProjectDetail | void>, ok: string) => {
    setOccupe(true);
    try {
      const r = await fn();
      if (r) setData(r);
      toast("succes", ok);
      setModal(null);
      setCommentaire("");
    } catch (e) { toast("erreur", errMsg(e)); } finally { setOccupe(false); }
  };

  const jalonAtteint = (mid: number, title: string, due: string, done: string | null) =>
    action(() => api.put<ProjectDetail>(`/projects/${p.id}/milestones/${mid}`, { title, due_date: due, completed_date: done }),
      done ? "Jalon marqué comme atteint." : "Jalon rouvert.");

  return (
    <div className="space-y-5">
      <Link to="/projets" className="btn-lien inline-flex items-center gap-1"><ArrowLeft className="size-4" /> Retour aux projets</Link>

      <div className="carte flex flex-col gap-4 p-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <StatusBadge status={p.status} />
            {p.is_delayed && <span className="inline-flex items-center gap-1 rounded-full bg-orange-50 px-2 py-0.5 text-xs font-medium text-alerte"><AlarmClock className="size-3" /> En retard</span>}
            {p.is_simulated && <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-900">Donnée simulée</span>}
          </div>
          <h1 className="titre-page">{p.name}</h1>
          <p className="mt-1 text-sm text-muted">N° {p.id} · {p.domain.name} · {p.cohort.name} · mis à jour le {fmtDateHeure(p.updated_at)}</p>
          {p.description && <p className="mt-3 max-w-3xl text-sm">{p.description}</p>}
        </div>
        {edit && (
          <div className="flex flex-wrap gap-2">
            <button className="btn-principal" disabled={!p.allowed_transitions.length}
              onClick={() => { setStatut(p.allowed_transitions[0] ?? ""); setModal("status"); }}>Changer le statut</button>
            <button className="btn-secondaire" onClick={() => { setProgression(p.progress_pct); setModal("progress"); }}>Progression</button>
            <button className="btn-secondaire" onClick={() => setModal("edit")} aria-label="Modifier"><Pencil className="size-4" /></button>
            <button className="btn-secondaire !text-danger" onClick={() => setModal("delete")} aria-label="Supprimer"><Trash2 className="size-4" /></button>
          </div>
        )}
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <Card title="Informations" className="lg:col-span-1">
          <dl className="space-y-3 text-sm">
            {[
              ["Porteur", `${p.leader.first_name} ${p.leader.last_name}`],
              ["Profil", p.leader.profile], ["Genre", p.leader.gender ?? "Non renseigné"],
              ["E-mail", p.leader.email ?? (user?.role === "analyst" ? "Masqué (rôle Analyste)" : "—")],
              ["Téléphone", p.leader.phone ?? (user?.role === "analyst" ? "Masqué (rôle Analyste)" : "—")],
              ["Date de création", fmtDate(p.created_at)], ["Date limite", fmtDate(p.deadline)],
              ["Cohorte", `${p.cohort.name} (${fmtDate(p.cohort.start_date)} → ${fmtDate(p.cohort.end_date)})`],
            ].map(([k, v]) => <div key={k}><dt className="text-xs text-muted">{k}</dt><dd className="font-medium">{v}</dd></div>)}
            <div><dt className="text-xs text-muted">Progression</dt><dd className="mt-1"><ProgressBar value={p.progress_pct} late={p.is_delayed} /></dd></div>
          </dl>
        </Card>

        <Card title="Financement" className="lg:col-span-2"
          actions={edit && !["En attente", "En évaluation", "Non retenu"].includes(p.status)
            ? <button className="btn-secondaire !py-1" onClick={() => setModal("funding")}><Plus className="size-4" /> Ajouter</button> : undefined}>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {[["Budget prévisionnel", p.funding.planned_budget], ["Demandé", p.funding.requested], ["Accordé (financement obtenu)", p.funding.granted],
              ["Reçu", p.funding.received], ["Reste à recevoir", p.funding.remaining_to_receive], ["Besoin non couvert", p.funding.uncovered_need]]
              .map(([k, v]) => <div key={k as string} className="rounded-md bg-gris p-3"><p className="text-xs text-muted">{k}</p><p className="font-semibold tabular-nums">{fmtFCFA(v as number)}</p></div>)}
          </div>
          {p.fundings.length > 0 && (
            <div className="-mx-4 mt-4 overflow-x-auto">
              <table className="tableau min-w-[560px]">
                <thead><tr><th>Source</th><th>Statut</th><th className="text-right">Demandé</th><th className="text-right">Accordé</th><th className="text-right">Reçu</th><th>Demande</th></tr></thead>
                <tbody>{p.fundings.map((x) => (
                  <tr key={x.id}><td>{x.source_type}{x.partner && <span className="block text-xs text-muted">{x.partner}</span>}</td><td>{x.status}</td>
                    <td className="text-right tabular-nums">{fmtFCFA(x.amount_requested)}</td><td className="text-right tabular-nums">{fmtFCFA(x.amount_granted)}</td>
                    <td className="text-right tabular-nums">{fmtFCFA(x.amount_received)}</td><td>{fmtDate(x.request_date)}</td></tr>))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Jalons" subtitle="Un jalon non atteint après sa date prévue met le projet en retard."
          actions={edit ? <button className="btn-secondaire !py-1" onClick={() => setModal("milestone")}><Plus className="size-4" /> Jalon</button> : undefined}>
          {p.milestones.length === 0 ? <p className="text-sm text-muted">Les jalons sont créés automatiquement au passage « En incubation ».</p> : (
            <ol className="space-y-2">
              {p.milestones.map((m) => {
                const late = !m.completed_date && m.due_date < todayISO();
                return (
                  <li key={m.id} className="flex items-center gap-3 rounded-md border border-ligne p-2.5">
                    <span className={`flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${m.completed_date ? "bg-emerald-100 text-emerald-800" : late ? "bg-orange-100 text-alerte" : "bg-gris text-muted"}`}>
                      {m.completed_date ? <Check className="size-4" /> : m.position}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">{m.title}</p>
                      <p className={`text-xs ${late ? "text-alerte" : "text-muted"}`}>Prévu le {fmtDate(m.due_date)}{m.completed_date ? ` · atteint le ${fmtDate(m.completed_date)}` : late ? " · en retard" : ""}</p>
                    </div>
                    {edit && (m.completed_date
                      ? <button className="btn-lien" onClick={() => jalonAtteint(m.id, m.title, m.due_date, null)}>Rouvrir</button>
                      : <button className="btn-secondaire !py-1 text-xs" onClick={() => jalonAtteint(m.id, m.title, m.due_date, todayISO())}>Atteint</button>)}
                  </li>
                );
              })}
            </ol>
          )}
        </Card>

        <Card title="Candidature et évaluations"
          actions={edit && ["En attente", "En évaluation"].includes(p.status) ? <button className="btn-secondaire !py-1" onClick={() => setModal("eval")}><Plus className="size-4" /> Évaluation</button> : undefined}>
          <p className="text-sm">Candidature <b>{p.application.status}</b> · déposée le {fmtDate(p.application.submitted_at)}
            {p.application.decision_date && ` · décision le ${fmtDate(p.application.decision_date)}`}
            {p.application.average_score !== null && ` · note moyenne ${p.application.average_score.toLocaleString("fr-FR")}/20`}</p>
          <ul className="mt-3 space-y-2">
            {p.evaluations.map((e) => (
              <li key={e.id} className="rounded-md bg-gris p-2.5 text-sm">
                <div className="flex justify-between"><b>{e.evaluator}</b><span className="tabular-nums">{Number(e.score).toLocaleString("fr-FR")}/20 · {e.recommendation}</span></div>
                {e.comment && <p className="text-xs text-muted">{e.comment}</p>}
              </li>
            ))}
            {!p.evaluations.length && <li className="text-sm text-muted">Aucune évaluation saisie. Une évaluation est requise avant la décision du comité.</li>}
          </ul>
        </Card>
      </div>

      <Card title="Historique des statuts">
        <ol className="relative space-y-3 border-l border-ligne pl-5">
          {p.history.map((h, i) => (
            <li key={i} className="text-sm">
              <span className="absolute -left-[5px] mt-1.5 size-2.5 rounded-full bg-beige" />
              <p><b>{h.new_status}</b>{h.old_status && <span className="text-muted"> (depuis « {h.old_status} »)</span>}</p>
              <p className="text-xs text-muted">{fmtDateHeure(h.changed_at)}{h.changed_by && ` · ${h.changed_by}`}{h.comment && ` · ${h.comment}`}</p>
            </li>
          ))}
        </ol>
      </Card>

      {/* ---- Modales ---- */}
      <ProjectForm open={modal === "edit"} project={p} onClose={() => setModal(null)} onSaved={(r) => { setData(r); setModal(null); }} />
      <FundingForm open={modal === "funding"} project={{ id: p.id, name: p.name }} onClose={() => setModal(null)} onSaved={() => { setModal(null); reload(); }} />

      <Modal open={modal === "status"} title="Changer le statut" onClose={() => setModal(null)}
        footer={<><button className="btn-secondaire" onClick={() => setModal(null)}>Annuler</button>
          <button className="btn-principal" disabled={occupe || !statut} onClick={() => action(() => api.post<ProjectDetail>(`/projects/${p.id}/status`, { status: statut, comment: commentaire || null }), `Statut : « ${statut} ».`)}>Valider</button></>}>
        <div className="space-y-3">
          <p className="text-sm">Statut actuel : <StatusBadge status={p.status} /></p>
          <Field label="Nouveau statut (transitions autorisées)" htmlFor="st-new">
            <select id="st-new" className="champ" value={statut} onChange={(e) => setStatut(e.target.value)}>
              {p.allowed_transitions.map((s) => <option key={s}>{s}</option>)}
            </select>
          </Field>
          {["Sélectionné", "Non retenu"].includes(statut) && !p.evaluations.length && <p className="text-xs text-alerte">Saisissez d'abord au moins une évaluation de la candidature.</p>}
          <Field label="Commentaire" htmlFor="st-com"><textarea id="st-com" className="champ" value={commentaire} onChange={(e) => setCommentaire(e.target.value)} /></Field>
        </div>
      </Modal>

      <Modal open={modal === "progress"} title="Mettre à jour la progression" onClose={() => setModal(null)}
        footer={<><button className="btn-secondaire" onClick={() => setModal(null)}>Annuler</button>
          <button className="btn-principal" disabled={occupe} onClick={() => action(() => api.post<ProjectDetail>(`/projects/${p.id}/progress`, { progress_pct: progression, comment: commentaire || null }), "Progression mise à jour.")}>Enregistrer</button></>}>
        <div className="space-y-3">
          <label className="etiquette" htmlFor="prog">Progression : <b className="text-profond">{progression} %</b></label>
          <input id="prog" type="range" min={0} max={100} step={5} value={progression} onChange={(e) => setProgression(Number(e.target.value))} className="w-full accent-[#4C311F]" />
          {progression < p.progress_pct && <p className="text-xs text-alerte">Une baisse de progression doit être justifiée.</p>}
          <Field label={progression < p.progress_pct ? "Justification *" : "Commentaire"} htmlFor="prog-c">
            <textarea id="prog-c" className="champ" value={commentaire} onChange={(e) => setCommentaire(e.target.value)} /></Field>
        </div>
      </Modal>

      <Modal open={modal === "eval"} title="Ajouter une évaluation" onClose={() => setModal(null)}
        footer={<><button className="btn-secondaire" onClick={() => setModal(null)}>Annuler</button>
          <button className="btn-principal" disabled={occupe || !evalF.evaluator || evalF.score === ""} onClick={() => action(() => api.post<ProjectDetail>(`/projects/${p.id}/evaluations`, { ...evalF, score: Number(evalF.score), comment: evalF.comment || null }), "Évaluation enregistrée.")}>Enregistrer</button></>}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Évaluateur *" htmlFor="ev-n"><input id="ev-n" className="champ" value={evalF.evaluator} onChange={(e) => setEvalF({ ...evalF, evaluator: e.target.value })} /></Field>
          <Field label="Note sur 20 *" htmlFor="ev-s"><input id="ev-s" type="number" min={0} max={20} step={0.5} className="champ" value={evalF.score} onChange={(e) => setEvalF({ ...evalF, score: e.target.value })} /></Field>
          <Field label="Avis" htmlFor="ev-r"><select id="ev-r" className="champ" value={evalF.recommendation} onChange={(e) => setEvalF({ ...evalF, recommendation: e.target.value })}><option>Favorable</option><option>Réservé</option><option>Défavorable</option></select></Field>
          <Field label="Date" htmlFor="ev-d"><input id="ev-d" type="date" className="champ" max={todayISO()} value={evalF.evaluated_at} onChange={(e) => setEvalF({ ...evalF, evaluated_at: e.target.value })} /></Field>
          <div className="sm:col-span-2"><Field label="Commentaire" htmlFor="ev-c"><textarea id="ev-c" className="champ" value={evalF.comment} onChange={(e) => setEvalF({ ...evalF, comment: e.target.value })} /></Field></div>
        </div>
      </Modal>

      <Modal open={modal === "milestone"} title="Ajouter un jalon" onClose={() => setModal(null)}
        footer={<><button className="btn-secondaire" onClick={() => setModal(null)}>Annuler</button>
          <button className="btn-principal" disabled={occupe || !jalon.title || !jalon.due_date} onClick={() => action(() => api.post<ProjectDetail>(`/projects/${p.id}/milestones`, jalon), "Jalon ajouté.")}>Ajouter</button></>}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Intitulé *" htmlFor="j-t"><input id="j-t" className="champ" value={jalon.title} onChange={(e) => setJalon({ ...jalon, title: e.target.value })} /></Field>
          <Field label="Date prévue *" htmlFor="j-d"><input id="j-d" type="date" className="champ" value={jalon.due_date} onChange={(e) => setJalon({ ...jalon, due_date: e.target.value })} /></Field>
        </div>
      </Modal>

      <ConfirmDialog open={modal === "delete"} title="Supprimer le projet" danger confirmLabel="Supprimer" busy={occupe}
        message={<>Le projet <b>{p.name}</b> sera archivé : il disparaîtra des listes et des indicateurs. Seul un administrateur pourra le restaurer.</>}
        onCancel={() => setModal(null)}
        onConfirm={() => action(async () => { await api.del(`/projects/${p.id}`); nav("/projets"); }, "Projet supprimé (archivé).")} />
    </div>
  );
}
