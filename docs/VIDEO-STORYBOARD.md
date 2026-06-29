# Video Storyboard — Mainframe AI Copilot (5 min)

Companion to [STEP-BY-STEP-GUIDE.md](./STEP-BY-STEP-GUIDE.md)

## Shot list

| # | Time | Shot | Audio / narration | On-screen text |
|---|------|------|-------------------|------------------|
| 1 | 0:00 | Black → JES log scroll, red highlight on `S0C7` | "2 AM. Claims batch CLMDAY01 abends. SLA at risk." | **S0C7 — Data Exception** |
| 2 | 0:20 | Split: engineer at console vs AI dashboard | "What if AI could do the first hour of triage?" | |
| 3 | 0:35 | Architecture diagram (Mermaid export) | "11 agents. One LangGraph pipeline." | Agent flow diagram |
| 4 | 1:00 | Terminal: venv + pip + generate data | "Two-minute setup." | Commands overlay |
| 5 | 1:30 | `uvicorn` start + `/health` curl | "API is live." | `healthy` badge |
| 6 | 2:00 | curl investigate — loading spinner | "Full incident: 8 log types." | File icons: JES, ABEND, JCL… |
| 7 | 2:30 | JSON response — zoom severity + root cause | "CRITICAL. S0C7. Invalid packed decimal." | Highlight boxes |
| 8 | 2:50 | JSON — runbook + guardrail | "Runbook matched. Restart needs approval." | `RB-ABEND-S0C7` |
| 9 | 3:10 | Streamlit dashboard load | "Ops-friendly UI." | |
| 10 | 3:20 | Upload files + Run Investigation click | | |
| 11 | 3:40 | Agent confidence chart | "Every agent reports confidence." | |
| 12 | 3:55 | Runbook tab + Download report | | |
| 13 | 4:10 | pytest 146 passed | "146 tests. Production-ready." | Green checkmarks |
| 14 | 4:30 | Docker Compose services grid | "Full stack: Redis, Prometheus, Grafana." | |
| 15 | 4:50 | End card: logo + repo link | "Try it today." | **Mainframe AI Copilot** |

## B-roll suggestions

- Scrolling JES log (`IEF142I`, `IEF450I`)
- ABEND dump text (`CEE3202S`, `OFFSET`)
- CA-7 scheduler screen (generic)
- ServiceNow ticket mockup with copilot summary pasted

## Recording setup

```
Resolution:  1920×1080 or 1280×720
Frame rate:  30 fps
Terminal:    dark theme, font 16+
Browser:     zoom 110% for Streamlit
Mic:         quiet room, -12 dB peak
Length:      4:45 – 5:15 target
```

## Files to have open before recording

1. Terminal 1 — API running
2. Terminal 2 — curl command ready in clipboard
3. Browser tab 1 — Streamlit `localhost:8501`
4. Browser tab 2 — Swagger `localhost:8000/docs`
5. Finder — `logs/jes/jes_CLMDAY01_000.log` and `logs/abend/abend_S0C7_000.log`

## One-take command sequence

```bash
# Terminal 1
cd mainframe-ai-copilot && source .venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 2 (after health check)
streamlit run dashboard/app.py

# Terminal 3 (for pytest ending shot)
pytest tests/ -q
```
