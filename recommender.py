import json
import re
import random
from config import client


def _clean_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```$", "", text)
    return text.strip()


# ── Default Scoring Criteria ─────────────────────────────────────
SCORING_CRITERIA = {
    "new_user": {
        "genre_match":         {"weight": 0.35, "description": "How well the book's genre matches your preferred genres"},
        "age_appropriateness": {"weight": 0.25, "description": "Whether the book's maturity level fits your age"},
        "mood_match":          {"weight": 0.20, "description": "How well the book's tone fits your current reading mood"},
        "reading_pace_fit":    {"weight": 0.20, "description": "Whether the book's length suits your reading pace"},
    },
    "returning_user": {
        "genre_match":         {"weight": 0.25, "description": "How well the book's genre matches your preferred genres"},
        "age_appropriateness": {"weight": 0.15, "description": "Whether the book's maturity level fits your age"},
        "mood_match":          {"weight": 0.15, "description": "How well the book's tone fits your current reading mood"},
        "reading_pace_fit":    {"weight": 0.15, "description": "Whether the book's length suits your reading pace"},
        "historical_ratings":  {"weight": 0.30, "description": "Based on ratings you've given similar books"},
    }
}


def _compute_score(
    taste_profile: dict,
    age: int | None,
    reading_pace: str | None,
    current_mood: str | None,
    ratings: dict,
    ai_scores: dict,
    custom_weights: dict | None = None   # ← Iteration 3
) -> float:
    has_history = bool(ratings)
    criteria = SCORING_CRITERIA["returning_user"] if has_history else SCORING_CRITERIA["new_user"]

    # Use custom weights if provided, otherwise fall back to defaults
    weights = custom_weights if custom_weights else {
        k: v["weight"] for k, v in criteria.items()
    }

    total = 0.0
    for key in criteria:
        raw = ai_scores.get(key, 5.0)
        normalized = max(0.0, min(10.0, float(raw))) / 10.0
        total += normalized * weights.get(key, 0.0)

    return round(total * 10, 2)


def get_recommendations(
    taste_profile: dict,
    book_pool: list,
    age: int | None = None,
    reading_pace: str | None = None,
    current_mood: str | None = None,
    ratings: dict | None = None,
    dnf_books: list | None = None,
    surprise: bool = False,
    custom_weights: dict | None = None    # ← Iteration 3
) -> dict:

    ratings = ratings or {}
    dnf_books = dnf_books or []
    has_history = bool(ratings)

    # Resolve weights for prompt display
    if custom_weights:
        w = custom_weights
    else:
        criteria = SCORING_CRITERIA["returning_user"] if has_history else SCORING_CRITERIA["new_user"]
        w = {k: v["weight"] for k, v in criteria.items()}

    def pct(key):
        return int(round(w.get(key, 0) * 100))

    pool = book_pool.copy()
    random.shuffle(pool)

    books_formatted = "\n".join([
        f"- {b['title']} by {b['author']} [{b.get('genre', 'Unknown')}]: {b.get('summary', '')}"
        for b in pool
    ])

    profile_str = json.dumps(taste_profile, indent=2)

    if ratings:
        ratings_lines = []
        for title, score in ratings.items():
            stars = "⭐" * score
            ratings_lines.append(f"  - {title}: {stars} ({score}/5)")
        ratings_str = "\n".join(ratings_lines)
    else:
        ratings_str = "None yet"

    dnf_str = (
        "\n".join([f"  - {b['title']} by {b['author']}" for b in dnf_books])
        if dnf_books else "None"
    )

    surprise_instruction = (
        "Include at least one 'wildcard' pick intentionally outside the user's "
        "usual preferences but that might pleasantly surprise them. "
        "Mark it with 'surprise': true."
        if surprise else ""
    )

    phase_note = (
        "The user has rated books before — use those ratings heavily "
        f"({pct('historical_ratings')}% weight) "
        "to infer what they like and dislike. Books rated 4-5 stars indicate strong "
        "preferences; books rated 1-2 stars indicate things to avoid."
        if has_history else
        "This is a new user with no rating history — do NOT use historical ratings."
    )

    prompt = f"""
You are a rigorous book recommendation engine using a weighted scoring system.

## Scoring Criteria (score each 0-10):
- genre_match ({pct('genre_match')}%): Genre overlap with user preferences
- age_appropriateness ({pct('age_appropriateness')}%): Maturity fit for age {age if age else "unspecified"}
- mood_match ({pct('mood_match')}%): Tone fit for mood "{current_mood if current_mood else "unspecified"}"
- reading_pace_fit ({pct('reading_pace_fit')}%): Length fit for "{reading_pace if reading_pace else "unspecified"}" reading pace
{"- historical_ratings (" + str(pct('historical_ratings')) + "%): Inferred from the user's past star ratings" if has_history else ""}

{phase_note}

## User Taste Profile:
{profile_str}

## User's Past Ratings:
{ratings_str}

## DNF Books (strong negative signals — avoid similar):
{dnf_str}

## User Age: {age if age else "Not specified"}

## Reading Pace: {reading_pace if reading_pace else "Not specified"}

## Current Mood: {current_mood if current_mood else "Not specified"}

## Available Books:
{books_formatted}

## Instructions:
1. Score every book on each criterion (0-10).
2. Rank and return the top 5.
3. For each book include a 2-sentence reason and flag if it is part of a series.
4. Use the user's ratings to infer taste nuance — not just genre but tone, complexity, pacing.
5. Treat DNF books as strong negative signals — avoid similar books.
6. Include a "poor_matches" list for clear mismatches.
7. {surprise_instruction}
8. Keep tone warm and enthusiastic.

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
        temperature=0.7,
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

    for rec in result.get("recommendations", []):
        rec["final_score"] = _compute_score(
            taste_profile=taste_profile,
            age=age,
            reading_pace=reading_pace,
            current_mood=current_mood,
            ratings=ratings,
            ai_scores=rec.get("score_breakdown", {}),
            custom_weights=custom_weights       # ← pass through
        )

    return result