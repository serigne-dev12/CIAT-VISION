/** Module 9 – Administration : utilisateurs, paramètres, journal d'audit, données. */
import { Database, KeyRound, Pencil, Plus, ScrollText, Settings, Users } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { Role, User } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useData } from "../components/DataContext";
import { Card, ErrorBox, Field, Modal, Pagination, Spinner, useToast } from "../components/ui";
import { fmtDateHeure, ROLE_LABELS } from "../lib/format";
import { errMsg, useApi } from "../lib/hooks";

const ONGLETS = [
  { k: "users", l: "Utilisateurs", i: Users }, { k: "settings", l: "Paramètres", i: Settings },
  { k: "audit", l: "Journal d'activité", i: ScrollText }, { k: "data", l: "Données", i: Database },
] as const;

function Utilisateurs() {
  const toast = useToast();
  const { user: moi } = useAuth();
  const users = useApi(() => api.get<User[]>("/admin/users"), []);
  const [form, setForm] = useState<User | "new" | null>(null);
  const [f, setF] = useState({ username: "", full_name: "", email: "", role: "analyst" as Role, password: "", is_active: true });
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    setErr(null);
    if (form === "new") setF({ username: "", full_name: "", email: "", role: "analyst", password: "", is_active: true });
    else if (form) setF({ username: form.username, full_name: form.full_name, email: form.email ?? "", role: form.role, password: "", is_active: form.is_active });
  }, [form]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (f.password && (f.password.length < 8 || !/[A-Z]/.test(f.password) || !/[a-z]/.test(f.password) || !/\d/.test(f.password)))
      return setErr("Mot de passe : 8 caractères minimum, majuscules, minuscules et chiffres.");
    try {
      if (form === "new") await api.post("/admin/users", { username: f.username, full_name: f.full_name, email: f.email || null, role: f.role, password: f.password });
      else if (form) await api.put(`/admin/users/${form.id}`, { full_name: f.full_name, email: f.email || null, role: f.role, is_active: f.is_active, ...(f.password ? { new_password: f.password } : {}) });
      toast("succes", "Compte enregistré.");
      setForm(null);
      users.reload();
    } catch (x) { setErr(errMsg(x)); }
  };

  return (
    <Card title="Comptes utilisateurs" actions={<button className="btn-principal !py-1" onClick={() => setForm("new")}><Plus className="size-4" /> Ajouter</button>}>
      {users.error ? <ErrorBox message={users.error} /> : !users.data ? <Spinner /> : (
        <div className="-mx-4 overflow-x-auto">
          <table className="tableau min-w-[720px]">
            <thead><tr><th>Identifiant</th><th>Nom</th><th>Rôle</th><th>État</th><th>Dernière connexion</th><th /></tr></thead>
            <tbody>{users.data.map((u) => (
              <tr key={u.id}><td className="font-mono text-xs">{u.username}</td><td>{u.full_name}<span className="block text-xs text-muted">{u.email}</span></td>
                <td>{ROLE_LABELS[u.role]}</td>
                <td>{u.is_active ? <span className="text-emerald-800">Actif</span> : <span className="text-danger">Désactivé</span>}</td>
                <td className="text-xs">{fmtDateHeure(u.last_login_at)}</td>
                <td className="text-right"><button className="rounded p-1 hover:bg-gris" onClick={() => setForm(u)} aria-label={`Modifier ${u.username}`}><Pencil className="size-4" /></button></td></tr>))}
            </tbody>
          </table>
        </div>
      )}
      <Modal open={form !== null} title={form === "new" ? "Nouveau compte" : `Modifier ${form?.username ?? ""}`} onClose={() => setForm(null)}
        footer={<><button className="btn-secondaire" onClick={() => setForm(null)}>Annuler</button><button className="btn-principal" type="submit" form="form-user">Enregistrer</button></>}>
        <form id="form-user" onSubmit={save} noValidate className="grid gap-3 sm:grid-cols-2">
          <Field label="Identifiant *" htmlFor="u-id" hint="3 à 30 caractères : lettres, chiffres, . _ -">
            <input id="u-id" className="champ" disabled={form !== "new"} value={f.username} onChange={(e) => setF({ ...f, username: e.target.value })} /></Field>
          <Field label="Nom complet *" htmlFor="u-n"><input id="u-n" className="champ" value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></Field>
          <Field label="E-mail" htmlFor="u-e"><input id="u-e" type="email" className="champ" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
          <Field label="Rôle *" htmlFor="u-r"><select id="u-r" className="champ" value={f.role} disabled={form !== "new" && form?.id === moi?.id}
            onChange={(e) => setF({ ...f, role: e.target.value as Role })}>{(Object.keys(ROLE_LABELS) as Role[]).map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}</select></Field>
          <Field label={form === "new" ? "Mot de passe *" : "Nouveau mot de passe (facultatif)"} htmlFor="u-p">
            <input id="u-p" type="password" autoComplete="new-password" className="champ" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
          {form !== "new" && form?.id !== moi?.id && <label className="mt-6 flex items-center gap-2 text-sm"><input type="checkbox" checked={f.is_active} onChange={(e) => setF({ ...f, is_active: e.target.checked })} /> Compte actif</label>}
          {err && <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-900 sm:col-span-2">{err}</p>}
        </form>
      </Modal>
    </Card>
  );
}

