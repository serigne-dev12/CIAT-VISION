/** Hooks utilitaires : chargement de données depuis l'API avec gestion du chargement et des erreurs. */
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";

export function useApi<T>(loader: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const seq = useRef(0);

  const reload = useCallback(() => {
    const n = ++seq.current;
    setLoading(true);
    setError(null);
    loader()
      .then((d) => { if (n === seq.current) setData(d); })
      .catch((e: unknown) => { if (n === seq.current) setError(e instanceof ApiError ? e.message : "Erreur inattendue."); })
      .finally(() => { if (n === seq.current) setLoading(false); });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => { reload(); }, [reload]);
  return { data, error, loading, reload, setData };
}

export function useDebounced<T>(value: T, ms = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export const errMsg = (e: unknown) => (e instanceof ApiError ? e.message : "Erreur inattendue.");
