import { useState } from "react";
import "./App.css";
import { CompanionMascot } from "./components/CompanionMascot";
import { DashboardShell } from "./components/DashboardShell";
import { LoginGate } from "./components/LoginGate";

export function App() {
  const [sessionUser, setSessionUser] = useState<string | null>(null);

  return (
    <div className="app-shell app-shell--dashboard">
      <LoginGate onSessionChange={setSessionUser}>
        <DashboardShell username={sessionUser} />
      </LoginGate>
      <CompanionMascot />
    </div>
  );
}