function Parametres() {
  const toast = useToast();
  const { reloadRefs } = useData();
  const s = useApi(() => api.get<Record<string, string>>("/admin/settings"), []);
  const [f, setF] = useState<Record<string, string>>({});
  useEffect(() => { if (s.data) setF(s.data); }, [s.data]);
  const save = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.put("/admin/settings", { institution_name: f.institution_name, delay_tolerance_days: Number(f.delay_tolerance_days),
        session_minutes: Number(f.session_minutes), ai_enabled: f.ai_enabled === "true", ai_daily_limit: Number(f.ai_daily_limit) });
      toast("succes", "Paramètres enregistrés.");
      reloadRefs();
    } catch (x) { toast("erreur", errMsg(x)); }
  };
  if (!s.data) return <Spinner />;
  return (
    <Card title="Paramètres de l'application">
      <form onSubmit={save} className="grid max-w-3xl gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2"><Field label="Nom de l'institution" htmlFor="s-i"><input id="s-i" className="champ" value={f.institution_name ?? ""} onChange={(e) => setF({ ...f, institution_name: e.target.value })} /></Field></div>
        <Field label="Seuil de tolérance des retards (jours)" htmlFor="s-t" hint="Un jalon est en retard au-delà de ce délai après sa date prévue (0 à 180).">
          <input id="s-t" type="number" min={0} max={180} className="champ" value={f.delay_tolerance_days ?? ""} onChange={(e) => setF({ ...f, delay_tolerance_days: e.target.value })} /></Field>
        <Field label="Durée de session (minutes)" htmlFor="s-s" hint="Entre 15 et 480 minutes."><input id="s-s" type="number" min={15} max={480} className="champ" value={f.session_minutes ?? ""} onChange={(e) => setF({ ...f, session_minutes: e.target.value })} /></Field>
        <Field label="Assistant IA générative" htmlFor="s-a"><select id="s-a" className="champ" value={f.ai_enabled} onChange={(e) => setF({ ...f, ai_enabled: e.target.value })}><option value="true">Activé (si une clé d'API est configurée)</option><option value="false">Désactivé (mode dégradé)</option></select></Field>
        <Field label="Questions IA par utilisateur et par jour" htmlFor="s-l"><input id="s-l" type="number" min={0} max={1000} className="champ" value={f.ai_daily_limit ?? ""} onChange={(e) => setF({ ...f, ai_daily_limit: e.target.value })} /></Field>
        <p className="text-xs text-muted sm:col-span-2"><KeyRound className="mr-1 inline size-3" /> La clé d'API de l'IA n'est jamais saisie ici : elle est définie dans la configuration du serveur (variable ANTHROPIC_API_KEY).</p>
        <div><button className="btn-principal" type="submit">Enregistrer</button></div>
      </form>
    </Card>
  );
}

