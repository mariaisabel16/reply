import "./App.css";
import { BRAND } from "./branding";
import { AgentChat } from "./components/AgentChat";
import { CompanionMascot } from "./components/CompanionMascot";

export function App() {
  return (
    <div className="app-shell">
      <div className="app-glow" aria-hidden />
      <header className="app-header">
        <div className="app-brand">
          <span className="app-logo" aria-hidden />
          <div>
            <p className="app-title">{BRAND.name}</p>
            <p className="app-subtitle">{BRAND.tagline}</p>
          </div>
        </div>
        <div className="app-header-actions">
          <span className="app-pill">Bereit</span>
        </div>
      </header>
      <main className="app-main">
        <AgentChat />
      </main>
      <CompanionMascot />
    </div>
  );
}
