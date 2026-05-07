from playwright.sync_api import sync_playwright
from groq import Groq
from dotenv import load_dotenv
import re
import json
import os
from datetime import datetime, timedelta

load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Common Indian city → station code mapping
STATION_CODES = {
    "bangalore": "SBC", "bengaluru": "SBC",
    "mumbai": "CSTM", "bombay": "CSTM",
    "delhi": "NDLS", "new delhi": "NDLS",
    "chennai": "MAS", "madras": "MAS",
    "hyderabad": "HYB",
    "kolkata": "KOAA", "calcutta": "KOAA",
    "pune": "PUNE",
    "mysuru": "MYS", "mysore": "MYS",
    "goa": "MAO", "madgaon": "MAO",
    "ahmedabad": "ADI",
    "jaipur": "JP",
    "lucknow": "LKO",
    "patna": "PNBE",
    "bhopal": "BPL",
    "nagpur": "NGP",
    "surat": "ST",
    "coimbatore": "CBE",
    "kochi": "ERS", "cochin": "ERS",
    "thiruvananthapuram": "TVC",
    "visakhapatnam": "VSKP", "vizag": "VSKP",
    "mangalore": "MAQ",
    "hubli": "UBL",
}


def city_to_station_code(city: str) -> str:
    """Convert city name to station code using lookup + AI fallback"""
    code = STATION_CODES.get(city.lower().strip())
    if code:
        return code

    # AI fallback for unknown cities
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"What is the main Indian Railway station code for {city}? Reply with ONLY the station code, nothing else. Example: NDLS"
        }]
    )
    return response.choices[0].message.content.strip().upper()


def parse_trains_from_text(text):
    trains = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    i = 0
    while i < len(lines):
        match = re.match(r'^(\d{5})(.+)$', lines[i])
        if match:
            train = {
                "number": match.group(1),
                "name": match.group(2).strip(),
                "departure": None,
                "arrival": None,
                "duration": None,
                "duration_minutes": None,
                "classes": []
            }

            j = i + 1
            while j < min(i + 60, len(lines)):
                line = lines[j]

                if re.match(r'^(\d{5})(.+)$', line):
                    break

                dur = re.match(r'^(\d+)h\s+(\d+)m$', line)
                if dur:
                    train["duration"] = f"{dur.group(1)}h {dur.group(2)}m"
                    train["duration_minutes"] = int(dur.group(1)) * 60 + int(dur.group(2))
                    j += 1
                    continue

                time_match = re.match(r'^(\d{2}:\d{2})\s+\w+$', line)
                if time_match:
                    if not train["departure"]:
                        train["departure"] = time_match.group(1)
                    elif not train["arrival"]:
                        train["arrival"] = time_match.group(1)
                    j += 1
                    continue

                cls_match = re.match(r'^(SL|3A|2A|1A|CC|2S|3E)$', line)
                if cls_match:
                    class_code = cls_match.group(1)
                    fare = None
                    status = "Unknown"
                    seats_available = 0
                    waitlist_number = 0

                    for k in range(j + 1, min(j + 6, len(lines))):
                        fare_match = re.match(r'^(₹\d+)$', lines[k])
                        if fare_match:
                            fare = fare_match.group(1)

                        avl_match = re.search(r'AVL\s*(\d+)', lines[k])
                        if avl_match:
                            seats_available = int(avl_match.group(1))
                            status = "Available"

                        wl_match = re.search(r'WL\s*(\d+)', lines[k])
                        if wl_match:
                            waitlist_number = int(wl_match.group(1))
                            status = "Waitlist"

                        if lines[k] == "Available":
                            status = "Available"
                        elif lines[k] == "Waitlist":
                            status = "Waitlist"

                        if re.match(r'^(SL|3A|2A|1A|CC|2S|3E)$', lines[k]):
                            break

                    if fare:
                        train["classes"].append({
                            "class": class_code,
                            "fare": fare,
                            "fare_number": int(fare.replace("₹", "")),
                            "status": status,
                            "seats_available": seats_available,
                            "waitlist_number": waitlist_number,
                            # Waitlist chance of confirmation
                            "confirm_chance": (
                                "High" if status == "Available" else
                                "Medium" if waitlist_number <= 10 else
                                "Low" if waitlist_number <= 30 else
                                "Very Low"
                            )
                        })

                j += 1

            if train["departure"] and train["classes"]:
                trains.append(train)
            i = j
        else:
            i += 1

    return trains


def score_train(train):
    """Give each train a numerical score out of 100"""
    score = 0

    # Duration score (faster = better, max 30 pts)
    if train["duration_minutes"]:
        if train["duration_minutes"] <= 150:
            score += 30
        elif train["duration_minutes"] <= 180:
            score += 20
        elif train["duration_minutes"] <= 240:
            score += 10

    available_classes = [c for c in train["classes"] if c["status"] == "Available"]

    # Availability score (more seats = better, max 30 pts)
    max_seats = max((c["seats_available"] for c in available_classes), default=0)
    if max_seats >= 100:
        score += 30
    elif max_seats >= 50:
        score += 20
    elif max_seats >= 20:
        score += 15
    elif max_seats > 0:
        score += 10

    # Price score (cheaper = better, max 20 pts)
    cheapest = min((c["fare_number"] for c in available_classes), default=9999)
    if cheapest <= 150:
        score += 20
    elif cheapest <= 300:
        score += 15
    elif cheapest <= 500:
        score += 10

    # Class variety score (more options = better, max 20 pts)
    score += min(len(available_classes) * 5, 20)

    train["score"] = score
    return train


