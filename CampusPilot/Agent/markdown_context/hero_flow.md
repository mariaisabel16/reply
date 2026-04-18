# CampusPilot Hero Flow

## Ziel

CampusPilot plant das naechste Semester nach einem einmaligen Login. Der Agent sammelt Studienstand, Interessen, Masterziel und die aktuelle Aufgabe, rankt passende Module, prueft Konflikte und Deadlines, fuehrt eine TUMonline-Aktion aus und gibt klares Feedback zurueck.

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
5. Agent fuehrt die TUMonline-Aktion aus oder bereitet sie vor.
6. Agent gibt klares Feedback zurueck.
7. Flow springt wieder zu Schritt 2 fuer neue Interessen oder eine neue Aufgabe.

## Aktueller MVP im Repo

- Deterministische Profil-Erstellung aus Mock-Daten
- Gewichtetes Modul-Ranking
- Deadline- und Konfliktpruefung
- Simulierte TUMonline-Aktion mit Status pro Modul
- Klarer Text-Output fuer Demo und Pitch

## Was noch fuer den echten End-to-End Flow fehlt

- Echter Login- und Session-Layer
- Reale TUMonline-Integration statt Simulations-Action
- Echte Datenquelle fuer Modulangebot, Fristen und Verfuegbarkeit
- Bibliotheks- oder Lernslot-Planung als eigener Schritt nach der Anmeldung
- Confirm-before-action im UI
- API zwischen Frontend und Python-Workflow
