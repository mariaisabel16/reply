import { BRAND } from "../branding";
import { AgentChat } from "./AgentChat";
import { CampusCrawlPanel } from "./CampusCrawlPanel";
import "./DashboardShell.css";

type Props = {
  username: string | null;
};

const MOCK_AGENTS = [
  { id: "scout", name: "Scout-01", color: "#3b82f6" },
  { id: "tutor", name: "Tutor-Alpha", color: "#f97316" },
  { id: "strat", name: "Strategist", color: "#22c55e" },
];

const MOCK_CONSOLE = [
  "[18:16:56] AGENT_STRATEGIST: Sync complete — TUMonline session valid.",
  "[18:17:02] SCOUT_01: No new room conflicts for SS 2026.",
  "[18:17:41] TUTOR_ALPHA: Slides checksum OK (MA9712).",
];

const MOCK_LUNCH = [
  { dish: "Almond curry with tofu", price: "3,50 €" },
  { dish: "Pasta bar — pesto", price: "4,20 €" },
  { dish: "Soup of the day", price: "2,80 €" },
];

export function DashboardShell({ username }: Props) {
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
          <div className="dash-toolbar-actions">
            <button type="button" className="dash-toolbar-chip">
              TUMonline-Sync <span className="dash-toolbar-chip-meta">(demnächst)</span>
            </button>
            <button type="button" className="dash-toolbar-chip">
              Planer <span className="dash-toolbar-chip-meta">(Mock)</span>
            </button>
          </div>
        </div>

        <div className="dash-grid">
          <section className="dash-card dash-orchestration" aria-labelledby="orch-title">
            <div className="dash-card-head">
              <h2 id="orch-title" className="dash-card-title">
                Autonomous orchestration log
              </h2>
              <span className="dash-card-badge">Live</span>
            </div>
            <div className="dash-orchestration-body">
              <AgentChat embedded />
            </div>
          </section>

          <section className="dash-card dash-goal" aria-labelledby="goal-title">
            <h2 id="goal-title" className="dash-card-title dash-card-title--sm">
              Goal input
            </h2>
            <textarea
              className="dash-goal-input"
              rows={5}
              placeholder="Describe what you want the campus co-pilot to achieve…"
              readOnly
              defaultValue="Plan SS 2026 electives without timetable clashes."
            />
            <button type="button" className="dash-goal-btn">
              Process goal →
            </button>
          </section>

          <section className="dash-card dash-console" aria-labelledby="console-title">
            <h2 id="console-title" className="dash-card-title dash-card-title--mono">
              _ CONSOLE_SESSION
            </h2>
            <pre className="dash-console-pre">
              {MOCK_CONSOLE.join("\n")}
              {"\n"}
            </pre>
          </section>

          <section className="dash-card dash-study dash-study--crawl" aria-labelledby="crawl-title">
            <CampusCrawlPanel />
          </section>

          <section className="dash-card dash-interop" aria-labelledby="interop-title">
            <h2 id="interop-title" className="dash-card-title dash-card-title--sm">
              Service interop
            </h2>
            <div className="dash-interop-grid">
              <div>
                <span className="dash-interop-name">TUM</span>
                <span className="dash-interop-state dash-interop-state--ok">Authenticated</span>
              </div>
              <div>
                <span className="dash-interop-name">Moodle</span>
                <span className="dash-interop-state dash-interop-state--ok">Authenticated</span>
              </div>
              <div>
                <span className="dash-interop-name">ZHS</span>
                <span className="dash-interop-state dash-interop-state--off">Disconnected</span>
              </div>
              <div>
                <span className="dash-interop-name">Library</span>
                <span className="dash-interop-state dash-interop-state--mid">Bridged</span>
              </div>
            </div>
          </section>

          <section className="dash-card dash-lunch" aria-labelledby="lunch-title">
            <h2 id="lunch-title" className="dash-card-title dash-card-title--sm">
              Lunch analytics
            </h2>
            <ul className="dash-lunch-list">
              {MOCK_LUNCH.map((row) => (
                <li key={row.dish} className="dash-lunch-item">
                  <span>{row.dish}</span>
                  <span className="dash-lunch-price">{row.price}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </div>
  );
}
