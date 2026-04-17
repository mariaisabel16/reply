# Plan für euren Reply Makeathon

## Was die Jury wirklich sehen will

Das hochgeladene Deck gibt euch die Gewinnformel praktisch schon vor: Auf Seite 9 wird die fragmentierte „Service Jungle“ der studentischen Tools gezeigt, auf Seite 10 werden genau die vier attraktiven Richtungen benannt, auf Seite 11 wird ausdrücklich ein **„agent that acts“** verlangt, auf Seite 12 werden **Innovation/Ambition**, **UI/UX**, **Overall Quality** und **Presentation** **jeweils mit 25 Prozent** gewichtet, und auf den Setup-Seiten 13 bis 19 werden lokales Arbeiten, Cloud-Nutzung, AWS-Zugänge, Bedrock, S3, SageMaker und ein Beispiel-Repo als Beschleuniger genannt. Die richtige Schlussfolgerung ist deshalb nicht „möglichst viele Features“, sondern **ein klarer Schmerzpunkt, eine echte autonome Aktion, eine sehr gute Oberfläche und eine extrem saubere Demo-Story**. fileciteturn0file0

Das offizielle Repo auf entity["company","GitHub","developer platform"] stützt genau diesen pragmatischen Ansatz: Es liefert sofort nutzbare Beispiele für Bedrock, S3, S3 Vectors, RAG, LangChain und Python/TypeScript, weist ausdrücklich darauf hin, Zugangsschlüssel nie öffentlich zu speichern, und empfiehlt, für Bedrock **EU-Inference-Profile** zu nutzen. Ihr müsst also nicht bei null anfangen; ihr müsst die vorhandenen Starter sauber auf einen überzeugenden MVP zuschneiden. citeturn2view0turn0search3turn0search9

Die zentrale strategische Einsicht lautet daher: **Gewinnen werdet ihr nicht mit der breitesten Campus-Suite, sondern mit dem glaubwürdigsten studentischen Chief-of-Staff.** Der Agent muss sichtbar Zeit sparen, Friktion reduzieren und auf mindestens einer Plattform wirklich handeln. Alles, was darüber hinausgeht, ist Bonus. fileciteturn0file0

## Das Produkt, das ihr bauen solltet

Meine klare Empfehlung ist eine **Desktop-first Web-App** mit einem starken Namen und einer klaren Hero-Journey. Nennt das Produkt zum Beispiel **MATE** – euer persönlicher Campus Chief-of-Staff – und fokussiert es auf **zwei Ebenen**, aber nur **eine** davon als Hauptdemo.

**Die Hauptdemo** sollte sein: **ExamSprint Agent**.  
Der Flow lautet: *„Ich habe in 6 Tagen eine Klausur. Hol meine relevanten Moodle-Inhalte, erkenne die echten Prüfungsthemen, plane meine Lernblöcke, buche mir einen Platz in der Bibliothek und gib mir einen realistischen Tag-für-Tag-Plan.“*

**Die zweite Ebene** sollte sein: **MasterPath Planner**.  
Der Flow lautet: *„Ich bin im Bachelor, interessiere mich später für diese Master-Richtungen, welche Wahlmodule passen zu meinen Interessen, ECTS-Zielen, Voraussetzungen, Prüfungsformen und vorhandenen Lernmaterialien?“*

Warum genau diese Kombination? Weil sie drei der im Deck explizit genannten Richtungen elegant zusammenführt: **Autonomous Study Buddy**, **University Navigator** und **Study Career Agent**. Gleichzeitig passt sie perfekt auf die realen TUM-Systeme: **Moodle** ist die zentrale Lernplattform, **TUMonline** ist das Campus-Management für Lehrveranstaltungen, Prüfungen und Noten, und die entity["organization","TUM University Library","munich academic library"] bietet für Study Desks und Group Rooms eine Online-Reservierung mit Login per TUM-ID an. Das ist exakt die Art von systemübergreifender studentischer Friktion, die der Challenge-Text und das Deck adressieren. fileciteturn0file0 citeturn3search0turn4search2turn4search11turn3search2turn3search3turn3search7

Was ihr **wirklich** bauen solltet:

