from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()
client = Groq(api_key=os.getenv(os.getenv("GROQ_API_KEY")))

user_input = "Plan a 3-day trip to Goa for 2 people on a budget of ₹15,000"

prompt = f"""
You are a helpful Indian travel planner.
A user wants to plan a trip. Here is their request:

"{user_input}"

Give a day-by-day itinerary with:
- Places to visit each day
- Food suggestions (local and budget-friendly)
- Estimated cost per day
- Travel tips

Keep it practical and specific.
"""

print("Sending request to AI...\n")
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": prompt}]
)
print(response.choices[0].message.content)