# ================================
# SMART TRAIN ENGINE V2
# Realtime ConfirmTkt + Geo Fallback
# ================================

from playwright.sync_api import sync_playwright
from groq import Groq
from dotenv import load_dotenv

from geopy.geocoders import Nominatim
from geopy.distance import geodesic

from datetime import datetime

import os
import re
import json

# =========================================
# ENV
# =========================================

load_dotenv()

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

geolocator = Nominatim(
    user_agent="TripSaathi"
)

# =========================================
# PREMIUM TRAINS
# =========================================

PREMIUM_TRAINS = {
    "12951",
    "12952",
    "12301",
    "12302",
    "12431",
    "12432"
}

# =========================================
# CONFIRMTKT STATION SEARCH
# =========================================

def search_station_confirmtkt(place):

    print(f"\nSearching station for: {place}")

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page()

        page.goto(
            "https://www.confirmtkt.com",
            timeout=60000
        )

        try:
            page.locator("text=Not now").click(timeout=3000)
        except:
            pass

        try:

            inputs = page.locator("input")

            first_input = inputs.nth(0)

            first_input.fill(place)

            page.wait_for_timeout(3000)

            suggestions = page.locator("li").all_inner_texts()

            for s in suggestions:

                match = re.search(
                    r'([A-Z]{2,5})',
                    s
                )

                if match:

                    code = match.group(1)

                    browser.close()

                    print(f"Found station: {code}")

                    return {
                        "found": True,
                        "station_code": code,
                        "station_name": s
                    }

        except Exception as e:

            print("Station search error:", e)

        browser.close()

    print("No station found directly")

    return {
        "found": False
    }

# =========================================
# GEO FALLBACK
# =========================================

def geo_fallback(place):

    print(f"\nUsing geo fallback for: {place}")

    location = geolocator.geocode(place + ", India")

    if not location:

        print("Geolocation failed")

        return None

    lat = location.latitude
    lon = location.longitude

    print(f"Coordinates: {lat}, {lon}")

    candidate_places = [
        "Aluva",
        "Ernakulam",
        "Kochi",
        "Mysore",
        "Bangalore",
        "Coimbatore",
        "Madurai",
        "Kozhikode",
        "Trivandrum"
    ]

    best = None
    best_distance = 999999

    for p in candidate_places:

        try:

            station = search_station_confirmtkt(p)

            if not station["found"]:
                continue

            loc2 = geolocator.geocode(p + ", India")

            if not loc2:
                continue

            dist = geodesic(
                (lat, lon),
                (loc2.latitude, loc2.longitude)
            ).km

            if dist < best_distance:

                best_distance = dist

                best = {
                    "resolved_from": place,
                    "nearest_station": station,
                    "distance_km": round(dist, 1)
                }

        except:
            continue

    return best

# =========================================
# PLACE RESOLVER
# =========================================

def resolve_place(place):

    station = search_station_confirmtkt(place)

    if station["found"]:

        return {
            "type": "direct_station",
            "station_code": station["station_code"],
            "station_name": station["station_name"]
        }

    fallback = geo_fallback(place)

    if fallback:

        return {
            "type": "geo_fallback",
            **fallback
        }

    return {
        "type": "not_found"
    }

# =========================================
# SCRAPER
# =========================================

def scrape_confirmtkt(from_code, to_code, journey_date):

    url = f"https://www.confirmtkt.com/rbooking/trains/from/{from_code}/to/{to_code}/{journey_date}"

    print(f"\nOpening: {url}")

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page()

        print("Opening page...")

        page.goto(
            url,
            timeout=60000,
            wait_until="domcontentloaded"
        )

        print("Page opened")

        try:
            page.locator("text=Not now").click(timeout=3000)
            print("Popup closed")
        except:
            print("No popup found")

        print("Waiting for train section...")

        try:
            page.wait_for_selector(
                "text=Trains found",
                timeout=10000
            )

            print("Train section loaded")

        except:
            print("Train section timeout")

        page.wait_for_timeout(3000)

        print("Extracting text...")

        body_text = page.inner_text("body")

        print("Closing browser...")

        browser.close()

    print("Scraping completed")

    return body_text

# =========================================
# PARSER
# =========================================

