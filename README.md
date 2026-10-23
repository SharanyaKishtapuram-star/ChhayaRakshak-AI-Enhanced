# ChhayaRakshak AI 🌿

> **AI-powered Urban Heat Protection System** — National Hackathon Submission

ChhayaRakshak AI helps cities and citizens understand, visualise, and reduce urban heat exposure using real-time weather data, computer vision, and multilingual AI assistance.

---

## Features

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Heat Exposure Risk Analysis** | Real-time risk scoring (0–10) for any Indian city using Open-Meteo weather data |
| 2 | **AI-Based Shade & Infrastructure Detection** | Upload a street/park photo and get shade, green cover, and sky percentage with OpenCV |
| 3 | **Interactive Urban Heat Vulnerability Map** | Leaflet map showing live heat-risk colour markers for 32 Indian cities |
| 4 | **Budget Optimizer for Cooling Interventions** | Greedy knapsack solver recommends the best cooling actions within your budget |
| 5 | **Multilingual AI Heat Protection Assistant** | Ask heat-safety questions in English, Hindi (हिंदी), or Telugu (తెలుగు) via Gemini |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | Python 3.10 + FastAPI + Uvicorn |
| Database | SQLite + SQLAlchemy |
| AI | Google Gemini API (`google-genai` SDK) |
| Weather | Open-Meteo API (free, no key required) |
| Maps | Leaflet + react-leaflet + OpenStreetMap |
| Image Analysis | OpenCV 4.10 |
| Budget Solver | Greedy value-density algorithm (local, no external API) |

---

## Project Structure

```
ChhayaRakshak-AI-Fresh/
├── .venv/                        ← Python virtual environment (repo root)
│
├── backend/
│   ├── main.py                   ← FastAPI app, registers all routers
│   ├── requirements.txt          ← Python dependencies
│   ├── pytest.ini                ← Test configuration
│   ├── .env.example              ← Template for environment variables
│   ├── .env                      ← Your secrets (NOT committed)
│   │
│   ├── routers/
│   │   ├── heat_risk.py          ← GET /api/heat-risk
│   │   ├── shade_detection.py    ← POST /api/shade/analyze
│   │   ├── vulnerability_map.py  ← GET /api/map/cities
│   │   ├── budget_optimizer.py   ← POST /api/budget/optimize
│   │   └── assistant.py          ← GET/POST /api/assistant/*
│   │
│   ├── services/
│   │   ├── weather_service.py    ← Open-Meteo geocoding + forecast
│   │   ├── opencv_service.py     ← HSV-based shade/green/sky analysis
│   │   └── gemini_service.py     ← Gemini multilingual assistant
│   │
│   └── tests/                    ← 139 tests, all passing
│
└── frontend/
    ├── src/
    │   ├── App.jsx               ← React Router — 6 routes
    │   ├── pages/
    │   │   ├── Home.jsx
    │   │   ├── HeatRisk.jsx
    │   │   ├── ShadeDetection.jsx
    │   │   ├── VulnerabilityMap.jsx
    │   │   ├── BudgetOptimizer.jsx
    │   │   └── Assistant.jsx
    │   ├── components/
    │   │   └── Navbar.jsx
    │   └── services/
    │       └── api.js            ← All API calls to FastAPI
    └── vite.config.js            ← Proxy: /api → http://127.0.0.1:8001
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Git

### 1. Clone the repository

```bash
git clone https://github.com/your-username/ChhayaRakshak-AI-Fresh.git
cd ChhayaRakshak-AI-Fresh
```

### 2. Set up the Python virtual environment

```powershell
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt
```

```bash
# macOS / Linux
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
```

### 3. Configure environment variables

```powershell
# Copy the template
copy backend\.env.example backend\.env
```

Open `backend/.env` and fill in your keys:

```env
# Required for Feature 5 (AI Assistant)
# Get a free key at: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Optional — not currently used (no key needed for Open-Meteo)
OPENMETEO_BASE_URL=https://api.open-meteo.com/v1
GEOCODING_BASE_URL=https://geocoding-api.open-meteo.com/v1
```

> Features 1–4 work without any API key. Only Feature 5 (AI Assistant) requires `GEMINI_API_KEY`.

### 4. Start the backend

```powershell
# Windows (PowerShell) — from repo root
cd backend
..\.venv\Scripts\uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

```bash
# macOS / Linux — from repo root
cd backend
../.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

Backend will be live at: http://127.0.0.1:8001  
Interactive API docs: http://127.0.0.1:8001/docs

### 5. Start the frontend

Open a **new terminal** from the repo root:

```powershell
cd frontend
npm install
npm run dev
```

Frontend will be live at: http://localhost:5173

---

## Running Tests

All 139 tests must pass before any code is merged.

```powershell
# Windows (PowerShell) — from repo root
cd backend
..\.venv\Scripts\pytest -v
```

```bash
# macOS / Linux — from repo root
cd backend
../.venv/bin/pytest -v
```

Expected output:
```
========================= 139 passed in X.XXs =========================
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/heat-risk?city=Hyderabad` | Heat risk analysis for a city |
| POST | `/api/shade/analyze` | Upload image for shade/green/sky analysis |
| GET | `/api/map/cities` | Live heat risk for 32 Indian cities |
| POST | `/api/budget/optimize` | Budget optimizer for cooling interventions |
| GET | `/api/assistant/status` | Check if Gemini API key is configured |
| POST | `/api/assistant/ask` | Ask a heat-protection question (multilingual) |

Full interactive docs with request/response schemas: http://127.0.0.1:8001/docs

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes (Feature 5) | Google Gemini API key — get free at [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| `OPENMETEO_BASE_URL` | No | Override Open-Meteo forecast base URL (for testing) |
| `GEOCODING_BASE_URL` | No | Override Open-Meteo geocoding base URL (for testing) |

> **Security:** `.env` files are listed in `.gitignore` and are never committed to Git.

---

## Feature Walkthrough

### Feature 1 — Heat Exposure Risk Analysis
Type any Indian city name → get real-time temperature, humidity, wind speed, a risk score (0–10), risk level (Low / Moderate / High / Extreme), and actionable cooling recommendations.

### Feature 2 — Shade & Infrastructure Detection
Upload a street, park, or neighbourhood photo → OpenCV analyses pixel colours using HSV thresholds to quantify shade coverage, green vegetation, and open sky exposure. Returns an infrastructure score and tailored recommendations.

### Feature 3 — Urban Heat Vulnerability Map
An interactive Leaflet map displays 32 Indian cities with colour-coded risk markers (green → yellow → orange → red) based on live weather data fetched concurrently.

### Feature 4 — Budget Optimizer
Enter your budget (in lakhs ₹) and area type (urban/peri-urban/rural) → the system selects the highest-impact cooling interventions (shade trees, cool roofs, misting stations, etc.) that fit within the budget using a greedy value-density algorithm.

### Feature 5 — Multilingual AI Assistant
Ask any heat-protection question in English, Hindi, or Telugu. Powered by Google Gemini with a custom system prompt focused on urban heat safety in Indian cities.

---

## Development Notes

- The Vite dev server proxies `/api/*` requests to `http://127.0.0.1:8001` — no CORS issues during development
- `google-generativeai` is deprecated; this project uses the current `google-genai` SDK
- `opencv-python==4.10.0.84` is pinned because 4.9.x is incompatible with NumPy 2.x
- The virtual environment is placed at the **repo root** (`.venv/`), not inside `backend/`

---

## License

MIT License — free to use for educational and hackathon purposes.