- Einen **einzigen Command-Einstieg**: „Plane mir die nächsten 6 Tage bis zur Prüfung“.
- Einen **Action Feed**, in dem der Agent transparent zeigt, was er gelesen, geplant und ausgeführt hat.
- Eine **echte Aktion**, idealerweise Bibliotheksbuchung oder zumindest vorbereitete Buchung mit finaler Nutzerbestätigung.
- Einen **sauberen Wochenplan** mit Lernblöcken, Themen, Moodle-Aufgaben und Verweisen auf relevante Ressourcen.
- Einen **zweiten Tab** für den MasterPath Planner, der Wahlmodule erklärt und priorisiert.

Was ihr **bewusst nur als Zusatz** baut:

- Altklausuren-Zählung als **Metadaten-Layer**.
- Workshop-/Event-Scout.
- Tiefere TUMonline-Automation für Prüfungsanmeldung.
- Proaktive tägliche Digest-Nachrichten.

Was ihr **nicht** bauen solltet:

- Keine native Mobile-App.
- Keine „Alles-für-alle“-Superplattform.
- Keine generelle Vollautomatisierung irreversibler Hochschulaktionen.
- Keine automatischen Downloads oder Paywall-Umgehungen bei Drittplattformen wie entity["company","Studocu","study materials platform"] oder entity["company","StudyDrive","study materials platform"]. Im MVP solltet ihr dort höchstens öffentliche Links, Counts, vom Nutzer bereitgestellte Nachweise oder manuell kuratierte Metadaten verwenden.  

Der wichtigste Produktentscheid ist also: **verkauft den ExamSprint Agent als Wow-Moment und den MasterPath Planner als Beweis, dass eure Architektur auch langfristige Studienplanung kann.**

## Der technische Aufbau

Ihr solltet **eine Web-App bauen**, nicht nur Markdowns und nicht eine native App. Markdown nutzt ihr intern als Austauschformat für Studienpläne, Agent-Logs, Export-Reports und Pitch-Notizen. Das eigentliche Produkt ist aber eine browserbasierte Oberfläche, weil das für Jury, Demo und Teamarbeit am wenigsten riskant ist.

Der sinnvollste 36-Stunden-Stack ist:

- **Frontend:** Next.js App Router  
- **Backend/API:** FastAPI  
- **Agent-Orchestrierung:** LangGraph oder ein sehr ähnlicher zustandsbasierter Workflow  
- **Browser-Automation:** Playwright  
- **LLMs/Embeddings/Storage:** die von entity["company","Amazon Web Services","cloud provider"] bereitgestellte AWS-Infrastruktur mit Bedrock, S3 und idealerweise S3 Vectors bzw. Bedrock Knowledge Bases  
- **State/Metadaten:** SQLite oder eine sehr kleine Postgres-Instanz, wenn ihr schon etwas habt  

Next.js eignet sich hier, weil ihr schnell eine saubere Routenstruktur, Layouts und Navigation für eine überzeugende Web-Oberfläche bekommt; FastAPI passt sehr gut zu einem Python-zentrierten Agenten-Backend und bringt automatische interaktive API-Dokumentation mit. Playwright ist offiziell genau für zuverlässige Web-Automation und auch für agentische Workflows geeignet. citeturn5search0turn5search6turn5search9turn5search1turn5search4turn5search7turn5search14

Für das Modell-Setup würde ich **nicht** experimentell alles gleichzeitig nutzen. Wenn euer Bedrock-Account Zugriff darauf hat, nehmt **Claude Sonnet 4.6** als primären Planungs- und Tool-Controller, **Amazon Nova Pro** für multimodale Eingaben wie Screenshots oder Dokumentansichten und **Amazon Titan Text Embeddings v2** für semantische Suche. So trennt ihr Denken, Parsing und Retrieval sauber. Bedrock unterstützt genau diese Art des einheitlichen Zugriffs auf verschiedene Foundation Models über eine verwaltete Plattform. citeturn7search4turn6view0turn6view1turn6view2

Für eure Wissensbasis gilt: **RAG ist nur für unstrukturierte Inhalte** da, nicht für alles.  
Nutzt RAG für:

- Moodle-Skripte, PDFs, Folien, Aufgabenblätter, Regeln
- Modulbeschreibungen
- Lernpläne und frühere Materialien
- kuratierte Notizen zu Wahlmodulen

Nutzt **strukturierte Tabellen** für:

- ECTS
- Semesterangebot
- Modul-Tags
- Prüfungstyp
- geschätzte Lernlast
- verfügbare Altklausuren-Counts
- gebuchte Study-Desk-Slots
- Nutzerpräferenzen

