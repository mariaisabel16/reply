import { agentApiBase } from "./agentApi";

export type MeResponse = { logged_in: boolean; tum_username?: string | null };

async function parseJson(res: Response): Promise<unknown> {
  const text = await res.text();
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

export async function fetchAuthMe(): Promise<MeResponse> {
  const base = agentApiBase();
  const res = await fetch(`${base}/auth/me`, { credentials: "include" });
  if (!res.ok) {
    return { logged_in: false };
  }
  const j = (await parseJson(res)) as MeResponse;
  return j && typeof j === "object" ? j : { logged_in: false };
}

export async function loginTum(tum_username: string, tum_password: string): Promise<MeResponse> {
  const base = agentApiBase();
  const res = await fetch(`${base}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ tum_username, tum_password }),
  });
  const j = await parseJson(res);
  if (!res.ok) {
    const detail =
      typeof j === "object" && j !== null && "detail" in j && typeof (j as { detail: unknown }).detail === "string"
        ? (j as { detail: string }).detail
        : typeof j === "string"
          ? j
          : `HTTP ${res.status}`;
    throw new Error(detail);
  }
  return j as MeResponse;
}

export async function logoutTum(): Promise<void> {
  const base = agentApiBase();
  await fetch(`${base}/auth/logout`, { method: "POST", credentials: "include" });
}
