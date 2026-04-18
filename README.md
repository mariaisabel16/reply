# reply — **TUM CampusPilot**

Studentisches Hilfstool (Arbeitstitel): **CampusPilot** für die **TU München** — Marke im UI: **TUM CampusPilot**.

## QandA-Agent (NAT-API; OpenAI, Ollama oder Demo)

```bash
cd CampusPilot/QandA_Agent
# see CampusPilot/QandA_Agent/SETUP.txt — then:
python -m uvicorn main:app --reload --port 8010
```

Ohne `OPENAI_API_KEY` und ohne `OLLAMA_BASE_URL` läuft ein **Demo-Modus** (Semester-JSON → formatierte Antwort).  
Das Frontend spricht den Agent über den Vite-Proxy **`/qanda`** an (→ `http://127.0.0.1:8010`); alternativ `VITE_AGENT_API` setzen.

## Start Frontend

```bash
cd CampusPilot/"FrontEnd Folder"
npm install
npm run dev