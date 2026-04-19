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
  const modulesData =
    data && isRecord(data) && isRecord(data.modules_data) ? data.modules_data : null;

  // Grades from new scraper; fallback to curriculum modules for old cached data
  const gradeItems: unknown[] = modulesData && Array.isArray(modulesData.items)
    ? modulesData.items
    : curriculum && Array.isArray(curriculum.modules) ? curriculum.modules : [];

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

      {s === "ok" && (curriculum || studentCard) ? (
        <div className="crawl-body">
          {(() => {
            // Name: prefer new scraper's full_name, fallback to curriculum
            const displayName =
              studentCard && studentCard.full_name != null && String(studentCard.full_name).trim()
                ? String(studentCard.full_name)
                : curriculum && curriculum.name != null
                  ? String(curriculum.name)
                  : "Studierende/r";

            const matrikel =
              studentCard && studentCard.matrikelnummer != null && String(studentCard.matrikelnummer).trim()
                ? String(studentCard.matrikelnummer)
                : curriculum && curriculum.matrikelnummer != null
                  ? String(curriculum.matrikelnummer)
                  : null;

            const fachsemester =
              studentCard && studentCard.fachsemester != null ? String(studentCard.fachsemester) : null;
            const studienId =
              studentCard && studentCard.studien_id != null && String(studentCard.studien_id).trim()
                ? String(studentCard.studien_id)
                : null;

            // Stats: prefer modulesData (new scraper), fallback to counting from gradeItems
            const passedCount = modulesData
              ? Number(modulesData.passed ?? 0)
              : gradeItems.filter((m: unknown) => isRecord(m) && /positiv/i.test(String(m.status ?? ""))).length;
            const inProgressCount = modulesData
              ? Number(modulesData.in_progress ?? 0)
              : gradeItems.filter((m: unknown) => {
                  if (!isRecord(m)) return false;
                  const st = String(m.status ?? "").toLowerCase().trim();
                  return st.length > 0 && !/positiv/i.test(st);
                }).length;
            const passedEcts = modulesData
              ? Number(modulesData.total_ects ?? 0)
              : gradeItems.reduce((sum: number, m: unknown) => {
                  if (!isRecord(m) || !/positiv/i.test(String(m.status ?? ""))) return sum;
                  return sum + (Number(m.credits_current) || 0);
                }, 0);

            return (
              <div className="crawl-summary">
                <p className="crawl-summary-name">{displayName}</p>
                {matrikel && (
                  <p className="crawl-summary-matrikel">
                    <span className="crawl-summary-matrikel-label">MATRIKEL</span>
                    <strong>{matrikel}</strong>
                  </p>
                )}
                {studyStatus && <p className="crawl-summary-sub">{studyStatus}</p>}
                <div className="crawl-stats-grid">
                  {fachsemester && (
                    <div className="crawl-stats-item">
                      <span className="crawl-stats-label">Fachsemester</span>
                      <span className="crawl-stats-value">{fachsemester}</span>
                    </div>
                  )}
                  {studienId && (
                    <div className="crawl-stats-item">
                      <span className="crawl-stats-label">Studien-ID</span>
                      <span className="crawl-stats-value" style={{ fontSize: "0.78rem" }}>{studienId}</span>
                    </div>
                  )}
                  {curriculum && isRecord(curriculum.ects) && (
                    <div className="crawl-stats-item">
                      <span className="crawl-stats-label">ECTS</span>
                      <span className="crawl-stats-value">
                        {String(curriculum.ects.ects_current ?? "?")} / {String(curriculum.ects.ects_total ?? "?")}
                      </span>
                    </div>
                  )}
                  {passedCount > 0 && (
                    <div className="crawl-stats-item crawl-stats-item--passed">
                      <span className="crawl-stats-label">Bestanden</span>
                      <span className="crawl-stats-value">{passedCount} <small>({passedEcts} ECTS)</small></span>
                    </div>
                  )}
                  {inProgressCount > 0 && (
                    <div className="crawl-stats-item crawl-stats-item--progress">
                      <span className="crawl-stats-label">Laufend</span>
                      <span className="crawl-stats-value">{inProgressCount}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })()}

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

          {gradeItems.length > 0 ? (
            <section className="crawl-section" aria-labelledby="crawl-modules-title">
              <h3 id="crawl-modules-title" className="crawl-section-title">
                {modulesData ? "Noten" : "Module"} ({gradeItems.length})
              </h3>
              <div className="crawl-modules-wrap">
                <table className="crawl-mod-table">
                  <thead>
                    <tr>
                      {modulesData && <th>ID</th>}
                      <th>Titel</th>
                      {modulesData ? <th>Note</th> : <th>Status</th>}
                      <th>Credits</th>
                      {modulesData && <th>Datum</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {gradeItems.slice(0, 100).map((m: unknown, i: number) => {
                      if (!isRecord(m)) return null;
                      if (modulesData) {
                        // New scraper data
                        const title = String(m.title ?? m.module_name ?? "—");
                        const grade = m.grade != null ? Number(m.grade) : null;
                        const gradeStr = grade != null ? grade.toFixed(1) : "—";
                        return (
                          <tr key={i}>
                            <td className="crawl-mod-table-id">{String(m.module_id ?? "—")}</td>
                            <td className="crawl-mod-table-title" title={title.length > 60 ? title : undefined}>
                              {title}
                            </td>
                            <td className={`crawl-mod-table-grade ${grade != null ? (grade <= 1.5 ? "grade-excellent" : grade <= 2.5 ? "grade-good" : grade <= 3.5 ? "grade-ok" : "grade-pass") : ""}`}>
                              {gradeStr}
                            </td>
                            <td className="crawl-mod-table-credits">{m.credits != null ? String(m.credits) : "—"}</td>
                            <td className="crawl-mod-table-date">{m.date != null ? String(m.date) : "—"}</td>
                          </tr>
                        );
                      } else {
                        // Old data fallback
                        const name = String(m.module_name ?? "—");
                        const stLabel = String(m.status ?? "").trim();
                        const positive = /positiv/i.test(stLabel);
                        return (
                          <tr key={i}>
                            <td className="crawl-mod-table-title" title={name.length > 80 ? name : undefined}>
                              {name}
                            </td>
                            <td>
                              {stLabel && (
                                <span className={positive ? "crawl-mod-badge" : "crawl-mod-badge crawl-mod-badge--neutral"}>
                                  {stLabel}
                                </span>
                              )}
                            </td>
                            <td className="crawl-mod-table-credits">
                              {m.credits_current != null && m.credits_total != null
                                ? `${String(m.credits_current)} / ${String(m.credits_total)}`
                                : "—"}
                            </td>
                          </tr>
                        );
                      }
                    })}
                  </tbody>
                </table>
              </div>
              {gradeItems.length > 100 && (
                <p className="crawl-muted" style={{ padding: "0.35rem 0 0", margin: 0 }}>
                  … {gradeItems.length - 100} weitere in den Rohdaten.
                </p>
              )}
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
