import { useEffect, useRef, useState } from "react";
import type { CrawlStatusResponse } from "../authApi";
import { fetchCrawlStatus } from "../authApi";
import "./CampusCrawlPanel.css";

const POLL_MS = 2000;
const MAX_POLLS_BEFORE_WARN = 90;

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function formatScrapedAt(raw: string | null | undefined): string | null {
  if (!raw || typeof raw !== "string") return null;
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw;
  return d.toLocaleString("de-DE", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function karteiEntries(basis: Record<string, unknown>): [string, string][] {
  return Object.entries(basis)
    .map(([k, v]) => [k, String(v ?? "").trim()] as [string, string])
    .filter(([, v]) => v.length > 0 && v !== "—" && v !== "-");
}

export function CampusCrawlPanel() {
  const [status, setStatus] = useState<CrawlStatusResponse | null>(null);
  const [longWait, setLongWait] = useState(false);
  const pollsRef = useRef(0);

  useEffect(() => {
    let cancelled = false;
    let id: ReturnType<typeof setInterval> | undefined;

    async function poll() {
      try {
        const s = await fetchCrawlStatus();
        if (cancelled) {
          return;
        }
        if (!s) {
          setStatus({
            status: "error",
            message: "Crawl-Status nicht abrufbar (Session ungültig oder Serverfehler).",
          });
          if (id !== undefined) {
            window.clearInterval(id);
            id = undefined;
          }
          return;
        }
        setStatus(s);
        pollsRef.current += 1;
        const st = s?.status ?? "idle";
        if (pollsRef.current >= MAX_POLLS_BEFORE_WARN && (st === "pending" || st === "running")) {
          setLongWait(true);
        }
        if (st === "ok" || st === "error") {
          if (id !== undefined) {
            window.clearInterval(id);
            id = undefined;
          }
        }
      } catch {
        if (!cancelled) {
          setStatus({ status: "error", message: "Netzwerkfehler beim Abruf des Crawl-Status." });
          if (id !== undefined) {
            window.clearInterval(id);
            id = undefined;
          }
        }
      }
    }

    void poll();
    id = window.setInterval(() => {
      void poll();
    }, POLL_MS);

    return () => {
      cancelled = true;
      if (id !== undefined) {
        window.clearInterval(id);
      }
    };
  }, []);

  const s = status?.status ?? "idle";
  const done = s === "ok" || s === "error";

  if (!status && s === "idle") {
    return (
      <section
        className="crawl-panel crawl-panel--loading"
        aria-labelledby="crawl-title"
        aria-busy="true"
        aria-live="polite"
      >
        <div className="crawl-panel-head">
          <h2 id="crawl-title" className="crawl-panel-title">
            TUMonline-Sync
          </h2>
        </div>
        <div className="crawl-sync-loader crawl-sync-loader--compact">
          <div className="crawl-sync-spinner" aria-hidden />
          <p className="crawl-sync-label">Status wird geladen …</p>
        </div>
      </section>
    );
  }

  const data = status?.data;
  const curriculum = data && isRecord(data) && isRecord(data.curriculum_data) ? data.curriculum_data : null;
  const studentCard =
    data && isRecord(data) && isRecord(data.student_card_data) ? data.student_card_data : null;

  const modules = curriculum && Array.isArray(curriculum.modules) ? curriculum.modules : [];
  const studyStatus =
    curriculum && curriculum.study_status != null && String(curriculum.study_status).trim()
      ? String(curriculum.study_status).trim()
      : null;

  const syncing = s === "pending" || s === "running";
  const scrapedLabel = formatScrapedAt(status?.scraped_at ?? undefined);

  return (
    <section className="crawl-panel" aria-labelledby="crawl-title" aria-busy={syncing ? "true" : "false"}>
      <div className="crawl-panel-head">
        <h2 id="crawl-title" className="crawl-panel-title">
          TUMonline-Sync
        </h2>
        <span
          className={`crawl-badge crawl-badge--${done ? (s === "ok" ? "ok" : "err") : "run"}`}
          title={status?.scraped_at ?? undefined}
        >
          {s === "idle" && "Bereit"}
          {s === "pending" && "Warteschlange"}
          {s === "running" && "Läuft"}
          {s === "ok" && "Fertig"}
          {s === "error" && "Fehler"}
        </span>
      </div>

      {scrapedLabel && s === "ok" ? <p className="crawl-meta">Stand: {scrapedLabel}</p> : null}

      {syncing && (
        <div className="crawl-sync-block" aria-live="polite">
          <div className="crawl-sync-loader">
            <div className="crawl-sync-spinner" aria-hidden />
            <p className="crawl-sync-label">
              {s === "pending" ? "Starte Synchronisation …" : "Synchronisiere mit TUMonline …"}
            </p>
            <p className="crawl-sync-sublabel">
              Curriculum und Studierendenkartei werden geladen. Bitte warten.
            </p>
          </div>
          <p className="crawl-lead">
            Nach dem Login wird TUMonline im Hintergrund ausgelesen. Das kann einige Minuten dauern.
          </p>
        </div>
      )}

      {longWait && syncing ? (
        <p className="crawl-warn" style={{ margin: "0 1rem 0.75rem" }}>
          Ungewöhnlich lange. Prüfe{" "}
          <code style={{ fontSize: "0.75em" }}>playwright install chromium</code> und TUMonline-Erreichbarkeit.
        </p>
      ) : null}

      {s === "error" && status?.message ? <p className="crawl-error">{status.message}</p> : null}

      {s === "ok" && !curriculum && data ? (
        <pre className="crawl-raw">{JSON.stringify(data, null, 2).slice(0, 6000)}</pre>
      ) : null}

      {s === "ok" && curriculum ? (
        <div className="crawl-body">
          <div className="crawl-summary">
            <p className="crawl-summary-name">{String(curriculum.name ?? "Studierende/r")}</p>
            <p className="crawl-summary-sub">
              {[curriculum.semester ? String(curriculum.semester) : null, studyStatus].filter(Boolean).join(" · ")}
            </p>
            <div className="crawl-stat-row">
              {curriculum.matrikelnummer != null && String(curriculum.matrikelnummer).trim() ? (
                <div className="crawl-stat-pill">
                  <span>Matrikel</span>
                  <kbd>{String(curriculum.matrikelnummer)}</kbd>
                </div>
              ) : studentCard && studentCard.matrikelnummer != null ? (
                <div className="crawl-stat-pill">
                  <span>Matrikel</span>
                  <kbd>{String(studentCard.matrikelnummer)}</kbd>
                </div>
              ) : null}
              {curriculum.ects && isRecord(curriculum.ects) ? (
                <div className="crawl-stat-pill">
                  <span>Credits</span>
                  <kbd>
                    {String(curriculum.ects.ects_current ?? "?")} / {String(curriculum.ects.ects_total ?? "?")}
                  </kbd>
                </div>
              ) : null}
            </div>
          </div>

          {studentCard && isRecord(studentCard.basisinformationen) ? (
            <section className="crawl-section" aria-labelledby="crawl-kartei-title">
              <h3 id="crawl-kartei-title" className="crawl-section-title">
                Studierendenkartei
              </h3>
              <div className="crawl-kv-table">
                {karteiEntries(studentCard.basisinformationen as Record<string, unknown>).map(([k, v]) => (
                  <div key={k} className="crawl-kv-row">
                    <span className="crawl-k">{k}</span>
                    <span className="crawl-v">{v}</span>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          {modules.length > 0 ? (
            <section className="crawl-section" aria-labelledby="crawl-modules-title">
              <h3 id="crawl-modules-title" className="crawl-section-title">
                Module ({modules.length})
              </h3>
              <div className="crawl-modules-wrap">
                <ul className="crawl-modules">
                  {modules.slice(0, 50).map((m: unknown, i: number) => {
                    if (!isRecord(m)) return null;
                    const name = String(m.module_name ?? "—");
                    const stLabel = String(m.status ?? "").trim();
                    const positive = /positiv/i.test(stLabel);
                    return (
                      <li key={i} className="crawl-mod">
                        <span className="crawl-mod-name" title={name.length > 120 ? name : undefined}>
                          {name}
                        </span>
                        <div className="crawl-mod-meta">
                          {stLabel ? (
                            <span className={positive ? "crawl-mod-badge" : "crawl-mod-badge crawl-mod-badge--neutral"}>
                              {stLabel}
                            </span>
                          ) : null}
                          {m.credits_current != null && m.credits_total != null ? (
                            <span>
                              {String(m.credits_current)}/{String(m.credits_total)} Credits
                            </span>
                          ) : null}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
              {modules.length > 50 ? (
                <p className="crawl-muted" style={{ padding: "0.35rem 0 0", margin: 0 }}>
                  … {modules.length - 50} weitere in den Rohdaten.
                </p>
              ) : null}
            </section>
          ) : null}
        </div>
      ) : null}

      {s === "idle" ? (
        <p className="crawl-muted">Noch kein Crawl. Nach dem nächsten Login startet der Abruf automatisch.</p>
      ) : null}
    </section>
  );
}