AWS macht euch diesen Teil leichter: S3 Vectors stellt eigene Vector Buckets und Vector Indexes für Vektordaten bereit, und Bedrock Knowledge Bases liefert einen gemanagten End-to-End-RAG-Workflow mit Ingestion, Retrieval und Antwortgenerierung. Für ein Hackathon-Team ist das viel realistischer als ein komplett selbst gebauter Retrieval-Stack. citeturn0search1turn0search19turn7search0turn7search1turn7search3turn7search8

SageMaker würde ich **nicht** zum Herzstück des Produkts machen, aber sehr wohl als Nebenwerkzeug für einen Team-Teil einsetzen: Official Docs beschreiben Notebook-Instanzen und Studio/Shared Spaces als vorkonfiguriertes Jupyter-Umfeld mit kollaborativen Bearbeitungsmöglichkeiten. Das ist ideal für die Person, die Datenbereinigung, Parsing und Retrieval testet. Die eigentliche Web-App sollte trotzdem im normalen Git-Repo leben. citeturn0search2turn0search5turn0search8turn0search20

Meine empfohlene Architektur ist deshalb sehr schlicht:

- **Frontend:** Chat/Command Bar, Calendar View, Study Plan View, Module Planner View, Action Review View
- **Agent Backend:** Intent Router, Planner, Retriever, Scheduler, Action Executor
- **Tools:** Moodle Reader, TUMonline Reader, Library Booker, Calendar Writer, Link Counter, Exporter
- **Knowledge Layer:** S3 + Bedrock Knowledge Base oder S3 Vectors
- **Audit Layer:** jeder Agentenschritt wird als verständliche Karte im UI angezeigt

Ganz wichtig: Nutzt die Tipps aus dem offiziellen Repo. Startet als Erstes mit dem Credential-Check, einem simplen Bedrock-Call und einem minimalen S3-Test. Verwendet EU-Inference-Profile und commitet niemals Zugangsdaten. Das Repo empfiehlt genau diese Reihenfolge und genau diese Sicherheitsdisziplin. citeturn2view0turn0search3turn0search9

## Die Rollen eures Fünferteams

Die größte Gefahr in ersten Hackathons ist nicht zu wenig Talent, sondern **diffuse Verantwortung**. Ihr braucht fünf klar getrennte Ownership-Bereiche. Jede Person bekommt ein eigenes „Produktstück“, ein eigenes Toolset und ein eigenes Done-Kriterium.

### Produktlead und Pitch

Diese Person ist nicht „die Person, die nicht codet“, sondern der Scope-Guardian. Sie entscheidet, was **nicht** gebaut wird, und sorgt dafür, dass ihr auf die Jury-Kriterien einzahlt.

**Werkzeuge:** Kanban-Board, Slides, Excalidraw oder Whiteboard, dieser Assistent für Copy, User Stories und Pitch-Feinschliff.

**Aufgaben:**
- Bis Stunde 2 die eine Hauptstory festziehen: ExamSprint zuerst, MasterPath als zweiter Tab.
- Bis Stunde 3 drei Personas definieren: Erstsemester, gestresster Klausur-Student, Bachelor-Student mit Master-Ziel.
- Bis Stunde 4 ein Backlog in nur drei Spalten festlegen: Must Have, Stretch, Kill.
- Alle 3 Stunden ein 10-Minuten-Stand-up moderieren.
- Ab Stunde 18 den Pitch parallel zur Entwicklung bauen.
- Ab Stunde 26 nur noch polishen, vergleichen, üben, schneiden.

**So macht die Person es richtig:**  
Sie sammelt Screenshots, Demo-Argumente und Impact-Zahlen. Sie formuliert immer wieder denselben Kernsatz: *„Wir haben keinen Chatbot gebaut, sondern einen studentischen Chief-of-Staff, der Informationen aus TUM-Systemen in echte Aktionen übersetzt.“* Sie stoppt jedes Feature, das keinen klaren Beweis für Autonomie, Nutzen oder UI bringt.

**Done-Kriterium:**  
6-Folien-Deck, 90-Sekunden-Kurzpitch, 3-Minuten-Live-Demo-Skript, Backup-Video und finale Sprecherrollen.

### Frontend und UX

Diese Person macht den Unterschied zwischen „cooles Projekt“ und „gewinnt vielleicht wirklich“. Die Jury bewertet UI/UX genauso stark wie Innovation.