def filter_and_score_trains(trains):
    """Filter available trains and score them"""
    available = []
    for train in trains:
        available_classes = [c for c in train["classes"] if c["status"] == "Available"]
        if available_classes:
            train["available_classes"] = available_classes
            train = score_train(train)
            available.append(train)

    # Sort by score descending
    available.sort(key=lambda x: x["score"], reverse=True)
    return available


def scrape_trains(from_code: str, to_code: str, date: str):
    """Scrape ConfirmTkt for trains"""
    url = f"https://www.confirmtkt.com/rbooking/trains/from/{from_code}/to/{to_code}/{date}"

    print(f"Scraping: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)

        try:
            page.wait_for_selector("text=Trains found", timeout=20000)
        except:
            pass

        page.wait_for_timeout(3000)
        raw_text = page.inner_text("body")
        browser.close()

    return raw_text


def ai_pick_best_train(trains, from_station, to_station, preference="balanced"):
    """Use AI to pick best train with preference awareness"""

    # Only send top 8 scored trains to AI to keep prompt short
    top_trains = trains[:8]
    trains_summary = json.dumps(top_trains, ensure_ascii=False, indent=2)

    preference_guide = {
        "budget": "Prioritize cheapest fare above all else",
        "fast": "Prioritize shortest travel time above all else",
        "comfort": "Prioritize AC classes (3A, 2A, 1A) even if more expensive",
        "balanced": "Balance between price, speed, and availability"
    }

    prompt = f"""
You are a smart Indian train booking assistant.
User preference: {preference_guide.get(preference, preference_guide["balanced"])}
Route: {from_station} → {to_station}

Available trains (pre-scored, higher score = better overall):
{trains_summary}

Pick the BEST and SECOND BEST train based on user preference.
Return ONLY this JSON, no explanation, no markdown:
{{
    "best_train": {{
        "number": "train number",
        "name": "train name",
        "departure": "HH:MM",
        "arrival": "HH:MM",
        "duration": "Xh Ym",
        "score": 85,
        "recommended_class": "SL or 3A etc",
        "recommended_fare": "₹XXX",
        "seats_available": 50,
        "why": "2-line reason why this is the best pick for this user"
    }},
    "second_best": {{
        "number": "train number",
        "name": "train name",
        "departure": "HH:MM",
        "arrival": "HH:MM",
        "duration": "Xh Ym",
        "score": 75,
        "recommended_class": "class code",
        "recommended_fare": "₹XXX",
        "seats_available": 30,
        "why": "2-line reason"
    }}
}}
"""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw.strip())


def search_and_recommend(
    from_city: str,
    to_city: str,
    date: str,
    preference: str = "balanced",
    check_multiple_dates: bool = True
):
    """
    Full pipeline:
    city name → station code → scrape → score → AI recommend
    
    preference: "budget" | "fast" | "comfort" | "balanced"
    date: DD-MM-YYYY
    """

    # Step 1: Convert city names to station codes
    print(f"Converting city names...")
    from_code = city_to_station_code(from_city)
    to_code = city_to_station_code(to_city)
    print(f"{from_city} → {from_code}, {to_city} → {to_code}")

    # Step 2: Scrape
    raw_text = scrape_trains(from_code, to_code, date)

    # Step 3: Parse
    all_trains = parse_trains_from_text(raw_text)
    print(f"Total trains scraped: {len(all_trains)}")

    # Step 4: Filter + Score
    available_trains = filter_and_score_trains(all_trains)
    print(f"Trains with available seats: {len(available_trains)}")

    if not available_trains:
        # Try next day automatically
        print("No trains today — checking tomorrow...")
        next_date = (datetime.strptime(date, "%d-%m-%Y") + timedelta(days=1)).strftime("%d-%m-%Y")
        raw_text = scrape_trains(from_code, to_code, next_date)
        all_trains = parse_trains_from_text(raw_text)
        available_trains = filter_and_score_trains(all_trains)

        if not available_trains:
            return {"error": "No available trains found for today or tomorrow"}

        date = next_date
        print(f"Found trains for {next_date}")

    # Step 5: AI recommendation
    print(f"Picking best train (preference: {preference})...")
    recommendation = ai_pick_best_train(available_trains, from_city, to_city, preference)
    recommendation["travel_date"] = date
    recommendation["total_trains_checked"] = len(all_trains)
    recommendation["trains_with_seats"] = len(available_trains)

    return recommendation


if __name__ == "__main__":
    # Test with city names instead of codes!
    result = search_and_recommend(
        from_city="Bangalore",
        to_city="Mysore",
        date="15-05-2026",
        preference="fast"   # try: "budget", "fast", "comfort", "balanced"
    )
    print("\n=== AI RECOMMENDATION ===\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))