import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";

const strings = {
  it: {
    network: "La tua rete",
    invite: "Aggiungi computer",
    join: "Collega questo computer",
    code: "Codice di collegamento",
    send: "Collega",
    waiting: "Connessione in corso…",
    share: "Inserisci questo codice sul secondo computer entro 10 minuti.",
    confirm:
      "Autorizzi questo dispositivo a sincronizzare la cartella Pairthing?",
    allow: "Autorizza",
    cancel: "Annulla",
    folder: "Apri cartella",
    offline: "In attesa del dispositivo",
    active: "Cartella sincronizzata",
    sync: "Sincronizzazione in corso",
    issue: "Problema di sincronizzazione",
    files: "File locali",
    remaining: "Elementi in attesa",
    retry: "Riprova",
    error: "Collegamento interrotto. Verifica la connessione e riprova.",
    runtime:
      "Impossibile avviare il controller locale. Verifica il runtime Pairthing e riapri l’app.",
    incomplete:
      "Configurazione interrotta. La cartella è conservata. Occorre recuperare il profilo prima di riprendere.",
    invalid: "Controlla il codice e riprova.",
    loading: "Avvio del controller…",
    choose:
      "Per collegare due computer, genera il codice su uno e inseriscilo sull’altro.",
  },
  en: {
    network: "Your network",
    invite: "Add a computer",
    join: "Connect this computer",
    code: "Pairing code",
    send: "Connect",
    waiting: "Connecting…",
    share: "Enter this code on the second computer within 10 minutes.",
    confirm: "Allow this device to sync the Pairthing folder?",
    allow: "Allow device",
    cancel: "Cancel",
    folder: "Open folder",
    offline: "Waiting for device",
    active: "Folder up to date",
    sync: "Syncing",
    issue: "Sync issue",
    files: "Local files",
    remaining: "Pending items",
    retry: "Try again",
    error: "Connection interrupted. Check your connection and try again.",
    runtime:
      "Could not start the local controller. Check the Pairthing runtime and reopen the app.",
    incomplete:
      "Setup was interrupted. Your folder is preserved. Recover the profile before resuming.",
    invalid: "Check the pairing code and try again.",
    loading: "Starting controller…",
    choose:
      "To link two computers, generate the code on one and enter it on the other.",
  },
};
type View = {
  stage: string;
  code?: string;
  peer?: string;
  folder?: string;
  online?: boolean;
  transport?: string;
  files?: number;
  remaining?: number;
  scanning?: boolean;
  errors?: number;
};
export function Pairing({ lang }: { lang: "it" | "en" }) {
  const t = strings[lang];
  const [view, setView] = useState<View>({ stage: "loading" }),
    [code, setCode] = useState(""),
    [error, setError] = useState(""),
    [sending, setSending] = useState(false);
  useEffect(() => {
    let alive = true,
      timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const next = await invoke<View>("desktop_state");
        if (alive) setView(next);
      } catch {
        if (alive) setView({ stage: "unavailable" });
      }
      if (alive) timer = setTimeout(poll, 600);
    }
    void poll();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, []);
  async function act(action: string) {
    setError("");
    setSending(true);
    try {
      await invoke("desktop_action", {
        action,
        code: action === "join" ? code.trim() : null,
      });
      if (action === "join") setCode("");
    } catch (e) {
      setError(String(e) === "code" ? t.invalid : t.error);
    } finally {
      setSending(false);
    }
  }
  const stage = view.stage;
  return (
    <section className="pair">
      <h1>{t.network}</h1>
      {stage === "ready" && (
        <>
          <p>{t.choose}</p>
          <button
            className="primary"
            onClick={() => act("invite")}
            disabled={sending}
          >
            {t.invite}
          </button>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void act("join");
            }}
          >
            <h2>{t.join}</h2>
            <label htmlFor="join-code">{t.code}</label>
            <div className="line">
              <input
                id="join-code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                autoComplete="off"
                spellCheck={false}
                maxLength={128}
              />
              <button disabled={!code.trim() || sending}>{t.send}</button>
            </div>
          </form>
        </>
      )}
      <div role="status">
        {stage === "loading" && t.loading}
        {stage === "connecting" && t.waiting}
        {stage === "invite" && (
          <>
            <p>{t.share}</p>
            <output>{view.code}</output>
          </>
        )}
        {stage === "confirm" && (
          <>
            <p>{t.confirm}</p>
            <strong>{view.peer}</strong>
          </>
        )}
        {stage === "error" && t.error}
        {stage === "unavailable" && t.runtime}
        {stage === "incomplete" && t.incomplete}
        {stage === "active" && (
          <>
            <h2>
              {view.errors
                ? t.issue
                : !view.online
                  ? t.offline
                  : view.scanning || view.remaining
                    ? t.sync
                    : t.active}
            </h2>
            <p>
              {view.peer}{" "}
              {view.online && view.transport && (
                <small>({view.transport})</small>
              )}
            </p>
            <p>
              {t.files}: {view.files} · {t.remaining}: {view.remaining}
            </p>
            <p className="path">{view.folder}</p>
          </>
        )}
      </div>
      <div className="line">
        {stage === "confirm" && (
          <button className="primary" onClick={() => act("approve")}>
            {t.allow}
          </button>
        )}
        {["connecting", "invite", "confirm"].includes(stage) && (
          <button onClick={() => act("cancel")}>{t.cancel}</button>
        )}
        {stage === "error" && (
          <button onClick={() => act("retry")}>{t.retry}</button>
        )}
        {stage === "active" && (
          <button onClick={() => act("open")}>{t.folder}</button>
        )}
      </div>
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
