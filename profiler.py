import json
from config import client

def build_taste_profile(user_input: str) -> dict:
    prompt = f"""
You are a reading taste analyst. Based on the user's input below, extract and 
structure their reading preferences into a JSON profile.

User Input: "{user_input}"

Return ONLY a valid JSON object with these fields:
- favorite_genres: list of strings
- disliked_genres: list of strings
- preferred_themes: list of strings
- pacing_preference: "fast" | "slow" | "mixed"
- liked_books: list of strings
- disliked_books: list of strings
- mood: "light" | "heavy" | "mixed"
- notes: string with any extra nuance

Return only the JSON. No explanation, no markdown.
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    raw = response.choices[0].message.content.strip()

    try:
        profile = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        profile = json.loads(raw[start:end])

    return profile