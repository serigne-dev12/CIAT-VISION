/** Composants d'interface réutilisables. */
import { AlertTriangle, ChevronLeft, ChevronRight, Info, Loader2, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { STATUT_BADGE } from "../lib/colors";

export function Spinner({ label = "Chargement…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center justify-center gap-2 py-10 text-sm text-muted">
      <Loader2 className="size-5 animate-spin text-beige" aria-hidden /> {label}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
      <AlertTriangle className="mt-0.5 size-5 shrink-0" aria-hidden />
      <div className="flex-1">{message}</div>
      {onRetry && <button className="btn-secondaire !py-1" onClick={onRetry}>Réessayer</button>}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-1 py-10 text-center">
      <Info className="size-6 text-beige" aria-hidden />
      <p className="font-medium text-profond">{title}</p>
      {children && <p className="max-w-md text-sm text-muted">{children}</p>}
    </div>
  );
}

export function Card({ title, actions, children, className = "", subtitle }:
  { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string; subtitle?: ReactNode }) {
  return (
    <section className={`carte animate-apparition ${className}`}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-2 border-b border-ligne/70 px-4 py-3">
          <div>
            {title && <h2 className="text-sm font-semibold text-profond">{title}</h2>}
            {subtitle && <p className="text-xs text-muted">{subtitle}</p>}
          </div>
          {actions}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${STATUT_BADGE[status] ?? "bg-gris text-texte"}`}>
      {status}
    </span>
  );
}

export function ProgressBar({ value, late = false }: { value: number; late?: boolean }) {
  return (
    <div className="flex items-center gap-2" aria-label={`Progression ${value} %`}>
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-ligne">
        <div className={`h-full rounded-full ${late ? "bg-alerte" : "bg-brun"}`} style={{ width: `${value}%` }} />
      </div>
      <span className="w-9 text-xs tabular-nums text-muted">{value} %</span>
    </div>
  );
}

export function Field({ label, children, hint, error, htmlFor }:
  { label: string; children: ReactNode; hint?: string; error?: string; htmlFor?: string }) {
  return (
    <div>
      <label className="etiquette" htmlFor={htmlFor}>{label}</label>
      {children}
      {hint && !error && <p className="mt-1 text-xs text-muted">{hint}</p>}
      {error && <p className="mt-1 text-xs text-danger">{error}</p>}
    </div>
  );
}

export function Modal({ open, title, onClose, children, footer, wide = false }:
  { open: boolean; title: string; onClose: () => void; children: ReactNode; footer?: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", esc);
    ref.current?.querySelector<HTMLElement>("input, select, textarea, button")?.focus();
    return () => document.removeEventListener("keydown", esc);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-profond/40 p-0 sm:items-center sm:p-4"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={ref} role="dialog" aria-modal="true" aria-label={title}
        className={`animate-apparition flex max-h-[92vh] w-full flex-col rounded-t-xl bg-white shadow-xl sm:rounded-xl ${wide ? "sm:max-w-3xl" : "sm:max-w-lg"}`}>
        <div className="flex items-center justify-between border-b border-ligne px-5 py-3">
          <h2 className="font-semibold text-profond">{title}</h2>
          <button className="rounded p-1 text-muted hover:bg-gris" onClick={onClose} aria-label="Fermer"><X className="size-5" /></button>
        </div>
        <div className="overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="flex flex-wrap justify-end gap-2 border-t border-ligne px-5 py-3">{footer}</div>}
      </div>
    </div>
  );
}

export function Pagination({ page, pageSize, total, onChange }:
  { page: number; pageSize: number; total: number; onChange: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="flex items-center justify-between gap-2 pt-3 text-sm text-muted">
      <span>{total} résultat{total > 1 ? "s" : ""}</span>
      <div className="flex items-center gap-1">
        <button className="btn-secondaire !px-2 !py-1" disabled={page <= 1} onClick={() => onChange(page - 1)} aria-label="Page précédente"><ChevronLeft className="size-4" /></button>
        <span className="px-2 tabular-nums">{page} / {pages}</span>
        <button className="btn-secondaire !px-2 !py-1" disabled={page >= pages} onClick={() => onChange(page + 1)} aria-label="Page suivante"><ChevronRight className="size-4" /></button>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ notifications (toasts)
type Toast = { id: number; kind: "succes" | "erreur" | "info"; text: string };
const ToastCtx = createContext<(kind: Toast["kind"], text: string) => void>(() => undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((kind: Toast["kind"], text: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, kind, text }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), kind === "erreur" ? 7000 : 4000);
  }, []);
  const style = { succes: "border-emerald-200 bg-emerald-50 text-emerald-900", erreur: "border-red-200 bg-red-50 text-red-900",
    info: "border-ligne bg-white text-texte" };
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div aria-live="polite" className="fixed bottom-4 right-4 z-[60] flex w-[min(92vw,380px)] flex-col gap-2">
        {toasts.map((t) => (
          <div key={t.id} className={`animate-apparition rounded-lg border px-4 py-3 text-sm shadow-carte ${style[t.kind]}`}>{t.text}</div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
export const useToast = () => useContext(ToastCtx);

// ------------------------------------------------------------------ confirmation
export function ConfirmDialog({ open, title, message, confirmLabel = "Confirmer", danger = false, onConfirm, onCancel, busy }:
  { open: boolean; title: string; message: ReactNode; confirmLabel?: string; danger?: boolean; onConfirm: () => void; onCancel: () => void; busy?: boolean }) {
  return (
    <Modal open={open} title={title} onClose={onCancel}
      footer={<>
        <button className="btn-secondaire" onClick={onCancel}>Annuler</button>
        <button className={danger ? "btn-danger" : "btn-principal"} onClick={onConfirm} disabled={busy}>{confirmLabel}</button>
      </>}>
      <div className="text-sm text-texte">{message}</div>
    </Modal>
  );
}
