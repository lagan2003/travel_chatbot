# 🌍 Agentic AI Travel Planner

A production-grade, multi-agent travel assistant built on **LangGraph** for orchestration, **Groq** for fast LLM inference, **FastAPI** for the backend, and **Streamlit** for a polished, multi-page UI.

It takes a natural-language travel query (or structured inputs) and:

1. **Extracts** the trip intent (source / destination / dates / budget / preferences / travelers).
2. **Searches** flights, hotels, and weather **in parallel** via async agents.
3. **Optimizes** the budget and picks the best flight + hotel combination.
4. **Generates** a day-by-day itinerary tuned to the forecast and budget.
5. **Adds** hidden-gem recommendations, **validates** for budget overrun, and **formats** a polished Markdown trip plan.

---

## ✨ Features

| Capability                       | Notes                                                                  |
| -------------------------------- | ---------------------------------------------------------------------- |
| Multi-agent LangGraph workflow   | 9 agents, fan-out to (flights ∥ hotels ∥ weather), fan-in to budget.   |
| Real OpenWeatherMap forecasting  | 5-day / 3-hour data aggregated to daily highs/lows. Mock fallback.     |
| AviationStack airline enrichment | Pulls real airline names to vary the synthesized route pool.           |
| Hotel pool with amenities        | Rich synthesized pool (rating, price, amenities, km from center).      |
| Dedicated **Flight NLP** page    | "Cheapest flights from Delhi to Dubai next weekend" → ranked results.  |
| Dedicated **Hotel NLP** page     | "Family hotels in Singapore under $200 with a pool" → filtered cards.  |
| Chat (streamed)                  | Server-streamed Groq responses via `/chat/stream`.                     |
| Saved Trips                      | JSON-file persistence — save / list / open / delete.                   |
| API Status Dashboard             | Live probe of LLM, flights, hotels, weather, plus cache stats.         |
| Caching + retries                | In-process TTL cache for API responses; exponential-backoff retry.     |
| Export                           | Markdown, styled HTML, real PDF (ReportLab).                           |
| Premium UI                       | Dark glass-morphism, gradients, animations, fully responsive.          |

---

## 🛠️ Tech Stack

- **LLM**: Groq Cloud — `llama-3.3-70b-versatile` (override via `GROQ_MODEL`)
- **Orchestration**: LangGraph + LangChain Core
- **Backend**: FastAPI + Uvicorn
- **Frontend**: Streamlit (multi-page, sidebar router)
- **APIs (optional, mocked if missing)**:
  - AviationStack — flight airline metadata
  - RapidAPI Hotels-com Provider — hotels (gracefully falls back to synthesized pool)
  - OpenWeatherMap — daily forecast
- **Schema validation**: Pydantic v2
- **HTTP**: httpx (async) + tenacity for retries
- **Export**: markdown2, ReportLab

---

## 📁 Project Structure

```text
├── main.py                   # FastAPI entrypoint (all endpoints)
├── requirements.txt
├── .env.example
├── agents/                   # LangGraph nodes
│   ├── intent_agent.py
│   ├── flight_agent.py
│   ├── hotel_agent.py
│   ├── weather_agent.py
│   ├── budget_agent.py
│   ├── itinerary_agent.py
│   ├── recommendation_agent.py
│   ├── validation_agent.py
│   └── formatter_agent.py
├── workflows/
│   └── graph.py              # LangGraph state machine
├── services/
│   ├── llm.py                # Groq wrapper (ChatGroq)
│   ├── flights.py            # AviationStack + synth pool
│   ├── hotels.py             # Hotels API + synth pool
│   ├── weather.py            # OpenWeatherMap + mock fallback
│   ├── nlp.py                # Regex + LLM hybrid query extractor
│   ├── pdf_export.py         # Markdown → HTML / PDF (ReportLab)
│   ├── storage.py            # JSON-file trip store
│   ├── status.py             # Aggregated health probe
│   └── cache.py              # TTL cache + retry decorator
├── models/
│   ├── schemas.py            # Pydantic models for everything
│   └── state.py              # AgentState TypedDict for LangGraph
├── prompts/
│   └── system_prompts.py     # One template per agent
├── frontend/
│   ├── app.py                # Sidebar router (entrypoint)
│   ├── common.py             # BACKEND URL, get_json / post_json / delete
│   ├── styles.py             # Premium dark theme CSS
│   ├── pages_planner.py      # 4-step itinerary planner
│   ├── pages_flight_nlp.py
│   ├── pages_hotel_nlp.py
│   ├── pages_saved.py
│   ├── pages_status.py
│   └── pages_chat.py
└── browser/                  # Optional Playwright link helpers
```

