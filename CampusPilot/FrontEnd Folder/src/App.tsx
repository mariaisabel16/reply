import "./App.css";
import { AgentChat } from "./components/AgentChat";

export function App() {
  return (
    <div className="app-shell">
      <div className="app-glow" aria-hidden />
      <header className="app-header">
        <div className="app-brand">
          <span className="app-logo" aria-hidden />
          <div>
            <p className="app-title">KI-Agent</p>
            <p className="app-subtitle">Chat · React</p>
          </div>
        </div>
        <div className="app-header-actions">
          <span className="app-pill">Bereit</span>
        </div>
      </header>
      <main className="app-main">
        <AgentChat />
      </main>
    </div>
  );
}
