from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
from database import get_connection, create_table
from train_scraper import search_and_recommend
import os
import json

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

create_table()

# ── Models ──────────────────────────────────────────
class TripRequest(BaseModel):
    destination: str
    days: int
    budget: int
    people: int

class TrainSearchRequest(BaseModel):
    from_city: str
    to_city: str
    date: str
    preference: str = "balanced"
    check_multiple_dates: bool = True

# ── Routes ──────────────────────────────────────────
@app.get("/")
def home():
    return {"message": "TripSaathi API is running!"}

@app.post("/plan-trip")
def plan_trip(request: TripRequest):
    prompt = f"""
    You are a travel planner API that returns only JSON. No explanations, no markdown, no extra text.

    Plan a {request.days}-day trip to {request.destination} 
    for {request.people} people with a total budget of ₹{request.budget}.

    Return ONLY this JSON structure, nothing else:
    {{
        "destination": "{request.destination}",
        "total_days": {request.days},
        "total_people": {request.people},
        "estimated_total_cost": <number in rupees>,
        "days": [
            {{
                "day": 1,
                "theme": "short theme for the day",
                "places": ["place1", "place2"],
                "food": ["food suggestion 1", "food suggestion 2"],
                "estimated_cost": <number in rupees>
            }}
        ],
        "tips": ["tip1", "tip2", "tip3"]
    }}

    Rules:
    - estimated_total_cost must be within the budget of ₹{request.budget}
    - Generate exactly {request.days} day objects in the days array
    - Return pure JSON only, no markdown, no backticks, no explanations
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    raw_text = response.choices[0].message.content
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()
    trip_data = json.loads(cleaned)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trips (destination, days, people, budget, plan)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (
        request.destination,
        request.days,
        request.people,
        request.budget,
        json.dumps(trip_data)
    ))
    trip_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()

    trip_data["id"] = trip_id
    return trip_data

@app.get("/trips")
def get_all_trips():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, destination, days, people, budget, created_at 
        FROM trips 
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    trips = []
    for row in rows:
        trips.append({
            "id": row[0],
            "destination": row[1],
            "days": row[2],
            "people": row[3],
            "budget": row[4],
            "created_at": str(row[5])
        })
    return {"trips": trips}

@app.get("/trips/{trip_id}")
def get_trip(trip_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT plan FROM trips WHERE id = %s", (trip_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row is None:
        return {"error": "Trip not found"}
    return row[0]

@app.post("/parse-whatsapp")
async def parse_whatsapp(file: UploadFile = File(...)):
    content = await file.read()
    chat_text = content.decode("utf-8", errors="ignore")[:6000]

    prompt = f"""
    Extract trip planning details from this WhatsApp group chat.
    Return ONLY a JSON object, no explanation, no markdown:
    {{
        "destination": "city name or null",
        "days": number or null,
        "people": number or null,
        "budget": number in INR or null
    }}

    If something is not mentioned, set it to null.
    Do not guess. Only extract what is clearly stated.

    Chat:
    {chat_text}
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    return json.loads(raw)

@app.post("/search-trains")
def search_trains(request: TrainSearchRequest):
    result = search_and_recommend(
        from_city=request.from_city,
        to_city=request.to_city,
        date=request.date,
        preference=request.preference,
        check_multiple_dates=request.check_multiple_dates
    )
    return result