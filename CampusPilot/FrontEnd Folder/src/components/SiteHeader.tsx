import { useCallback, useEffect, useState } from "react";
import { fetchAgentHealth } from "../agentApi";
import { BRAND } from "../branding";
import { BrandMarkIcon } from "./BrandMarkIcon";
import "./SiteHeader.css";

type Props = {
  username: string;
  onLogout: () => void;
  logoutBusy: boolean;
};

export function SiteHeader({ username, onLogout, logoutBusy }: Props) {
  const [health, setHealth] = useState<"idle" | "ok" | "err">("idle");
  const [healthDetail, setHealthDetail] = useState<string>("");
  const [now, setNow] = useState(() => new Date());

  const display = username.split("@")[0] ?? username;
  const hour = now.getHours();
  const greet = hour < 11 ? "Guten Morgen" : hour < 18 ? "Guten Tag" : "Guten Abend";

  useEffect(() => {
    const t = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(t);
  }, []);

  const checkBackend = useCallback(async () => {
    setHealth("idle");
    setHealthDetail("Prüfe …");
    try {
      const h = await fetchAgentHealth();
      setHealth("ok");
      setHealthDetail(h.mode ? `OK · ${h.mode}` : "OK");
    } catch (e) {
      setHealth("err");
      setHealthDetail(e instanceof Error ? e.message : "Nicht erreichbar");
    }
  }, []);

  useEffect(() => {
    void checkBackend();
  }, [checkBackend]);

  const dateStr = new Intl.DateTimeFormat("de-DE", {
    weekday: "short",
    day: "numeric",
    month: "short",
  }).format(now);

  return (
    <header className="site-header">
      <div className="site-header-brand">
        <span className="site-header-logo" aria-hidden>
          <BrandMarkIcon variant="header" className="site-header-mark" />
        </span>
        <div className="site-header-titles">
          <span className="site-header-name">{BRAND.name}</span>
          <span className="site-header-tag">{BRAND.tagline}</span>
        </div>
      </div>

      <nav className="site-header-actions" aria-label="Schnellzugriff">
        <a
          className="site-header-btn site-header-btn--ghost"
          href="https://www.tum.de/studium"
          target="_blank"
          rel="noreferrer noopener"
        >
          TUM Studium
        </a>
        <button type="button" className="site-header-btn site-header-btn--ghost" onClick={() => void checkBackend()}>
          Agent-Status
          <span
            className={`site-header-ping site-header-ping--${health}`}
            title={healthDetail || "Backend"}
            aria-label={health === "ok" ? "Backend erreichbar" : health === "err" ? "Backend-Fehler" : "Backend wird geprüft"}
          />
        </button>
      </nav>

      <div className="site-header-user">
        <time className="site-header-date" dateTime={now.toISOString()}>
          {dateStr}
        </time>
        <div className="site-header-greet">
          <span className="site-header-greet-line">
            {greet}, <strong>{display}</strong>
          </span>
          <span className="site-header-email" title={username}>
            {username}
          </span>
        </div>
        <button
          type="button"
          className="site-header-btn site-header-btn--primary"
          onClick={() => void onLogout()}
          disabled={logoutBusy}
        >
          {logoutBusy ? "…" : "Abmelden"}
        </button>
      </div>
    </header>
  );
}
