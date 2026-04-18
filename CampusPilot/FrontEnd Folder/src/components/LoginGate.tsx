import { useCallback, useEffect, useState, type ReactNode } from "react";
import { fetchAuthMe, loginTum, logoutTum } from "../authApi";
import { BRAND } from "../branding";
import { SiteHeader } from "./SiteHeader";
import "./LoginGate.css";

type Props = {
  children: ReactNode;
  onSessionChange?: (username: string | null) => void;
};

export function LoginGate({ children, onSessionChange }: Props) {
  const [ready, setReady] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const [userField, setUserField] = useState("");
  const [passField, setPassField] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const me = await fetchAuthMe();
      const u = me.logged_in && me.tum_username ? me.tum_username : null;
      setUsername(u);
      onSessionChange?.(u);
    } catch {
      setUsername(null);
      onSessionChange?.(null);
    } finally {
      setReady(true);
    }
  }, [onSessionChange]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function submitLogin(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const me = await loginTum(userField.trim(), passField);
      setPassField("");
      const u = me.logged_in && me.tum_username ? me.tum_username : null;
      setUsername(u);
      onSessionChange?.(u);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleLogout() {
    setBusy(true);
    setError(null);
    try {
      await logoutTum();
      setUsername(null);
      onSessionChange?.(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  if (!ready) {
    return (
      <div className="login-gate login-gate--loading" role="status">
        <span className="login-loading-dot" aria-hidden />
        <span>Verbindung zum Server wird geprüft …</span>
      </div>
    );
  }

  if (!username) {
    return (
      <div className="login-gate">
        <div className="login-card">
          <header className="login-card-header">
            <p className="login-kicker">Anmeldung</p>
            <h1 className="login-title">{BRAND.name}</h1>
            <p className="login-tagline">{BRAND.tagline}</p>
          </header>

          <p className="login-lead">
            Mit deiner <strong>TUM-/LRZ-Kennung</strong> (wie beim Shibboleth-Login am Campus-Portal). Zugangsdaten
            werden auf dem Server <strong>verschlüsselt</strong> gespeichert und nur für geplante Portal-Schritte
            genutzt.
          </p>

          <form className="login-form" onSubmit={submitLogin}>
            <label className="login-label">
              Nutzername
              <input
                className="login-input"
                autoComplete="username"
                value={userField}
                onChange={(e) => setUserField(e.target.value)}
                required
                placeholder="z. B. ab12cde"
              />
            </label>
            <label className="login-label">
              Passwort
              <input
                className="login-input"
                type="password"
                autoComplete="current-password"
                value={passField}
                onChange={(e) => setPassField(e.target.value)}
                required
              />
            </label>
            {error ? <p className="login-error">{error}</p> : null}
            <button className="login-submit" type="submit" disabled={busy}>
              {busy ? "Wird angemeldet …" : "Anmelden"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <>
      <SiteHeader username={username} onLogout={() => void handleLogout()} logoutBusy={busy} />
      <div className="login-app-body">{children}</div>
    </>
  );
}
