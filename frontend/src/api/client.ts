/**
 * Client HTTP de l'API CIAT VISION.
 * - Ajoute le jeton JWT à chaque requête.
 * - Transforme les erreurs de l'API en messages français affichables.
 * - Le jeton est stocké en sessionStorage (effacé à la fermeture de l'onglet).
 */
const TOKEN_KEY = "ciat_vision_token";
const BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export const tokenStore = {
  get: (): string | null => {
    try { return sessionStorage.getItem(TOKEN_KEY); } catch { return null; }
  },
  set: (t: string) => { try { sessionStorage.setItem(TOKEN_KEY, t); } catch { /* stockage indisponible */ } },
  clear: () => { try { sessionStorage.removeItem(TOKEN_KEY); } catch { /* stockage indisponible */ } },
};

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: () => void) { onUnauthorized = fn; }

type Params = Record<string, string | number | boolean | undefined | null | (string | number)[]>;

export function buildQuery(params?: Params): string {
  if (!params) return "";
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    if (Array.isArray(v)) v.forEach((x) => q.append(k, String(x)));
    else q.append(k, String(v));
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return body.detail.map((d: { msg?: string }) => d.msg).join(" ; ");
  } catch { /* réponse non JSON */ }
  if (res.status === 403) return "Votre rôle ne permet pas cette action.";
  if (res.status === 404) return "Ressource introuvable.";
  if (res.status >= 500) return "Le serveur a rencontré une erreur. Réessayez dans un instant.";
  return `Erreur ${res.status}`;
}

async function request<T>(method: string, path: string, body?: unknown, params?: Params, isForm = false): Promise<T> {
  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined && !isForm) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(`${BASE}/api${path}${buildQuery(params)}`, {
      method, headers, body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Impossible de joindre le serveur. Vérifiez votre connexion.");
  }
  if (res.status === 401 && path !== "/auth/login") {
    tokenStore.clear();
    onUnauthorized?.();
  }
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res));
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string, params?: Params) => request<T>("GET", path, undefined, params),
  post: <T>(path: string, body?: unknown, params?: Params) => request<T>("POST", path, body ?? {}, params),
  put: <T>(path: string, body: unknown) => request<T>("PUT", path, body),
  del: <T = void>(path: string) => request<T>("DELETE", path),
  form: <T>(path: string, form: FormData) => request<T>("POST", path, form, undefined, true),

  /** Télécharge un fichier (rapport, modèle d'import) et déclenche l'enregistrement dans le navigateur. */
  async download(path: string, body?: unknown, fallbackName = "export"): Promise<void> {
    const headers: Record<string, string> = {};
    const token = tokenStore.get();
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const res = await fetch(`${BASE}/api${path}`, {
      method: body === undefined ? "GET" : "POST", headers, body: body === undefined ? undefined : JSON.stringify(body),
    }).catch(() => { throw new ApiError(0, "Impossible de joindre le serveur."); });
    if (!res.ok) throw new ApiError(res.status, await errorMessage(res));
    const dispo = res.headers.get("Content-Disposition") ?? "";
    const nom = /filename\*=UTF-8''([^;]+)/.exec(dispo)?.[1] ?? /filename="([^"]+)"/.exec(dispo)?.[1] ?? fallbackName;
    const url = URL.createObjectURL(await res.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = decodeURIComponent(nom);
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  },
};
