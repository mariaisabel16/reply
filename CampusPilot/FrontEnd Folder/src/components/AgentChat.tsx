import { useEffect, useRef, useState } from "react";
import "./AgentChat.css";

type Role = "user" | "assistant";

type ChatMessage = {
  id: string;
  role: Role;
  content: string;
};

function createId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function mockAssistantReply(userText: string) {
  const trimmed = userText.trim();
  if (!trimmed) {
    return "Schreib mir etwas – ich antworte hier (Demo ohne Backend).";
  }
  return `Ich habe gelesen: „${trimmed.slice(0, 280)}${trimmed.length > 280 ? "…" : ""}“. Später kannst du hier deinen echten Agenten anbinden.`;
}

export function AgentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: createId(),
      role: "assistant",
      content:
        "Hallo. Ich bin dein KI-Agent (UI-Demo). Stell eine Frage oder beschreib, was du brauchst.",
    },
  ]);
  const [draft, setDraft] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, isThinking]);

  function send() {
    const text = draft.trim();
    if (!text || isThinking) return;

    const userMessage: ChatMessage = { id: createId(), role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setDraft("");
    setIsThinking(true);

    window.setTimeout(() => {
      const reply: ChatMessage = {
        id: createId(),
        role: "assistant",
        content: mockAssistantReply(text),
      };
      setMessages((prev) => [...prev, reply]);
      setIsThinking(false);
    }, 650);
  }

  return (
    <section className="agent-chat" aria-label="Konversation mit dem KI-Agenten">
      <div className="agent-chat-inner">
        <div className="agent-chat-head">
          <div>
            <h1 className="agent-chat-title">Schreib mit dem Agenten</h1>
            <p className="agent-chat-lede">
              Klares Layout, Fokus auf Inhalt – inspiriert vom Look der Next.js-Startseite.
            </p>
          </div>
        </div>

        <div className="agent-chat-panel">
          <div ref={listRef} className="agent-chat-messages" role="log" aria-live="polite">
            {messages.map((m) => (
              <article
                key={m.id}
                className={`agent-bubble agent-bubble--${m.role}`}
                aria-label={m.role === "user" ? "Du" : "Assistent"}
              >
                <div className="agent-bubble-meta">{m.role === "user" ? "Du" : "Agent"}</div>
                <div className="agent-bubble-text">{m.content}</div>
              </article>
            ))}
            {isThinking ? (
              <div className="agent-thinking" aria-busy="true">
                <span className="agent-thinking-dot" />
                <span className="agent-thinking-dot" />
                <span className="agent-thinking-dot" />
                <span className="agent-thinking-label">Denkt nach…</span>
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
              placeholder="Nachricht eingeben…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
            />
            <div className="agent-composer-row">
              <p className="agent-hint">Enter senden · Shift+Enter Zeilenumbruch</p>
              <button type="button" className="agent-send" onClick={send} disabled={isThinking}>
                Senden
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
