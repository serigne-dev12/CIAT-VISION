/** Mise en page de l'application : barre latérale, barre supérieure, bandeau « données simulées ». */
import {
  BarChart3, Bot, ChevronsLeft, ChevronsRight, FileText, FolderKanban, LayoutDashboard, LogOut, Menu, Shield,
  TriangleAlert, Upload, UserRound, Users, Wallet, X,
} from "lucide-react";
import { Suspense, useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { peut, ROLE_LABELS } from "../lib/format";
import { useData } from "./DataContext";

const NAV = [
  { to: "/", label: "Tableau de bord", icon: LayoutDashboard, end: true },
  { to: "/projets", label: "Projets", icon: FolderKanban },
  { to: "/analyses", label: "Analyses", icon: BarChart3 },
  { to: "/cohortes", label: "Cohortes", icon: Users },
  { to: "/financements", label: "Financements", icon: Wallet },
  { to: "/assistant", label: "CIAT AI Analyst", icon: Bot },
  { to: "/rapports", label: "Rapports", icon: FileText },
  { to: "/importation", label: "Importation", icon: Upload, perm: "importer" as const },
  { to: "/administration", label: "Administration", icon: Shield, perm: "administrer" as const },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const { meta } = useData();
  const [mobile, setMobile] = useState(false);
  const [replie, setReplie] = useState(() => {
    try { return localStorage.getItem("ciat_sidebar") === "1"; } catch { return false; }
  });
  const loc = useLocation();
  useEffect(() => { setMobile(false); }, [loc.pathname]);
  useEffect(() => { try { localStorage.setItem("ciat_sidebar", replie ? "1" : "0"); } catch { /* indisponible */ } }, [replie]);

  const items = NAV.filter((n) => !n.perm || peut(user?.role, n.perm));
  const nav = (compact: boolean) => (
    <nav className="flex flex-1 flex-col gap-1 px-2 py-3" aria-label="Navigation principale">
      {items.map(({ to, label, icon: Icon, end }) => (
        <NavLink key={to} to={to} end={end} title={compact ? label : undefined}
          className={({ isActive }) => `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
            isActive ? "bg-white/10 font-semibold text-beige" : "text-white/85 hover:bg-white/5 hover:text-white"} ${compact ? "justify-center" : ""}`}>
          <Icon className="size-5 shrink-0" aria-hidden />
          {!compact && <span>{label}</span>}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="flex min-h-full">
      {/* Barre latérale (ordinateur) */}
      <aside className={`sticky top-0 hidden h-screen shrink-0 flex-col bg-brun transition-[width] duration-200 lg:flex ${replie ? "w-[72px]" : "w-64"}`}>
        {/* Logo officiel (fond transparent) sur la zone claire qui prolonge la barre supérieure :
            conçu pour un fond clair, il n'est jamais recoloré ni déformé */}
        <Link to="/" className={`flex h-16 items-center justify-center border-b border-r border-ligne bg-white ${replie ? "px-1" : "px-3"}`} aria-label="CIAT VISION – accueil">
          {replie ? <img src="/logo/logo-compact.png" alt="CIAT VISION" className="size-12 object-contain" />
            : <img src="/logo/logo-horizontal.png" alt="CIAT VISION" className="h-12 w-auto object-contain" />}
        </Link>
        {nav(replie)}
        <button onClick={() => setReplie(!replie)} className="m-2 flex items-center justify-center gap-2 rounded-md px-3 py-2 text-xs text-white/70 hover:bg-white/5"
          aria-label={replie ? "Déplier le menu" : "Replier le menu"}>
          {replie ? <ChevronsRight className="size-4" /> : <><ChevronsLeft className="size-4" /> Replier</>}
        </button>
      </aside>

      {/* Menu mobile */}
      {mobile && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-profond/50" onClick={() => setMobile(false)} />
          <aside className="animate-apparition absolute inset-y-0 left-0 flex w-72 flex-col bg-brun">
            <div className="flex h-16 items-center justify-between border-b border-ligne bg-white px-4">
              <img src="/logo/logo-horizontal.png" alt="CIAT VISION" className="h-11 w-auto object-contain" />
              <button onClick={() => setMobile(false)} className="rounded p-1 text-profond hover:bg-gris" aria-label="Fermer le menu"><X className="size-5" /></button>
            </div>
            {nav(false)}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-ligne bg-white/95 px-4 backdrop-blur sm:px-6">
          <button className="rounded p-1.5 text-profond lg:hidden" onClick={() => setMobile(true)} aria-label="Ouvrir le menu"><Menu className="size-6" /></button>
          <img src="/logo/logo-compact.png" alt="" className="size-10 object-contain lg:hidden" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-profond">CIAT VISION</p>
            <p className="hidden truncate text-xs text-muted sm:block">{meta?.institution ?? "ISEP Amadou Trawaré de Diamniadio"} · Centre d'Innovation, d'Application et de Transfert</p>
          </div>
          <Link to="/profil" className="flex items-center gap-2 rounded-md px-2 py-1 hover:bg-gris" title="Mon profil">
            <span className="flex size-8 items-center justify-center rounded-full bg-beige text-sm font-semibold text-profond">
              {user?.full_name.split(" ").map((x) => x[0]).slice(0, 2).join("")}
            </span>
            <span className="hidden text-left md:block">
              <span className="block text-sm font-medium leading-tight">{user?.full_name}</span>
              <span className="block text-xs text-muted">{user && ROLE_LABELS[user.role]}</span>
            </span>
          </Link>
          <button className="btn-secondaire !px-2.5" onClick={() => logout("Vous avez été déconnecté.")} title="Se déconnecter" aria-label="Se déconnecter">
            <LogOut className="size-4" />
          </button>
        </header>

        {meta?.simulated && (
          <div className="flex items-center gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-900 sm:px-6" role="note">
            <TriangleAlert className="size-4 shrink-0" aria-hidden />
            <span><b>Données simulées – non officielles.</b> Les statistiques affichées proviennent du jeu de démonstration.</span>
          </div>
        )}

        <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-5 sm:px-6">
          <Suspense fallback={<div className="py-16" />}><Outlet /></Suspense>
        </main>
        <footer className="px-6 py-4 text-center text-xs text-muted">
          CIAT VISION · Le pilotage intelligent de l'innovation par la donnée · <UserRound className="inline size-3" /> {user?.username}
        </footer>
      </div>
    </div>
  );
}
