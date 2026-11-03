/** Page de connexion. */
import { Eye, EyeOff, Lock, LogIn } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { errMsg } from "../lib/hooks";

export default function LoginPage() {
  const { user, login, sessionMessage } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [voir, setVoir] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) { setErreur("Saisissez votre identifiant et votre mot de passe."); return; }
    setEnvoi(true);
    setErreur(null);
    try { await login(username.trim(), password); } catch (err) { setErreur(errMsg(err)); } finally { setEnvoi(false); }
  };

  return (
    <div className="grid min-h-full lg:grid-cols-2">
      <div className="relative hidden flex-col justify-between overflow-hidden bg-brun p-10 text-white lg:flex">
        <span className="flex w-fit items-center rounded-lg bg-white px-3 py-2"><img src="/logo/logo-horizontal.png" alt="CIAT VISION" className="h-14 w-auto object-contain" /></span>
        <div className="max-w-md">
          <h1 className="text-3xl font-semibold leading-tight">Le pilotage intelligent de l'innovation par la donnée.</h1>
          <p className="mt-4 text-white/80">Suivez les candidatures, les projets incubés, les cohortes et les financements du
            Centre d'Innovation, d'Application et de Transfert, et interrogez vos données avec l'assistant CIAT AI Analyst.</p>
        </div>
        <p className="text-sm text-white/60">ISEP Amadou Trawaré de Diamniadio</p>
        <svg className="pointer-events-none absolute -right-20 -bottom-24 size-[420px] opacity-[0.07]" viewBox="0 0 100 100" aria-hidden>
          <rect x="10" y="55" width="16" height="35" fill="#CA9871" /><rect x="38" y="35" width="16" height="55" fill="#CA9871" /><rect x="66" y="12" width="16" height="78" fill="#CA9871" />
        </svg>
      </div>

      <div className="flex items-center justify-center bg-white p-6">
        <div className="w-full max-w-sm">
          <img src="/logo/logo-complet.png" alt="CIAT VISION – ISEP Amadou Trawaré" className="mx-auto mb-2 w-80 max-w-full object-contain" />
          <p className="mb-8 text-center text-sm text-muted">Le pilotage intelligent de l'innovation par la donnée</p>
          <h2 className="text-xl font-semibold text-profond">Connexion</h2>
          <p className="mb-6 text-sm text-muted">Accès réservé aux responsables du CIAT.</p>
          {sessionMessage && <p className="mb-4 rounded-md bg-gris px-3 py-2 text-sm text-texte">{sessionMessage}</p>}
          <form onSubmit={submit} className="space-y-4" noValidate>
            <div>
              <label className="etiquette" htmlFor="username">Identifiant</label>
              <input id="username" className="champ" autoComplete="username" maxLength={30} value={username}
                onChange={(e) => setUsername(e.target.value)} autoFocus />
            </div>
            <div>
              <label className="etiquette" htmlFor="password">Mot de passe</label>
              <div className="relative">
                <input id="password" type={voir ? "text" : "password"} className="champ pr-10" autoComplete="current-password"
                  maxLength={72} value={password} onChange={(e) => setPassword(e.target.value)} />
                <button type="button" className="absolute inset-y-0 right-0 px-3 text-muted" onClick={() => setVoir(!voir)}
                  aria-label={voir ? "Masquer le mot de passe" : "Afficher le mot de passe"}>
                  {voir ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
            </div>
            {erreur && <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-900">{erreur}</p>}
            <button type="submit" className="btn-principal w-full !py-2.5" disabled={envoi}>
              <LogIn className="size-4" /> {envoi ? "Connexion…" : "Se connecter"}
            </button>
          </form>
          <details className="mt-6 rounded-md border border-ligne p-3 text-xs text-muted">
            <summary className="cursor-pointer font-medium text-texte"><Lock className="mr-1 inline size-3" /> Comptes de démonstration</summary>
            <table className="mt-2 w-full">
              <tbody>
                <tr><td>admin</td><td>Admin@2026</td><td>Administrateur</td></tr>
                <tr><td>coordo</td><td>Coordo@2026</td><td>Coordonnateur</td></tr>
                <tr><td>analyste</td><td>Analyste@2026</td><td>Analyste</td></tr>
              </tbody>
            </table>
            <p className="mt-2">À désactiver avant toute utilisation avec des données réelles.</p>
          </details>
        </div>
      </div>
    </div>
  );
}