**Werkzeuge:** Next.js, eine einfache Komponentenbibliothek, Figma oder direkt Coding, dieser Assistent für Microcopy, Screen-Flows und leere Zustände.

**Aufgaben:**
- Sofort drei Schlüsselscreens skizzieren: Startscreen, Action Feed, Study Plan.
- Bis Stunde 6 ein klickbares UI-Skelett mit Dummy-Daten erstellen.
- Bis Stunde 12 den kompletten Happy Path visuell machen, auch wenn das Backend noch mockt.
- Bis Stunde 20 API-Antworten anschließen.
- Bis Stunde 28 finalen Feinschliff machen: Fehlermeldungen, Ladezustände, Bestätigungsdialoge, Farben, Typografie, Responsiveness.

**So macht die Person es richtig:**  
Sie baut keine generische Chat-Oberfläche, sondern eine **Action-First-Oberfläche**. Nach jeder Agentenhandlung sieht man:
- *Was wurde verstanden?*
- *Welche Daten wurden gelesen?*
- *Was wird vorgeschlagen?*
- *Welche Aktion kann jetzt bestätigt werden?*

**Done-Kriterium:**  
Die Jury kann in unter 15 Sekunden verstehen, was die App tut, ohne dass ihr viel erklären müsst.

### Backend und Agent-Orchestrierung

Diese Person baut das Gehirn des Systems, aber bitte nicht als chaotischen Prompt-Sumpf. Das Backend muss deterministisch genug sein, um in einer Demo nicht zu sterben.

**Werkzeuge:** FastAPI, Pydantic, AWS SDK/Bedrock SDK, LangGraph oder ein eigener State-Machine-Flow, dieser Assistent für Schemas, Tool-Contracts und Prompt-Refinement.

**Aufgaben:**
- Erst JSON-Schemas definieren, dann Prompts schreiben.
- Endpunkte anlegen wie `/plan_exam`, `/plan_modules`, `/review_action`, `/execute_action`.
- Tool-Aufrufe strikt strukturieren: Retrieve, Rank, Plan, Confirm, Execute.
- Bei jeder Ausgabe eine Audit-Struktur mitschicken, damit das Frontend Agentenschritte anzeigen kann.
- Fallbacks einbauen: Wenn ein Tool ausfällt, gibt der Agent nicht auf, sondern wechselt sauber in „Assist Mode“.

**So macht die Person es richtig:**  
Sie baut **keinen** frei laufenden Autonomie-Monolithen, sondern einen kontrollierten Orchestrator. Der beste Hackathon-Agent wirkt intelligent, weil die **Ablauflogik** gut ist, nicht weil ein einzelner Prompt magisch alles löst.

**Done-Kriterium:**  
Es gibt mindestens einen zuverlässigen End-to-End-Flow, der mit echten oder simulierten Daten jedes Mal sauber durchläuft.

### Integrationen und Browser-Automation

Das ist die Person für den „agent that acts“-Beweis. Ohne diese Rolle bleibt ihr bei einer hübschen Beratungs-App; mit ihr seid ihr plötzlich Challenge-konform.

**Werkzeuge:** Playwright, Browser-Profile, DevTools, lokale Testkonten oder Demo-Sessions, dieser Assistent für DOM-Analyse, Selektor-Debugging und Failure-Fallbacks.

**Aufgaben:**
- So früh wie möglich testen, welche Plattform realistisch automatisierbar ist.
- Priorität eins: Bibliotheks-Reservierung oder zumindest ein sehr glaubwürdiger Dry-Run bis unmittelbar vor die Bestätigung.
- Priorität zwei: Moodle-Inhalte einlesen.
- Priorität drei: TUMonline nur, wenn ihr stabile Sessions und eindeutige Selektoren habt.
- Nutzerbestätigung vor jeder irreversiblen Aktion einbauen.

**So macht die Person es richtig:**  
Sie beginnt **nicht** mit Vollautomatisierung, sondern mit dem kleinsten beweisbaren Action Loop. Zum Beispiel:
1. Kurs auswählen  
2. Agent zieht relevante Materialien  
3. Agent setzt Lernblöcke  
4. Agent reserviert einen Desk oder bereitet die Reservierung bis zur finalen Bestätigung vor

**Done-Kriterium:**  
Mindestens **eine** sichtbare und für die Jury glaubwürdige Plattform-Aktion.