def parse_trains(raw_text):

    trains = []

    lines = [
        l.strip()
        for l in raw_text.split("\n")
        if l.strip()
    ]

    i = 0

    while i < len(lines):

        train_match = re.match(
            r'^(\d{5})(.+)$',
            lines[i]
        )

        if train_match:

            train = {
                "number": train_match.group(1),
                "name": train_match.group(2).strip(),
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

                    hrs = int(dur.group(1))
                    mins = int(dur.group(2))

                    train["duration"] = f"{hrs}h {mins}m"
                    train["duration_minutes"] = hrs * 60 + mins

                time_match = re.match(
                    r'^(\d{2}:\d{2})\s+\w+$',
                    line
                )

                if time_match:

                    if not train["departure"]:
                        train["departure"] = time_match.group(1)

                    elif not train["arrival"]:
                        train["arrival"] = time_match.group(1)

                class_match = re.match(
                    r'^(SL|3A|2A|1A|CC|2S|3E)$',
                    line
                )

                if class_match:

                    cls = class_match.group(1)

                    status = "UNKNOWN"

                    fare = None
                    seats = 0
                    wl = None
                    rac = None

                    for k in range(j + 1, min(j + 8, len(lines))):

                        txt = lines[k]

                        fare_match = re.match(
                            r'^₹(\d+)$',
                            txt
                        )

                        if fare_match:
                            fare = int(fare_match.group(1))

                        avl_match = re.search(
                            r'AVL\s*(\d+)',
                            txt
                        )

                        if avl_match:
                            status = "AVAILABLE"
                            seats = int(avl_match.group(1))

                        wl_match = re.search(
                            r'WL\s*(\d+)',
                            txt
                        )

                        if wl_match:
                            status = "WL"
                            wl = int(wl_match.group(1))

                        rac_match = re.search(
                            r'RAC\s*(\d+)',
                            txt
                        )

                        if rac_match:
                            status = "RAC"
                            rac = int(rac_match.group(1))

                    if fare:

                        train["classes"].append({
                            "class": cls,
                            "status": status,
                            "fare": fare,
                            "available_seats": seats,
                            "wl_number": wl,
                            "rac_number": rac
                        })

                j += 1

            if train["classes"]:
                trains.append(train)

            i = j

        else:
            i += 1

    return trains

# =========================================
# WL PREDICTION
# =========================================

def wl_prediction(wl, coach, days_before, train_number=""):

    pct = 10

    if coach == "SL":

        if wl <= 5:
            pct = 90
        elif wl <= 15:
            pct = 70
        elif wl <= 30:
            pct = 45
        else:
            pct = 20

    elif coach == "3A":

        if wl <= 5:
            pct = 80
        elif wl <= 10:
            pct = 60
        elif wl <= 20:
            pct = 35
        else:
            pct = 15

    if train_number in PREMIUM_TRAINS:
        pct = min(97, pct + 10)

    if days_before <= 2:
        pct -= 20

    pct = max(1, pct)

    if pct >= 80:
        label = "Very likely"
    elif pct >= 60:
        label = "Likely"
    elif pct >= 40:
        label = "Uncertain"
    elif pct >= 20:
        label = "Risky"
    else:
        label = "Very risky"

    return {
        "percent": pct,
        "label": label
    }

# =========================================
# SCORING
# =========================================

def score_train(train):

    score = 0

    mins = train.get("duration_minutes", 9999)

    if mins <= 300:
        score += 45
    elif mins <= 500:
        score += 35
    elif mins <= 800:
        score += 20
    else:
        score += 5

    available_classes = [
        c for c in train["classes"]
        if c["status"] == "AVAILABLE"
    ]

    wl_classes = [
        c for c in train["classes"]
        if c["status"] == "WL"
    ]

    if available_classes:

        score += 35

        max_seats = max(
            c["available_seats"]
            for c in available_classes
        )

        if max_seats >= 50:
            score += 15
        elif max_seats >= 20:
            score += 10
        else:
            score += 5

    if wl_classes:

        avg_wl = sum(
            c["wl_number"]
            for c in wl_classes
            if c["wl_number"]
        ) / len(wl_classes)

        if avg_wl >= 50:
            score -= 25
        elif avg_wl >= 20:
            score -= 10

    if (
        "vande" in train["name"].lower()
        or train["number"] in PREMIUM_TRAINS
    ):
        score += 20

    train["score"] = max(score, 1)

    return train

# =========================================
# AI RECOMMENDER
# =========================================

def ai_recommend(trains, preference):

    top = trains[:8]

    prompt = f"""
You are an Indian railway booking assistant.

Preference:
{preference}

Available trains:
{json.dumps(top, indent=2)}

Pick BEST train.

Return ONLY JSON:

{{
  "best_train_number": "",
  "reason": "",
  "recommended_class": "",
  "why": ""
}}
"""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):

        raw = raw.split("```")[1]

        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw.strip())

# =========================================
# MAIN SEARCH
# =========================================

def smart_search(
    from_city,
    to_city,
    journey_date,
    preference="balanced"
):

    from_resolved = resolve_place(from_city)
    to_resolved = resolve_place(to_city)

    print("\nFROM:")
    print(json.dumps(from_resolved, indent=2))

    print("\nTO:")
    print(json.dumps(to_resolved, indent=2))

    from_code = from_resolved["station_code"]

    if to_resolved["type"] == "direct_station":
        to_code = to_resolved["station_code"]

    else:
        to_code = to_resolved["nearest_station"]["station_code"]

    raw_text = scrape_confirmtkt(
        from_code,
        to_code,
        journey_date
    )

    trains = parse_trains(raw_text)

    print(f"\nTotal parsed trains: {len(trains)}")

    if not trains:

        return {
            "error": "No trains parsed"
        }

    scored = []

    today = datetime.today().date()

    for train in trains:

        train = score_train(train)

        for cls in train["classes"]:

            if cls["status"] == "WL":

                jdate = datetime.strptime(
                    journey_date,
                    "%d-%m-%Y"
                ).date()

                days_before = (
                    jdate - today
                ).days

                cls["wl_prediction"] = wl_prediction(
                    cls["wl_number"],
                    cls["class"],
                    days_before,
                    train["number"]
                )

        scored.append(train)

    scored.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    ai_pick = ai_recommend(
        scored,
        preference
    )

    return {
        "from_resolution": from_resolved,
        "to_resolution": to_resolved,
        "route": f"{from_code} → {to_code}",
        "journey_date": journey_date,
        "total_trains": len(scored),
        "best_ai_pick": ai_pick,
        "top_trains": scored[:5]
    }

# =========================================
# TEST
# =========================================

if __name__ == "__main__":

    result = smart_search(
        from_city="Bangalore",
        to_city="Munnar",
        journey_date="15-05-2026",
        preference="fast"
    )

    print("\n========== RESULT ==========\n")

    print(json.dumps(
        result,
        indent=2,
        ensure_ascii=False
    ))