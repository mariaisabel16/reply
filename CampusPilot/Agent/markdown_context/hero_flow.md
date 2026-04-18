# TUM CampusPilot — Hero Flow

## Ziel

<<<<<<< HEAD
TUM CampusPilot (CampusPilot an der TUM) plant das naechste Semester nach einem einmaligen Login. Der Agent sammelt Studienstand, Interessen, Masterziel und die aktuelle Aufgabe, rankt passende Module, prueft Konflikte und Deadlines, fuehrt eine TUMonline-Aktion aus und gibt klares Feedback zurueck.
=======
CampusPilot plant das naechste Semester nach einem einmaligen Login. Der Agent sammelt Studienstand, Interessen, Masterziel und die aktuelle Aufgabe, rankt passende Module, prueft Konflikte und Deadlines, fordert eine Bestaetigung fuer die TUMonline-Aktion an, fuehrt die Aktion aus und gibt anschliessend Lernslot- und Bibliotheksvorschlaege zurueck.
>>>>>>> 1fadc548634dc2c73016c1ff8ca564df956d81c8

## Hauptablauf

1. Student loggt sich einmal ein.
2. Agent erfasst Interessen, Studienstand, gewuenschte ECTS und die aktuelle Aufgabe.
3. Agent rankt passende Module mit dieser Formel:

`Score = 0.35 * Interesse + 0.25 * Master-Fit + 0.15 * ECTS-Fit + 0.15 * Konfliktfreiheit + 0.10 * Materialverfuegbarkeit`

4. Agent prueft:
   - Voraussetzungen
   - Semesterverfuegbarkeit
   - Zeitkonflikte
   - ECTS-Abweichung
   - Anmelde-Deadlines
5. Agent erstellt einen `confirmation_payload` fuer die TUMonline-Aktion.
6. Nach Bestaetigung fuehrt der Agent die TUMonline-Aktion aus oder bereitet sie vor.
7. Danach erzeugt der Agent:
   - Lernslot-Vorschlaege
   - Bibliotheks-/Anny-Vorschlaege
8. Der Agent gibt strukturiertes Feedback zurueck.
9. Der Flow springt wieder zu Schritt 2 fuer neue Interessen oder eine neue Aufgabe.

## Aktueller MVP im Repo

- Deterministische Profil-Erstellung aus Mock-Daten
- Gewichtetes Modul-Ranking
- Deadline- und Konfliktpruefung
- Expliziter Workflow-Status (`ready_for_confirmation`, `completed`, `completed_with_warnings`)
- `confirmation_payload` fuer Confirm-before-action
- Simulierte TUMonline-Aktion mit Status pro Modul
- Lernslot- und Bibliotheksvorschlaege nach erfolgreicher Anmeldung
- Klarer Text-Output fuer Demo und Pitch
- Normalisierung eines TUMonline-Scraper-Exports fuer den Agent

## Agent Contract

### Input

Pflichtfelder:

- `program`
- `current_semester`
- `current_term`
- `desired_ects`
- `interests`
- `master_goal`
- `agent_task`

Optionale Felder:

- `study_history`
- `blocked_slots`
- `preferred_free_days`
- `pending_requirements`
- `total_ects`
- `user_id`
- `name`

### Output

Top-Level-Felder:

- `hero_flow`
- `workflow_state`
- `user_profile`
- `intent`
- `recommended_modules`
- `rejected_modules`
- `plan_summary`
- `confirmation_payload`
- `action_result`
- `study_slot_suggestions`
- `library_booking_suggestions`
- `next_step`
- `feedback`

## Was noch fuer den echten End-to-End Flow fehlt

- Echter Login- und Session-Layer
- Reale TUMonline-Integration statt Simulations-Action
- Reale Bibliotheksbuchung statt Vorschlag
- Echte Modul- und Fristdaten aus TUMonline oder einer stabilen API
- API zwischen Frontend und Python-Workflow
- Guardrails im UI fuer Confirm-before-action
