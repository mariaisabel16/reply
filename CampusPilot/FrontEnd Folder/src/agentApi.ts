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

export async function sendAgentMessage(
  message: string,
  history: ChatHistoryItem[],
): Promise<ChatResponse> {
  const base = agentApiBase();
  const res = await fetch(`${base}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ message, history }),
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
