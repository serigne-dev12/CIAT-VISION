/** Profil de l'utilisateur connecté : informations et changement de mot de passe. */
import { useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { User } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Card, Field, useToast } from "../components/ui";
import { ROLE_LABELS } from "../lib/format";
import { errMsg } from "../lib/hooks";

export default function ProfilePage() {
  const { user, setUser } = useAuth();
  const toast = useToast();
  const [p, setP] = useState({ full_name: user?.full_name ?? "", email: user?.email ?? "" });
  const [m, setM] = useState({ current_password: "", new_password: "", confirm: "" });
  const [err, setErr] = useState<string | null>(null);

  const saveProfil = async (e: FormEvent) => {
    e.preventDefault();
    try { setUser(await api.put<User>("/auth/me", { full_name: p.full_name, email: p.email || null })); toast("succes", "Profil mis à jour."); }
    catch (x) { toast("erreur", errMsg(x)); }
  };
  const saveMdp = async (e: FormEvent) => {
    e.preventDefault();
    setErr(null);
    if (m.new_password !== m.confirm) return setErr("Les deux nouveaux mots de passe ne correspondent pas.");
    try {
      await api.post("/auth/change-password", { current_password: m.current_password, new_password: m.new_password });
      setM({ current_password: "", new_password: "", confirm: "" });
      toast("succes", "Mot de passe modifié.");
    } catch (x) { setErr(errMsg(x)); }
  };

  return (
    <div className="space-y-5">
      <h1 className="titre-page">Mon profil</h1>
      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Informations">
          <form onSubmit={saveProfil} className="space-y-3">
            <p className="text-sm">Identifiant : <b>{user?.username}</b> · rôle : <b>{user && ROLE_LABELS[user.role]}</b></p>
            <Field label="Nom complet" htmlFor="pf-n"><input id="pf-n" className="champ" value={p.full_name} onChange={(e) => setP({ ...p, full_name: e.target.value })} /></Field>
            <Field label="E-mail" htmlFor="pf-e"><input id="pf-e" type="email" className="champ" value={p.email} onChange={(e) => setP({ ...p, email: e.target.value })} /></Field>
            <button className="btn-principal" type="submit">Enregistrer</button>
          </form>
        </Card>
        <Card title="Changer mon mot de passe">
          <form onSubmit={saveMdp} className="space-y-3">
            <Field label="Mot de passe actuel" htmlFor="pw-a"><input id="pw-a" type="password" autoComplete="current-password" className="champ" value={m.current_password} onChange={(e) => setM({ ...m, current_password: e.target.value })} /></Field>
            <Field label="Nouveau mot de passe" htmlFor="pw-n" hint="8 caractères minimum, majuscules, minuscules et au moins un chiffre."><input id="pw-n" type="password" autoComplete="new-password" className="champ" value={m.new_password} onChange={(e) => setM({ ...m, new_password: e.target.value })} /></Field>
            <Field label="Confirmation" htmlFor="pw-c"><input id="pw-c" type="password" autoComplete="new-password" className="champ" value={m.confirm} onChange={(e) => setM({ ...m, confirm: e.target.value })} /></Field>
            {err && <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-900">{err}</p>}
            <button className="btn-principal" type="submit" disabled={!m.current_password || !m.new_password}>Mettre à jour</button>
          </form>
        </Card>
      </div>
    </div>
  );
}
