/** Mise en forme française des valeurs (identique aux règles du backend). */
import type { KpiUnit, Role } from "../api/types";

const nf = new Intl.NumberFormat("fr-FR");

export const fmtNombre = (v: number | null | undefined) => (v === null || v === undefined ? "—" : nf.format(v));
export const fmtFCFA = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${nf.format(Math.round(v))} FCFA`);
export const fmtMillions = (v: number) => `${(v / 1_000_000).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} M`;
export const fmtTaux = (v: number | null | undefined) =>
  v === null || v === undefined ? "—" : `${(v * 100).toLocaleString("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} %`;
export const fmtPct = (v: number | null | undefined) =>
  v === null || v === undefined ? "—" : `${v.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} %`;

export function fmtKpi(value: number | null, unit: KpiUnit): string {
  if (unit === "rate") return fmtTaux(value);
  if (unit === "percent") return fmtPct(value);
  if (unit === "amount") return fmtFCFA(value);
  return fmtNombre(value);
}

export function fmtDate(v: string | null | undefined): string {
  if (!v) return "—";
  const d = new Date(v.length === 10 ? `${v}T00:00:00` : v);
  return Number.isNaN(d.getTime()) ? v : d.toLocaleDateString("fr-FR");
}

export function fmtDateHeure(v: string | null | undefined): string {
  if (!v) return "—";
  const d = new Date(v);
  return d.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

export function fmtMois(m: string): string {
  const [a, mo] = m.split("-").map(Number);
  return new Date(a, mo - 1, 1).toLocaleDateString("fr-FR", { month: "short", year: "2-digit" });
}

export const ROLE_LABELS: Record<Role, string> = {
  admin: "Administrateur", coordinator: "Coordonnateur du CIAT", analyst: "Analyste",
};

/** Matrice des droits (miroir du backend – la vérification réelle est faite par l'API). */
export const PERMISSIONS = {
  modifier: ["admin", "coordinator"],
  importer: ["admin", "coordinator"],
  administrer: ["admin"],
} as const satisfies Record<string, readonly Role[]>;

export function peut(role: Role | undefined, action: keyof typeof PERMISSIONS): boolean {
  return !!role && (PERMISSIONS[action] as readonly Role[]).includes(role);
}

export function todayISO(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
