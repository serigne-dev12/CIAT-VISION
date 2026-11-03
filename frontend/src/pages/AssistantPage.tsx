/** Module 7 – CIAT AI Analyst : questions en langage naturel, réponses fondées sur les fonctions d'analyse. */
import { Bot, ChevronDown, Database, Send, Sparkles, User as UserIcon } from "lucide-react";
import { Fragment, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { api } from "../api/client";
import type { AskResult } from "../api/types";
import { useData } from "../components/DataContext";
import { Card, Spinner } from "../components/ui";
import { errMsg, useApi } from "../lib/hooks";

interface Statut { ai_available: boolean; daily_limit: number; used_today: number; examples: string[]; functions: { name: string; description: string }[] }
interface Message { role: "user" | "assistant"; text: string; result?: AskResult; error?: boolean }

/** Rendu minimal et sûr (aucun HTML injecté) : **gras**, listes à puces et numérotées. */
function Texte({ text }: { text: string }) {
  const inline = (s: string): ReactNode[] => s.split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
    p.startsWith("**") && p.endsWith("**") ? <strong key={i}>{p.slice(2, -2)}</strong> : <Fragment key={i}>{p}</Fragment>);
  const blocs: ReactNode[] = [];
  let liste: { ordered: boolean; items: string[] } | null = null;
  const flush = () => {
    if (!liste) return;
    const L = liste.ordered ? "ol" : "ul";
    blocs.push(<L key={blocs.length} className={`my-1 space-y-0.5 pl-5 ${liste.ordered ? "list-decimal" : "list-disc"}`}>{liste.items.map((x, i) => <li key={i}>{inline(x)}</li>)}</L>);
    liste = null;
  };
  for (const ligne of text.split("\n")) {
    const puce = /^\s*[-•]\s+(.*)$/.exec(ligne);
    const num = /^\s*\d+[.)]\s+(.*)$/.exec(ligne);
    if (puce || num) {
      const ordered = !!num;
      if (!liste || liste.ordered !== ordered) { flush(); liste = { ordered, items: [] }; }
      liste.items.push((puce ?? num)![1]);
    } else {
      flush();
      if (ligne.trim()) blocs.push(<p key={blocs.length} className="my-1">{inline(ligne)}</p>);
    }
  }
  flush();
  return <div className="text-sm leading-relaxed">{blocs}</div>;
}

function Outils({ result }: { result: AskResult }) {
  const [ouvert, setOuvert] = useState(false);
  if (!result.tools.length) return null;
  return (
    <div className="mt-2 rounded-md border border-ligne bg-gris/60 text-xs">
      <button className="flex w-full items-center justify-between px-3 py-2 font-medium text-profond" onClick={() => setOuvert(!ouvert)} aria-expanded={ouvert}>
        <span className="flex items-center gap-1.5"><Database className="size-3.5" /> Données utilisées : {result.tools.map((t) => t.name).join(", ")}</span>
        <ChevronDown className={`size-4 transition-transform ${ouvert ? "rotate-180" : ""}`} />
      </button>
      {ouvert && result.tools.map((t, i) => (
        <div key={i} className="border-t border-ligne px-3 py-2">
          <p className="font-mono text-[11px] text-muted">{t.name}({JSON.stringify(t.arguments)})</p>
          {t.error ? <p className="text-danger">{t.error}</p> :
            <pre className="mt-1 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded bg-white p-2 font-mono text-[11px]">{JSON.stringify(t.result, null, 2)}</pre>}
        </div>
      ))}
    </div>
  );
}

