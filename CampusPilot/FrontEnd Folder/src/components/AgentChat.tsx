import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import { fetchAgentChatMessages, resetAgentChat, sendAgentMessage } from "../agentApi";
import { BRAND } from "../branding";
import { MessageBody } from "./MessageBody";
import "./AgentChat.css";

export type AgentChatHandle = {
  /** Leert Server-Chat + Pending-Zustände und setzt die Begrüßung im UI. */
  resetChat: () => Promise<void>;
};

type AgentChatProps = {
  /** Eingebettet ins Dashboard: kein großer Titel, heller Karten-Stil */
  embedded?: boolean;
};

type Role = "user" | "assistant";

type ChatMessage = {
  id: string;
  role: Role;
  content: string;
};

function createId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function introBubble(): ChatMessage {
  return {
    id: createId(),
    role: "assistant",
    content:
      `Hallo — ich bin der Assistent von **${BRAND.name}**. Stell eine Frage zu Semesterdaten, z. B. **Welche Feiertage gibt es im Semester 2026s?** ` +
      "Antworten kommen vom **QandA-Agent** (nach Login mit deiner TUM-/LRZ-Kennung). Ohne API-Key läuft ein **Demo-Modus** mit echten JSON-Daten; mit Ollama oder OpenAI siehe ENV.example dort. " +
      "Dein Chat wird **in der Login-Session** auf dem Server gespeichert — mit **Neuer Chat** setzt du ihn zurück.",
  };
}

export const AgentChat = forwardRef<AgentChatHandle, AgentChatProps>(function AgentChat(
  { embedded = false },
  ref,
) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionReady, setSessionReady] = useState(false);
  const [draft, setDraft] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const rows = await fetchAgentChatMessages();
        if (cancelled) return;
        if (rows.length === 0) {
          setMessages([introBubble()]);
        } else {
          setMessages(
            rows.map((r, i) => ({
              id: `loaded-${i}-${r.role}`,
              role: r.role as Role,
              content: r.content,
            })),
          );
        }
      } catch {
        if (!cancelled) setMessages([introBubble()]);
      } finally {
        if (!cancelled) setSessionReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, isThinking]);

  const resetChat = useCallback(async () => {
    if (isThinking || !sessionReady) return;
    try {
      await resetAgentChat();
      setMessages([introBubble()]);
      setDraft("");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setMessages((prev) => [
        ...prev,
        {
          id: createId(),
          role: "assistant",
          content: `**Neuer Chat:** Zurücksetzen ist fehlgeschlagen (${msg}).`,
        },
      ]);
    }
  }, [isThinking, sessionReady]);

  useImperativeHandle(ref, () => ({ resetChat }), [resetChat]);

  async function send() {
    const text = draft.trim();
    if (!text || isThinking || !sessionReady) return;

    const userMessage: ChatMessage = { id: createId(), role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setDraft("");
    setIsThinking(true);

    try {
      const data = await sendAgentMessage(text);
      const body = data.reply.trim() || "(Leere Antwort vom Server.)";
      const reply: ChatMessage = {
        id: createId(),
        role: "assistant",
        content: body,
      };
      setMessages((prev) => [...prev, reply]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setMessages((prev) => [
        ...prev,
        {
          id: createId(),
          role: "assistant",
          content:
            `**Agent nicht erreichbar:** ${msg}\n\n` +
            "Bitte Backend starten: cd CampusPilot/QandA_Agent, venv aktivieren, " +
            "python -m uvicorn main:app --reload --port 8010.\n\n" +
            "Im Dev-Modus nutzt das Frontend den Vite-Proxy /qanda auf Port 8010.",
        },
      ]);
    } finally {
      setIsThinking(false);
    }
  }

  return (
    <section
      className={`agent-chat${embedded ? " agent-chat--embedded" : ""}`}
      aria-label={`Konversation mit ${BRAND.name}`}
    >
      {!embedded ? (
        <div className="agent-chat-inner">
          <div className="agent-chat-head">
            <div>
              <h1 className="agent-chat-title">Frag den CampusPilot</h1>
              <p className="agent-chat-lede">
                {BRAND.name}: organisatorische Infos zur TUM — verbunden mit dem QandA-Agent (FastAPI). Demo ohne
                OpenAI, optional Ollama oder OpenAI-Key.
              </p>
            </div>
          </div>
        </div>
      ) : null}

      <div className={embedded ? "agent-chat-inner agent-chat-inner--tight" : "agent-chat-inner"}>
        <div className="agent-chat-panel">
          {!sessionReady ? (
            <div className="agent-chat-loading" aria-busy="true">
              Konversation wird geladen…
            </div>
          ) : null}
          <div ref={listRef} className="agent-chat-messages" role="log" aria-live="polite">
            {messages.map((m) => (
              <article
                key={m.id}
                className={`agent-bubble agent-bubble--${m.role}`}
                aria-label={m.role === "user" ? "Du" : "Assistent"}
              >
                <div className="agent-bubble-meta">{m.role === "user" ? "Du" : "Agent"}</div>
                <div className="agent-bubble-text">
                  <MessageBody role={m.role} content={m.content} />
                </div>
              </article>
            ))}
            {isThinking ? (
              <div className="agent-thinking" aria-busy="true">
                <span className="agent-thinking-dot" />
                <span className="agent-thinking-dot" />
                <span className="agent-thinking-dot" />
                <span className="agent-thinking-label">Agent antwortet…</span>
              </div>
            ) : null}
          </div>

          <div className="agent-chat-composer">
            <label className="agent-sr-only" htmlFor="agent-input">
              Nachricht
            </label>
            <textarea
              id="agent-input"
              className="agent-input"
              rows={2}
              placeholder="z. B. Welche Feiertage gibt es im Semester 2026s?"
              value={draft}
              disabled={!sessionReady || isThinking}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send();
                }
              }}
            />
            <div className="agent-composer-row">
              <p className="agent-hint">Enter senden · Shift+Enter Zeilenumbruch</p>
              <button
                type="button"
                className="agent-send"
                onClick={() => void send()}
                disabled={!sessionReady || isThinking}
              >
                Senden
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
});

AgentChat.displayName = "AgentChat";