---

## 🚀 Quick start (local)

```bash
# 1. clone & enter
git clone https://github.com/<you>/<this-repo>.git
cd <this-repo>

# 2. virtual env
python -m venv venv
.\venv\Scripts\Activate.ps1     # Windows PowerShell
# source venv/bin/activate      # macOS / Linux

# 3. install
pip install -r requirements.txt

# 4. configure
copy .env.example .env          # then edit .env with your keys

# 5. run the backend
uvicorn main:app --port 8000 --reload

# 6. in a second terminal, run the frontend
streamlit run frontend\app.py
```

Open the Streamlit URL it prints (default `http://localhost:8501`). The sidebar pill should show **● Backend online**.

### Required keys

Only `GROQ_API_KEY` is **required**. Everything else has graceful fallbacks. Get a free Groq key at [console.groq.com](https://console.groq.com/keys).

```env
GROQ_API_KEY=gsk_xxx                       # required
GROQ_MODEL=llama-3.3-70b-versatile
AVIATIONSTACK_API_KEY=...                  # optional — enriches airline mix
HOTEL_API_KEY=...                          # optional — RapidAPI hotels-com
GOOGLE_WEATHER_API_KEY=...                 # optional — OpenWeatherMap key
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
CACHE_TTL_SECONDS=900
TRIPS_STORE_PATH=./saved_trips.json
```

---

## 🧠 Architecture

### LangGraph flow

```
                          ┌────────────┐
                          │   START    │
                          └─────┬──────┘
                                ▼
                          ┌────────────┐
                          │   intent   │   (extracts source/dest/dates/budget…)
                          └─────┬──────┘
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
        ┌──────────┐      ┌──────────┐      ┌──────────┐
        │ flights  │      │  hotels  │      │ weather  │   (async, parallel)
        └────┬─────┘      └────┬─────┘      └────┬─────┘
             └─────────────────┼──────────────────┘
                                ▼
                          ┌────────────┐
                          │   budget   │   (picks best F+H, computes daily $)
                          └─────┬──────┘
                                ▼
                          ┌────────────┐
                          │ itinerary  │   (day-by-day plan)
                          └─────┬──────┘
                                ▼
                          ┌────────────┐
                          │recommendation│ (hidden gems)
                          └─────┬──────┘
                                ▼
                          ┌────────────┐
                          │ validation │   (budget + date checks)
                          └─────┬──────┘
                                ▼
                          ┌────────────┐
                          │ formatter  │   (Markdown output)
                          └─────┬──────┘
                                ▼
                          ┌────────────┐
                          │    END     │
                          └────────────┘
```

### REST endpoints

| Endpoint                | Purpose                                            |
| ----------------------- | -------------------------------------------------- |
| `GET  /health`          | Liveness probe                                     |
| `GET  /status`          | Per-service health (LLM, flights, hotels, weather) |
| `POST /plan`            | Full multi-agent pipeline                          |
| `POST /select`          | Re-plan with the user's chosen flight + hotel      |
| `POST /filter`          | Deterministic NLP filter over a returned list      |
| `POST /flights/search`  | NLP flight search (regex + LLM hybrid)             |
| `POST /hotels/search`   | NLP hotel search                                   |
| `POST /chat/stream`     | Token-streamed Groq completion                     |
| `GET  /trips`           | List saved trips                                   |
| `POST /trips`           | Save a trip                                        |
| `GET  /trips/{id}`      | Open one                                           |
| `DELETE /trips/{id}`    | Delete one                                         |

Swagger UI is at `http://127.0.0.1:8000/docs`.

---

## 🧪 Smoke test

```bash
python test_workflow.py                       # imports + compiles workflow
curl http://127.0.0.1:8000/health             # → {"status": "ok"}
curl http://127.0.0.1:8000/status             # per-service report
```

---

## 📄 License

MIT.