export default function AssistantPage() {
  const statut = useApi(() => api.get<Statut>("/assistant/status"), []);
  const { body, chips } = useData();
  const [avecFiltres, setAvecFiltres] = useState(true);
  const [messages, setMessages] = useState<Message[]>([]);
  const [q, setQ] = useState("");
  const [envoi, setEnvoi] = useState(false);
  const fin = useRef<HTMLDivElement>(null);
  // Accolades obligatoires : scrollIntoView peut renvoyer une promesse, qui ne doit pas être prise pour un nettoyage
  useEffect(() => { fin.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages, envoi]);

  const poser = async (question: string) => {
    const texte = question.trim();
    if (!texte || envoi) return;
    setMessages((m) => [...m, { role: "user", text: texte }]);
    setQ("");
    setEnvoi(true);
    try {
      const r = await api.post<AskResult>("/assistant/ask", { question: texte, filters: avecFiltres && chips.length ? body : null });
      setMessages((m) => [...m, { role: "assistant", text: r.answer, result: r }]);
      statut.reload();
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: errMsg(e), error: true }]);
    } finally { setEnvoi(false); }
  };
  const submit = (e: FormEvent) => { e.preventDefault(); poser(q); };
  const s = statut.data;

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="flex min-h-[70vh] flex-col">
        <div className="mb-3">
          <h1 className="titre-page flex items-center gap-2"><Sparkles className="size-6 text-beige-fonce" /> CIAT AI Analyst</h1>
          <p className="text-sm text-muted">Posez vos questions sur les données du CIAT. Chaque chiffre provient d'une fonction d'analyse exécutée sur la base.</p>
        </div>
        <div className="carte flex flex-1 flex-col">
          <div className="flex-1 space-y-4 overflow-y-auto p-4" aria-live="polite">
            {messages.length === 0 && (
              <div className="py-6 text-center">
                <Bot className="mx-auto size-10 text-beige" />
                <p className="mt-2 font-medium text-profond">Que souhaitez-vous savoir ?</p>
                <div className="mx-auto mt-4 flex max-w-2xl flex-wrap justify-center gap-2">
                  {(s?.examples ?? []).map((ex) => <button key={ex} className="rounded-full border border-ligne px-3 py-1.5 text-xs hover:border-beige hover:bg-beige-pale" onClick={() => poser(ex)}>{ex}</button>)}
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
                {m.role === "assistant" && <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-brun text-beige"><Bot className="size-4" /></span>}
                <div className={`max-w-[85%] rounded-xl px-4 py-2.5 ${m.role === "user" ? "bg-brun text-white" : m.error ? "bg-red-50 text-red-900" : "bg-gris"}`}>
                  {m.role === "user" ? <p className="text-sm">{m.text}</p> : <Texte text={m.text} />}
                  {m.result && (
                    <>
                      <p className="mt-1 text-[11px] text-muted">Mode : {m.result.mode === "IA" ? "IA générative (Claude)" : m.result.mode}
                        {m.result.filters && <> · Filtres pris en compte : {m.result.filters}</>}</p>
                      <Outils result={m.result} />
                    </>
                  )}
                </div>
                {m.role === "user" && <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-beige text-profond"><UserIcon className="size-4" /></span>}
              </div>
            ))}
            {envoi && <Spinner label="Analyse des données en cours…" />}
            <div ref={fin} />
          </div>
          {chips.length > 0 && (
            <label className="flex flex-wrap items-center gap-2 border-t border-ligne px-3 pt-2 text-xs text-muted">
              <input type="checkbox" checked={avecFiltres} onChange={(e) => setAvecFiltres(e.target.checked)} />
              Tenir compte des filtres actifs du tableau de bord :
              {chips.map((c) => <span key={c.key} className="rounded-full bg-beige-pale px-2 py-0.5 text-profond">{c.label}</span>)}
            </label>
          )}
          <form onSubmit={submit} className="flex gap-2 border-t border-ligne p-3">
            <input className="champ" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ex. : Quels projets nécessitent une attention particulière ?"
              maxLength={1000} aria-label="Votre question" disabled={envoi} />
            <button className="btn-principal" type="submit" disabled={envoi || q.trim().length < 2} aria-label="Envoyer"><Send className="size-4" /></button>
          </form>
        </div>
      </div>

      <aside className="space-y-4">
        <Card title="Fonctionnement">
          {s ? (
            <div className="space-y-2 text-sm">
              <p>Mode : <b>{s.ai_available ? "IA générative (Claude)" : "dégradé (sans IA générative)"}</b></p>
              <p className="text-muted">Questions aujourd'hui : {s.used_today} / {s.daily_limit}</p>
              <ul className="list-disc space-y-1 pl-4 text-xs text-muted">
                <li>L'assistant n'exécute aucune requête SQL : il choisit parmi {s.functions.length} fonctions d'analyse autorisées.</li>
                <li>Les noms et coordonnées des porteurs ne sont jamais transmis au service d'IA.</li>
                <li>Les recommandations sont des propositions à examiner, pas des décisions.</li>
              </ul>
            </div>
          ) : <Spinner />}
        </Card>
        {s && <Card title="Fonctions d'analyse autorisées">
          <ul className="space-y-2 text-xs">{s.functions.map((f) => <li key={f.name}><code className="font-semibold text-profond">{f.name}</code><p className="text-muted">{f.description}</p></li>)}</ul>
        </Card>}
      </aside>
    </div>
  );
}