### Daten, RAG und Qualitätssicherung

Diese Person ist in Wahrheit euer „Realitätsanker“. Sie sorgt dafür, dass der Agent nicht nur flüssig spricht, sondern passable Antworten auf Basis brauchbarer Daten produziert.

**Werkzeuge:** S3, S3 Vectors oder Bedrock Knowledge Base, SQLite, kleine Python-Skripte, Testlisten, dieser Assistent für Extraktion, Strukturierung und Vergleich verschiedener Planungslogiken.

**Aufgaben:**
- Einen kleinen, sauberen Korpus aufbauen: Modulbeschreibungen, Moodle-Materialien, Beispielprüfungen, eigene Notizen.
- Daten strukturieren: Modulname, ECTS, Semester, Kategorie, Prüfungsform, geschätzte Schwierigkeit, Materialverfügbarkeit.
- Den MasterPath Planner als Rankingproblem modellieren.
- Drei Testfälle mit realen Personas durchspielen.
- Halluzinationen und falsche Zuordnungen manuell wegtesten.

**So macht die Person es richtig:**  
Sie widersteht der Versuchung, das gesamte Campus-Internet zu scrapen. Für einen Gewinner-MVP reicht ein kleiner, hochqualitativer Datensatz, wenn der Use Case glasklar und die Antwortqualität sichtbar gut ist.

**Done-Kriterium:**  
Die Pläne für mindestens drei studentische Profile wirken plausibel, nachvollziehbar und stabil reproduzierbar.

## Der 36-Stunden-Fahrplan

Der größte Trick ist, dass ihr nicht 36 Stunden „entwickelt“, sondern **36 Stunden sehr bewusst Risiken abbaut**. Die Reihenfolge ist entscheidend.

**Stunden 0 bis 2**  
Finale Scope-Entscheidung. Personas festlegen. Git-Repo aufsetzen. AWS-Zugang prüfen. Ein Board anlegen. Direkt den Verify/Hello-World-Pfad aus dem Beispiel-Repo oder ein minimales Bedrock/S3-Skript laufen lassen, damit ihr Credentials, Modellzugriff und Grundgerüst früh de-riskt. citeturn2view0turn7search4

**Stunden 2 bis 5**  
Wireframes erstellen. API-Verträge definieren. UI-Shell mit Dummy-Daten bauen. Parallel erste Playwright-Tests gegen Bibliothek/Moodle durchführen. In dieser Phase entscheidet ihr bereits, welche Aktion realistisch live gezeigt werden kann. citeturn3search2turn3search3turn3search0turn5search14

**Stunden 5 bis 9**  
Backend-Skelett, erste Agent-Pipeline, Logging und UI-Integration. Noch keine Perfektion. Wenn möglich, bereits ein einfacher Flow: Nutzer nennt Kurs + Prüfungsdatum, Agent erzeugt Lernplan aus Mock-Daten.

**Stunden 9 bis 14**  
Echter „Happy Path“ für ExamSprint. Moodle- oder Dokument-Parsing anschließen. Study-Plan-Timeline sichtbar machen. Bibliotheks-Action auf echten oder halb-echten Daten testen. Hier müsst ihr einen ersten Demo-Loop vorführbar haben.

**Stunden 14 bis 18**  
RAG und Ranking verbessern. Altklausuren-Counts oder öffentliche Link-Metadaten ergänzen. Bibliotheks-Action stabilisieren. Falls die echte Automation wackelt, jetzt auf einen sauberen Review-&-Confirm-Flow umstellen, nicht später.

**Stunden 18 bis 22**  
MasterPath Planner hinzufügen. Nur für einen begrenzten Modulraum, zum Beispiel einen konkreten Fakultätsbereich oder eine Handvoll sinnvoller Wahlmodule. Der Planner soll intelligentes Priorisieren zeigen, nicht die komplette Studienordnung der ganzen Universität lösen.

**Stunden 22 bis 26**  
UI-Polish, Fehlerfälle, Agent-Logs, Exportfunktion, Demo-Texte. Pitch-Deck wird parallel fertig. In dieser Phase entscheidet ihr auch, welche Screenshots und Vorher/Nachher-Vergleiche in die Slides kommen.

**Stunden 26 bis 30**  
Feature Freeze. Keine neuen Ideen mehr. Nur noch Bugfixing, Caching, Latenz reduzieren, Demo-Daten sichern, Backup-Modus absichern.

