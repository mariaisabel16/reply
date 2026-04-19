import { useRef } from "react";
import { BRAND } from "../branding";
import { AgentChat, type AgentChatHandle } from "./AgentChat";
import { CampusCrawlPanel } from "./CampusCrawlPanel";
import "./DashboardShell.css";

type Props = {
  username: string | null;
};

const MOCK_AGENTS = [
  { id: "Room Finder", name: "Room Finder", color: "#3b82f6" },
  { id: "Chief", name: "Orchestrator", color: "#f97316" },
  { id: "strat", name: "Strategist", color: "#22c55e" },
];

const USEFUL_LINKS: { label: string; href: string }[] = [
  { label: "Artemis", href: "https://artemis.tum.sexy/" },
  { label: "TUM Hunger", href: "https://hunger.tum.sexy/" },
  { label: "Reddit TUM", href: "https://reddit.tum.sexy/" },
  { label: "Guessr Game TUM", href: "https://guessr.tum.sexy/" },
  { label: "TUM Matching System", href: "https://matching-in.cit.tum.de/" },
  { label: "TUM Zulip", href: "https://zulip.cit.tum.de/login/" },
  { label: "TUM Studium", href: "https://www.tum.de/studium" },
  { label: "Campus & Moodle (my)", href: "https://www.campus.tum.de/" },
];

export function DashboardShell({ username }: Props) {
  const orchestrationChatRef = useRef<AgentChatHandle>(null);

  return (
    <div className="dashboard">
      <aside className="dash-sidebar" aria-label="Hauptnavigation">
        <div className="dash-brand">{BRAND.name.replace(" ", " · ").toUpperCase()}</div>

        <nav className="dash-nav" aria-label="Core system">
          <p className="dash-nav-label">Core system</p>
          <button type="button" className="dash-nav-item dash-nav-item--active">
            Command center
          </button>
          <button type="button" className="dash-nav-item">
            Academic records
          </button>
          <button type="button" className="dash-nav-item">
            Fleet & logistics
          </button>
        </nav>

        <div className="dash-vault">
          <p className="dash-nav-label">Identity vault</p>
          <div className="dash-vault-row">
            <span className="dash-vault-name">TUM</span>
            <span className="dash-dot dash-dot--ok" title="Verbunden" />
          </div>
          <p className="dash-vault-meta">{username ?? "—"}</p>
          <div className="dash-vault-row">
            <span className="dash-vault-name">Moodle</span>
            <span className="dash-dot dash-dot--ok" title="Verbunden" />
          </div>
          <p className="dash-vault-meta">synced user</p>
        </div>

        <div className="dash-agents">
          <p className="dash-nav-label">Active agents</p>
          <ul className="dash-agent-list">
            {MOCK_AGENTS.map((a) => (
              <li key={a.id} className="dash-agent-item">
                <span className="dash-agent-dot" style={{ background: a.color }} />
                {a.name}
              </li>
            ))}
          </ul>
        </div>

        <div className="dash-sidebar-footer">
          <div className="dash-orchestrator">
            <p className="dash-orchestrator-title">Orchestrator</p>
            <p className="dash-orchestrator-status">Running</p>
            <p className="dash-orchestrator-meta">AWS Bedrock · Demo / Ollama</p>
          </div>
          <button type="button" className="dash-terminate">
            Terminate session
          </button>
        </div>
      </aside>

      <div className="dash-main">
        <div className="dash-toolbar" role="region" aria-label="Arbeitsbereich">
          <p className="dash-toolbar-title">Command center</p>
        </div>

        <div className="dash-grid">
          <section className="dash-card dash-orchestration" aria-labelledby="orch-title">
            <div className="dash-card-head">
              <h2 id="orch-title" className="dash-card-title">
                Chat with CampusPilot
              </h2>
              <div className="dash-card-head-actions">
                <button
                  type="button"
                  className="dash-card-chat-reset"
                  onClick={() => void orchestrationChatRef.current?.resetChat()}
                  title="Server-Chat und Anmelde-Auswahl zurücksetzen"
                >
                  Neuer Chat
                </button>
                <span className="dash-card-badge">Live</span>
              </div>
            </div>
            <div className="dash-orchestration-body">
              <AgentChat ref={orchestrationChatRef} embedded />
            </div>
          </section>

          <section className="dash-card dash-useful-links" aria-labelledby="useful-links-title">
            <h2 id="useful-links-title" className="dash-card-title dash-card-title--sm">
              Useful links
            </h2>
            <p className="dash-useful-links-lede">Kurzzugriffe — öffnen in einem neuen Tab.</p>
            <ul className="dash-link-list">
              {USEFUL_LINKS.map((item) => (
                <li key={item.href}>
                  <a href={item.href} target="_blank" rel="noreferrer noopener" className="dash-link-item">
                    {item.label}
                    <span className="dash-link-icon" aria-hidden>
                      ↗
                    </span>
                  </a>
                </li>
              ))}
            </ul>
          </section>

          <section className="dash-card dash-study dash-study--crawl" aria-labelledby="crawl-title">
            <CampusCrawlPanel />
          </section>
        </div>
      </div>
    </div>
  );
}
