<div align="center">
  <h1>🗺️ TripSaathi</h1>
  <p>AI-powered student budget trip planner for India — paste a WhatsApp chat or type a prompt, get a full itinerary with real train options, hotel suggestions, food plan, and live budget breakdown.</p>

  ![Status](https://img.shields.io/badge/status-in_development-f59e0b?style=flat-square)
  ![Stack](https://img.shields.io/badge/stack-React_+_FastAPI-6366f1?style=flat-square)
  ![AI](https://img.shields.io/badge/AI-Groq_LLaMA_3.3-22c55e?style=flat-square)
  ![License](https://img.shields.io/badge/license-MIT-gray?style=flat-square)
</div>

---

> **Work in progress.** Backend core is functional — trip planning, WhatsApp parsing, train search, and database are working. Frontend UI is being built.

---

## The problem

Planning a group trip in India means 47 WhatsApp messages, 6 tabs open (IRCTC, MakeMyTrip, Zomato, Google Maps, Splitwise, and the weather app), and someone always ending up confused about how much it costs per person.

TripSaathi takes all of that and collapses it into one flow — paste your group chat or just describe the trip, and it figures out the rest.

---

## What works right now

**Trip planner** — POST your destination, days, budget, and number of people. The backend calls Groq (LLaMA 3.3-70b) and returns a day-wise itinerary with places, food suggestions, and cost breakdown, saved to PostgreSQL.

**WhatsApp chat parser** — Upload your group's exported `.txt` chat. The AI reads it and extracts destination, dates, group size, and budget — no form filling needed.

**Train search with AI recommendation** — Give it two city names (not codes — it figures those out). It scrapes [ConfirmTkt](https://confirmtkt.com) live using Playwright, parses all trains, scores them by speed + availability + price, and returns the best two picks with an explanation. Falls back to the next day automatically if no seats are available today.

**Trip history** — All generated plans are saved to PostgreSQL. You can fetch any past trip by ID.

---

## What's being built next

- [ ] Hotel and hostel suggestions (OYO API + curated fallback database)
- [ ] Food planner with Zomato integration and local dish recommendations
- [ ] React frontend — input screen, plan view, budget dashboard
- [ ] Live budget sliders — change group size or budget and only that part recalculates
- [ ] PDF export of the full trip plan
- [ ] Shareable trip link

---

## How the train search works

This was the most interesting part to build. IRCTC blocks scrapers, so we use ConfirmTkt instead.

```
City name input ("Bangalore", "Mysore")
        │
        ▼
Station code lookup → AI fallback if city not in dictionary
        │
        ▼
Playwright scrapes ConfirmTkt (headless Chromium)
        │
        ▼
Custom parser extracts train number, name, departure, arrival,
duration, class codes, fares, seat availability
        │
        ▼
Scoring algorithm (speed + seats + price + class variety → /100)
        │
        ▼
Top 8 trains sent to Groq AI with user preference
("budget" | "fast" | "comfort" | "balanced")
        │
        ▼
Returns best pick + second best with reasoning
```

The scraper handles AVL/WL status, waitlist confirmation chance, and automatically checks the next day if today has no available seats.

---

## Stack

| | |
|---|---|
| Frontend | React + Vite (in progress) |
| Backend | Python + FastAPI |
| AI | Groq API — LLaMA 3.3-70b Versatile |
| Scraping | Playwright (headless Chromium) |
| Database | PostgreSQL (psycopg2) |
| Deploy (planned) | Vercel (frontend) · Railway (backend) |

---

## Running locally

**Prerequisites:** Python 3.10+, Node 18+, a PostgreSQL database, Groq API key.

```bash
git clone https://github.com/abhigyan24-ops/tripSaathi.git
cd tripSaathi
```

**Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium   # needed for train scraper
cp .env.example .env          # fill in your keys
uvicorn main:app --reload
```

API docs auto-generated at `http://localhost:8000/docs`

**Frontend** *(UI in progress)*
```bash
cd frontend
npm install
npm run dev
```

---

## Environment variables

```env
GROQ_API_KEY=
DB_HOST=
DB_PORT=5432
DB_NAME=
DB_USER=
DB_PASSWORD=
```

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/plan-trip` | Generate a full trip plan |
| POST | `/parse-whatsapp` | Extract trip details from WhatsApp chat |
| POST | `/search-trains` | Find and rank trains between two cities |
| GET | `/trips` | Get all saved trips |
| GET | `/trips/{id}` | Get a specific saved trip |

**Example — plan a trip**
```json
POST /plan-trip
{
  "destination": "Goa",
  "days": 3,
  "budget": 8000,
  "people": 4
}
```

**Example — search trains**
```json
POST /search-trains
{
  "from_city": "Bangalore",
  "to_city": "Goa",
  "date": "20-05-2026",
  "preference": "budget",
  "check_multiple_dates": true
}
```

---

## Backend structure

```
backend/
├── main.py            # all API routes
├── database.py        # PostgreSQL connection + table setup
├── train_scraper.py   # ConfirmTkt scraper + scoring + AI recommendation
└── trip.py            # quick local test script
```

---

## Contributing

This project is actively being built. If you want to contribute, check the open issues or pick something from the roadmap above. Fork → branch → PR.

---

## License

MIT