function Journal() {
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);
  const j = useApi(() => api.get<{ total: number; actions: string[]; items: { id: number; created_at: string; username: string | null; action: string; entity: string | null; details: string | null; ip_address: string | null }[] }>(
    "/admin/audit-logs", { action, page, page_size: 25 }), [action, page]);
  return (
    <Card title="Journal d'activité" actions={
      <select className="champ !w-auto !py-1" value={action} onChange={(e) => { setAction(e.target.value); setPage(1); }} aria-label="Filtrer par action">
        <option value="">Toutes les actions</option>{(j.data?.actions ?? []).map((a) => <option key={a}>{a}</option>)}
      </select>}>
      {!j.data ? <Spinner /> : (
        <>
          <div className="-mx-4 overflow-x-auto">
            <table className="tableau min-w-[760px]">
              <thead><tr><th>Date</th><th>Utilisateur</th><th>Action</th><th>Détails</th><th>Adresse IP</th></tr></thead>
              <tbody>{j.data.items.map((a) => (
                <tr key={a.id}><td className="whitespace-nowrap text-xs">{fmtDateHeure(a.created_at)}</td><td>{a.username ?? "—"}</td>
                  <td><code className="text-xs">{a.action}</code></td><td className="max-w-md text-xs">{a.details ?? ""}</td><td className="text-xs text-muted">{a.ip_address ?? ""}</td></tr>))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pageSize={25} total={j.data.total} onChange={setPage} />
        </>
      )}
    </Card>
  );
}

function Donnees() {
  const toast = useToast();
  const { reloadRefs } = useData();
  const d = useApi(() => api.get<{ simulated_projects: number; real_projects: number; archived: { id: number; name: string; cohort: string; archived_at: string }[] }>("/admin/data-status"), []);
  const [mot, setMot] = useState("");
  const purger = async () => {
    try {
      const r = await api.post<{ projets: number }>("/admin/purge-simulated", {}, { confirmation: mot });
      toast("succes", `${r.projets} projets simulés supprimés. Vous pouvez importer les données réelles.`);
      setMot(""); d.reload(); reloadRefs();
    } catch (e) { toast("erreur", errMsg(e)); }
  };
  const restaurer = async (id: number) => {
    try { await api.post(`/admin/projects/${id}/restore`); toast("succes", "Projet restauré."); d.reload(); } catch (e) { toast("erreur", errMsg(e)); }
  };
  if (!d.data) return <Spinner />;
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Card title="Passage aux données réelles">
        <p className="text-sm">Projets simulés : <b>{d.data.simulated_projects}</b> · projets réels : <b>{d.data.real_projects}</b></p>
        <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-muted">
          <li>Purgez les données simulées (les comptes, domaines et paramètres sont conservés).</li>
          <li>Importez les cohortes, puis les projets, puis les financements réels (page Importation).</li>
          <li>Le bandeau « Données simulées » disparaît automatiquement.</li>
        </ol>
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3">
          <label className="etiquette !text-red-900" htmlFor="purge">Saisissez PURGER pour confirmer (action irréversible)</label>
          <div className="flex gap-2">
            <input id="purge" className="champ" value={mot} onChange={(e) => setMot(e.target.value)} placeholder="PURGER" />
            <button className="btn-danger" disabled={mot !== "PURGER" || !d.data.simulated_projects} onClick={purger}>Purger</button>
          </div>
        </div>
      </Card>
      <Card title={`Projets supprimés (archivés) – ${d.data.archived.length}`}>
        {d.data.archived.length === 0 ? <p className="text-sm text-muted">Aucun projet archivé.</p> : (
          <ul className="divide-y divide-ligne">{d.data.archived.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-2 py-2 text-sm">
              <span><b>{p.name}</b><span className="block text-xs text-muted">{p.cohort} · supprimé le {fmtDateHeure(p.archived_at)}</span></span>
              <button className="btn-secondaire !py-1" onClick={() => restaurer(p.id)}>Restaurer</button>
            </li>))}
          </ul>
        )}
      </Card>
    </div>
  );
}

export default function AdminPage() {
  const [onglet, setOnglet] = useState<(typeof ONGLETS)[number]["k"]>("users");
  return (
    <div className="space-y-5">
      <h1 className="titre-page">Administration</h1>
      <div className="flex gap-1 overflow-x-auto border-b border-ligne" role="tablist">
        {ONGLETS.map(({ k, l, i: Icon }) => (
          <button key={k} role="tab" aria-selected={onglet === k} onClick={() => setOnglet(k)}
            className={`flex items-center gap-2 whitespace-nowrap border-b-2 px-4 py-2 text-sm ${onglet === k ? "border-brun font-semibold text-profond" : "border-transparent text-muted hover:text-texte"}`}>
            <Icon className="size-4" /> {l}
          </button>
        ))}
      </div>
      {onglet === "users" && <Utilisateurs />}
      {onglet === "settings" && <Parametres />}
      {onglet === "audit" && <Journal />}
      {onglet === "data" && <Donnees />}
    </div>
  );
}
