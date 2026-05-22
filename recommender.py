import json
import re
from config import client


def _clean_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```$", "", text)
    return text.strip()


# ── Scoring Criteria (exported for help button) ──────────────────
SCORING_CRITERIA = {
    "new_user": {
        "genre_match":          {"weight": 0.35, "description": "How well the book's genre matches your preferred genres"},
        "age_appropriateness":  {"weight": 0.25, "description": "Whether the book's maturity level fits your age"},
        "mood_match":           {"weight": 0.20, "description": "How well the book's tone fits your current reading mood"},
        "reading_pace_fit":     {"weight": 0.20, "description": "Whether the book's length suits your reading pace"},
    },
    "returning_user": {
        "genre_match":          {"weight": 0.25, "description": "How well the book's genre matches your preferred genres"},
        "age_appropriateness":  {"weight": 0.15, "description": "Whether the book's maturity level fits your age"},
        "mood_match":           {"weight": 0.15, "description": "How well the book's tone fits your current reading mood"},
        "reading_pace_fit":     {"weight": 0.15, "description": "Whether the book's length suits your reading pace"},
        "historical_ratings":   {"weight": 0.30, "description": "Based on ratings you've given similar books"},
    }
}


def _compute_score(
    book: dict,
    taste_profile: dict,
    age: int | None,
    reading_pace: str | None,
    current_mood: str | None,
    ratings: dict,
    ai_scores: dict
) -> float:
    """
    Compute a weighted score for a book.
    ai_scores: dict with keys matching criteria, values 0-10 from the LLM.
    """
    has_history = bool(ratings)
    criteria = SCORING_CRITERIA["returning_user"] if has_history else SCORING_CRITERIA["new_user"]

    total = 0.0
    for key, meta in criteria.items():
        raw = ai_scores.get(key, 5.0)          # default 5 if LLM missed it
        normalized = max(0.0, min(10.0, float(raw))) / 10.0
        total += normalized * meta["weight"]

    return round(total * 10, 2)                # return as 0-10 scale


def get_recommendations(
    taste_profile: dict,
    book_pool: list,
    age: int | None = None,
    reading_pace: str | None = None,
    current_mood: str | None = None,
    ratings: dict | None = None,
    surprise: bool = False
) -> dict:

    ratings = ratings or {}
    has_history = bool(ratings)

    books_formatted = "\n".join([
        f"- {b['title']} by {b['author']} [{b.get('genre','Unknown')}]: {b.get('summary','')}"
        for b in book_pool
    ])

    profile_str = json.dumps(taste_profile, indent=2)
    ratings_str = json.dumps(ratings, indent=2) if ratings else "None yet"

    surprise_instruction = (
        "Include at least one 'wildcard' pick that is intentionally outside "
        "the user's usual preferences but might pleasantly surprise them. "
        "Mark it with 'surprise': true in its JSON object."
        if surprise else ""
    )

    phase_note = (
        "The user has rated books before — factor in historical ratings (30% weight)."
        if has_history else
        "This is a new user with no rating history — do NOT use historical ratings."
    )

    prompt = f"""
You are a rigorous book recommendation engine using a weighted scoring system.

## Scoring Criteria (score each 0-10):
- genre_match ({"25" if has_history else "35"}%): Genre overlap with user preferences
- age_appropriateness ({"15" if has_history else "25"}%): Maturity level fit for age {age if age else "unspecified"}
- mood_match ({"15" if has_history else "20"}%): Tone fit for mood "{current_mood if current_mood else "unspecified"}"
- reading_pace_fit ({"15" if has_history else "20"}%): Length fit for "{reading_pace if reading_pace else "unspecified"}" reading pace
{"- historical_ratings (30%): Similarity to books the user rated highly" if has_history else ""}

{phase_note}

## User Taste Profile:
{profile_str}

## User's Past Ratings:
{ratings_str}

## User Age: {age if age else "Not specified"}

## Reading Pace: {reading_pace if reading_pace else "Not specified"}

## Current Mood: {current_mood if current_mood else "Not specified"}

## Available Books:
{books_formatted}

## Instructions:
1. Score every book on each criterion (0-10).
2. Rank and return the top 5.
3. For each book include a 2-sentence reason and flag if it is part of a series.
4. Include a "poor_matches" list for clear mismatches.
5. {surprise_instruction}
6. Keep tone warm and enthusiastic.

Return ONLY a valid JSON object. No explanation, no markdown.

Format:
{{
  "recommendations": [
    {{
      "title": "",
      "author": "",
      "reason": "",
      "is_series": false,
      "series_name": "",
      "series_position": 1,
      "surprise": false,
      "score_breakdown": {{
        "genre_match": 0,
        "age_appropriateness": 0,
        "mood_match": 0,
        "reading_pace_fit": 0,
        "historical_ratings": 0
      }}
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
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=2048
    )

    raw = response.choices[0].message.content.strip()
    cleaned = _clean_json(raw)

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        result = json.loads(cleaned[start:end])

    # Compute final weighted scores locally
    for rec in result.get("recommendations", []):
        rec["final_score"] = _compute_score(
            book={},
            taste_profile=taste_profile,
            age=age,
            reading_pace=reading_pace,
            current_mood=current_mood,
            ratings=ratings,
            ai_scores=rec.get("score_breakdown", {})
        )

    return result