**Stunden 30 bis 33**  
Backup-Video aufnehmen. Demo mit Flugmodus-Simulation oder reduziertem Netz einmal testen. Klare Sprecherwechsel üben. Jede Person muss wissen, was sie sagt, wenn live etwas schiefgeht.

**Stunden 33 bis 36**  
Pitch proben, streichen, verdichten. Nichts Neues mehr bauen. Die letzten Stunden gewinnen nicht die Teams mit dem meisten Code, sondern die Teams mit der besten Klarheit.

Die harten Kill-Regeln sollten so aussehen:

- Wenn bis Stunde 12 kein glaubwürdiger Happy Path steht, streicht ihr Stretch Features.
- Wenn bis Stunde 18 keine stabile reale Buchung klappt, zeigt ihr eine Review-&-Confirm-Aktion plus realen Kalendereintrag.
- Wenn bis Stunde 22 der MasterPath Planner nur mittelmäßig ist, bleibt er im Pitch ein zweiter Tab und nicht euer Hero-Flow.
- Wenn bis Stunde 26 euer UI noch roh ist, stoppt ihr Backend-Arbeit und poliert die Oberfläche.  

Diese Disziplin zahlt direkt auf die vier 25-Prozent-Kriterien ein. fileciteturn0file0

## Wie ihr diesen Assistenten maximal nutzt

Wenn ihr diesen Assistenten klug benutzt, seid ihr als Anfänger deutlich schneller. Aber nutzt ihn **nicht** als Blackbox, sondern als **Team-Verstärker**.

Für den Produktlead:

> „Ich gebe dir jetzt unsere drei Kernfeatures. Reduziere sie auf einen 36-Stunden-MVP, formuliere 10 GitHub-Issues mit Priorität Must/Should/Kill und schreibe für jedes ein klares Done-Kriterium.“

Für Frontend/UX:

> „Schreibe mir für einen ExamSprint-Agenten die komplette Microcopy für Startscreen, Ladezustände, Action-Review, Fehlerfall und Erfolgsbildschirm. Tonalität: klar, studentisch, souverän.“

Für Backend:

> „Entwirf mir JSON-Schemas für exam_planning_request, module_planner_request, action_review_card und execution_result. Gib mir Feldnamen, Typen, Validierungen und zwei Beispielpayloads.“

Für Integrationen:

> „Ich poste dir jetzt den HTML-Ausschnitt oder Screenshot einer Reservierungsseite. Extrahiere die stabilsten Interaktionselemente, schlage robuste Selektorstrategien vor und gib mir einen Fallback-Plan, wenn IDs dynamisch sind.“

Für Daten/RAG:

> „Hier sind Modulbeschreibungen. Extrahiere daraus sauberes JSON mit ECTS, Semester, Themen-Tags, Prüfungsform, empfohlene Vorkenntnisse, wahrgenommene Schwierigkeit und Kandidaten für Master-Richtungen.“

Für den Pitch:

> „Schreibe mir einen 90-Sekunden-Pitch für eine Jury, die Innovation, UI/UX, Overall Quality und Presentation gleich gewichtet. Ziel: Nicht wie ein Chatbot klingen, sondern wie ein echter autonomer Studienassistent.“

Wenn ihr zusätzlich einen Coding Assistant nutzt, ist auch der Repo-Tipp nützlich, aktuelle LangChain-/LangGraph-Dokumentation via MCP an den Assistenten anzubinden, damit weniger veralteter Code vorgeschlagen wird. Das ist in einem schnellen Hackathon-Kontext tatsächlich wertvoll. citeturn2view0

## So präsentiert ihr das Projekt

Eure Präsentation muss nicht technisch überladen sein. Sie muss **unvermeidlich logisch** wirken.

Die Story sollte so aufgebaut sein:

**Problem.**  
Studenten springen zwischen Moodle, TUMonline, Bibliotheks-Reservierung und weiteren Portalen. Genau dieses fragmentierte Campus-Ökosystem visualisiert das Deck selbst bereits sehr stark auf der „Service Jungle“-Folie. fileciteturn0file0

**These.**  
„Studierende brauchen keinen weiteren Chatbot. Sie brauchen einen Agenten, der Kontext versteht, Prioritäten setzt und auf Plattformen handelt.“

