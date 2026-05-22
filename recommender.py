import json
import re
from config import client


def _clean_json(text: str) -> str:
    """Strip markdown fences if model wraps response in ```json blocks."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```$", "", text)
    return text.strip()


def get_recommendations(taste_profile: dict, book_pool: list) -> dict:

    books_formatted = "\n".join([
        f"- {b['title']} by {b['author']} [{b['genre']}]: {b['summary']}"
        for b in book_pool
    ])

    profile_str = json.dumps(taste_profile, indent=2)

    prompt = f"""
You are a book recommendation engine. Match books from the pool below to the
user's taste profile.

## User Taste Profile:
{profile_str}

## Available Books:
{books_formatted}

## Instructions:
1. Rank the top 5 books that best match this user's profile.
2. For each book provide:
   - title: string
   - author: string
   - reason: 2-sentence explanation of why it matches their taste
   - confidence: score from 1-10
3. Also include a "poor_matches" list: books that clearly clash with their
   preferences, each with a brief reason why.
4. Keep the tone conversational and enthusiastic like a knowledgeable friend.

Return ONLY a valid JSON object. No explanation, no markdown.

Format:
{{
  "recommendations": [
    {{
      "title": "",
      "author": "",
      "reason": "",
      "confidence": 0
    }}
  ],
  "poor_matches": [
    {{
      "title": "",
      "reason": ""
    }}
  ]
}}
"""

    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=1024
    )

    raw = response.choices[0].message.content.strip()
    cleaned = _clean_json(raw)

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        result = json.loads(cleaned[start:end])

    return result