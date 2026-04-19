/** Base URL for QandA FastAPI (no trailing slash). Dev default: same-origin `/qanda` → Vite proxy. */
export function agentApiBase(): string {
  const raw = import.meta.env.VITE_AGENT_API?.trim();
  if (raw) return raw.replace(/\/$/, "");
  if (import.meta.env.DEV) return "/qanda";
  return "http://127.0.0.1:8010";
}

export type ChatHistoryItem = { role: "user" | "assistant"; content: string };

export type ChatResponse = {
  reply: string;
  debug_tools: unknown[];
};

export type ChatMessagesPayload = {
  messages: ChatHistoryItem[];
};

export type AgentHealth = {
  status: string;
  mode?: string;
};

export async function fetchAgentHealth(): Promise<AgentHealth> {
  const base = agentApiBase();
  const res = await fetch(`${base}/health`, { credentials: "include" });
  const text = await res.text();
  if (!res.ok) {
    throw new Error(text || `HTTP ${res.status}`);
  }
  try {
    return JSON.parse(text) as AgentHealth;
  } catch {
    return { status: "ok" };
  }
}

export async function fetchAgentChatMessages(): Promise<ChatHistoryItem[]> {
  const base = agentApiBase();
  const res = await fetch(`${base}/chat/messages`, { credentials: "include" });
  const text = await res.text();
  if (!res.ok) {
    throw new Error(text || `HTTP ${res.status}`);
  }
  const data = JSON.parse(text) as ChatMessagesPayload;
  return Array.isArray(data.messages) ? data.messages : [];
}

export async function resetAgentChat(): Promise<void> {
  const base = agentApiBase();
  const res = await fetch(`${base}/chat/reset`, {
    method: "POST",
    credentials: "include",
  });
  const text = await res.text();
  if (!res.ok) {
    throw new Error(text || `HTTP ${res.status}`);
  }
}

/** Konversation liegt serverseitig in der Session; `history` wird nicht mehr mitgeschickt. */
export async function sendAgentMessage(message: string): Promise<ChatResponse> {
  const base = agentApiBase();
  const res = await fetch(`${base}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ message }),
  });
  const text = await res.text();
  if (!res.ok) {
    let detail = text;
    try {
      const j = JSON.parse(text) as { detail?: string };
      if (typeof j?.detail === "string") detail = j.detail;
    } catch {
      /* keep raw */
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return JSON.parse(text) as ChatResponse;
}