**Produkt.**  
„MATE ist ein Campus Chief-of-Staff. Unser Hero-Use-Case ist ExamSprint: sechs Tage vor der Klausur zieht MATE relevante Materialien, priorisiert Themen, baut einen realistischen Lernplan und kümmert sich um den Lernort.“

**Technik.**  
„Wir nutzen AWS-Bausteine, die im Challenge-Setup ausdrücklich vorgesehen sind, insbesondere Bedrock für Modelle und S3/S3 Vectors bzw. Knowledge Bases für Retrieval; die Oberfläche läuft als Web-App, der Action-Layer über Browser-Automation.“ fileciteturn0file0 citeturn7search4turn7search0turn0search1turn5search14

**Impact.**  
Hier dürft ihr nicht abstrakt werden. Messt im Demo-Skript drei einfache, harte Sachen:
- Wie viele Portale musste der Student vorher öffnen?
- Wie viele manuelle Schritte spart ihr?
- Wie schnell bekommt der Student einen belastbaren 6-Tage-Plan?

**Demo-Reihenfolge.**
- Student gibt Kurs und Prüfungsdatum ein.
- App zeigt aktuelle Moodle-relevante Inhalte und priorisierte Prüfungsthemen.
- Agent schlägt Zeitblöcke vor.
- Agent reserviert einen Bibliotheksplatz oder bringt die Reservierung bis zur finalen Bestätigung.
- App zeigt den fertigen Plan.
- Danach zeigt ihr in 20 Sekunden den MasterPath Planner als zweiten Beweis der Plattform.

Das Deck gewichtet Präsentationsqualität exakt so stark wie die anderen drei Blöcke. Deshalb soll eure Live-Demo **kurz, kontrolliert und filmisch** sein. Drei Minuten live schlagen fast immer sieben Minuten API-Erklärung. fileciteturn0file0

Die stärksten Sätze für euch sind diese:

- „Wir haben nicht nur Wissen abgerufen, sondern studentische Reibung orchestriert.“
- „Unser System ist nicht nur beratend, sondern handlungsfähig.“
- „Wir haben bewusst einen realistischen Scope gewählt und den zuverlässigsten studentischen Pain Point priorisiert.“
- „Die gleiche Architektur kann später von ExamSprint zu Wahlmodulplanung, Event-Scouting und Career-Coaching wachsen.“

## Risiken und harte Scope-Grenzen

Der schnellste Weg, einen Hackathon zu verlieren, ist ein Projekt, das groß klingt und in der Demo nicht trägt. Eure No-Gos sollten deshalb glasklar sein.

**Kein Paywall-Bypass.**  
Ihr solltet keine Bezahlschranken oder Mitgliedschaften von Drittplattformen umgehen und keine automatischen Downloads fremder Materialien versprechen. Wenn ihr Altklausuren einbezieht, arbeitet mit öffentlichen Links, Metadaten, Nutzerfreigaben oder kuratierten Beispieldaten.

**Keine irreversiblen Klicks ohne Bestätigung.**  
Prüfungsanmeldungen, Kursanmeldungen und ähnliche Aktionen sollten im MVP immer einen Confirm-Schritt haben. Das erhöht Vertrauen und reduziert Demo-Risiko.

**Keine Vollabdeckung aller TUM-Systeme.**  
Ein stabiler Moodle-plus-Bibliothek-Flow ist wertvoller als fünf halbe Integrationen.

**Keine Geheimnisse im Repo.**  
Das offizielle Repo warnt ausdrücklich davor, Access Keys öffentlich zu speichern. Haltet euch daran, nutzt Umgebungsvariablen und EU-Inference-Profile. citeturn2view0turn0search3turn0search9

**Kein zu breiter Datenraum.**  
Für den MasterPath Planner reicht ein enger, gut strukturierter Modulkatalog für einen exemplarischen Studienbereich. Qualität schlägt Vollständigkeit.

**Kein Live-Demo-Roulette.**  
Nehmt immer ein Backup-Video und einen kompletten Fallback-Flow mit statischen Demo-Daten auf. Wenn die echte Plattform-Automation ausfällt, muss eure Story trotzdem weiterlaufen.

Wenn ihr diese Grenzen wirklich einhaltet, habt ihr genau das, was die Challenge verlangt: **ein kreatives, nützliches und glaubwürdiges agentisches Produkt, das nicht nur redet, sondern studentische Friktion sichtbar reduziert.**