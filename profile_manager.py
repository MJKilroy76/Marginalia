import json
import os
from datetime import datetime

USERS_DIR = "users"

# ── Default weights per phase ────────────────────────────────────
DEFAULT_WEIGHTS_NEW = {
    "genre_match":         0.35,
    "age_appropriateness": 0.25,
    "mood_match":          0.20,
    "reading_pace_fit":    0.20,
}

DEFAULT_WEIGHTS_RETURNING = {
    "genre_match":         0.25,
    "age_appropriateness": 0.15,
    "mood_match":          0.15,
    "reading_pace_fit":    0.15,
    "historical_ratings":  0.30,
}


def _ensure_users_dir():
    if not os.path.exists(USERS_DIR):
        os.makedirs(USERS_DIR)


def _profile_path(username: str) -> str:
    return os.path.join(USERS_DIR, f"{username}.json")


def profile_exists(username: str) -> bool:
    return os.path.exists(_profile_path(username))


def create_profile(username: str, password_hash: str) -> dict:
    _ensure_users_dir()
    profile = {
        "username": username,
        "password_hash": password_hash,
        "age": None,
        "taste_profile": {
            "favorite_genres": [],
            "preferred_themes": [],
            "liked_books": [],
            "disliked_genres": [],
            "favorite_authors": []
        },
        "reading_pace": None,
        "current_mood": None,
        "owned_books": [],
        "read_books": [],
        "reading_list": [],
        "currently_reading": None,
        "dnf_books": [],
        "ratings": {},
        "reading_goal": {
            "target": 0,
            "year": None
        },

        # ── Iteration 3 ──────────────────────────────────────────
        "criterion_weights": None,          # None = use defaults
        "recommendation_feedback": []       # list of feedback events
    }
    save_profile(username, profile)
    return profile


def save_profile(username: str, profile: dict):
    _ensure_users_dir()
    with open(_profile_path(username), "w") as f:
        json.dump(profile, f, indent=2)


def load_profile(username: str) -> dict | None:
    path = _profile_path(username)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def _migrate_profile(profile: dict) -> dict:
    """
    Ensure older profiles have all Iteration 3 fields.
    Called on every load so existing users don't break.
    """
    profile.setdefault("criterion_weights", None)
    profile.setdefault("recommendation_feedback", [])
    return profile


def load_profile(username: str) -> dict | None:
    path = _profile_path(username)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        profile = json.load(f)
    return _migrate_profile(profile)


def update_taste_profile(username: str, taste_profile: dict):
    profile = load_profile(username)
    if profile:
        profile["taste_profile"] = taste_profile
        save_profile(username, profile)


def update_user_info(username: str, age: int = None,
                     reading_pace: str = None, current_mood: str = None):
    profile = load_profile(username)
    if not profile:
        return
    if age is not None:
        profile["age"] = age
    if reading_pace is not None:
        profile["reading_pace"] = reading_pace
    if current_mood is not None:
        profile["current_mood"] = current_mood
    save_profile(username, profile)


def add_owned_books(username: str, books: list):
    profile = load_profile(username)
    if not profile:
        return
    existing_titles = {b["title"].lower() for b in profile["owned_books"]}
    for book in books:
        if book["title"].lower() not in existing_titles:
            profile["owned_books"].append(book)
            existing_titles.add(book["title"].lower())
    save_profile(username, profile)


def add_to_reading_list(username: str, book: dict):
    profile = load_profile(username)
    if not profile:
        return
    existing_titles = {b["title"].lower() for b in profile["reading_list"]}
    if book["title"].lower() not in existing_titles:
        profile["reading_list"].append(book)
        save_profile(username, profile)


def mark_as_read(username: str, book_title: str):
    profile = load_profile(username)
    if not profile:
        return
    book = next(
        (b for b in profile["reading_list"]
         if b["title"].lower() == book_title.lower()),
        None
    )
    if book:
        profile["reading_list"] = [
            b for b in profile["reading_list"]
            if b["title"].lower() != book_title.lower()
        ]
        if book_title.lower() not in [
            b["title"].lower() for b in profile["read_books"]
        ]:
            profile["read_books"].append(book)

    if (profile.get("currently_reading") and
            profile["currently_reading"]["title"].lower() == book_title.lower()):
        profile["currently_reading"] = None
    save_profile(username, profile)


def rate_book(username: str, book_title: str, rating: int):
    profile = load_profile(username)
    if not profile:
        return
    if "ratings" not in profile:
        profile["ratings"] = {}
    profile["ratings"][book_title] = max(1, min(5, rating))
    save_profile(username, profile)


def set_currently_reading(username: str, book: dict | None):
    profile = load_profile(username)
    if not profile:
        return
    profile["currently_reading"] = book
    save_profile(username, profile)


def mark_dnf(username: str, book_title: str):
    profile = load_profile(username)
    if not profile:
        return
    book = next(
        (b for b in profile["reading_list"]
         if b["title"].lower() == book_title.lower()),
        None
    )
    if book:
        profile["reading_list"] = [
            b for b in profile["reading_list"]
            if b["title"].lower() != book_title.lower()
        ]
        dnf_titles = {b["title"].lower() for b in profile.get("dnf_books", [])}
        if book_title.lower() not in dnf_titles:
            profile.setdefault("dnf_books", []).append(book)

    if (profile.get("currently_reading") and
            profile["currently_reading"]["title"].lower() == book_title.lower()):
        profile["currently_reading"] = None
    save_profile(username, profile)


def set_reading_goal(username: str, target: int, year: int):
    profile = load_profile(username)
    if not profile:
        return
    profile["reading_goal"] = {"target": target, "year": year}
    save_profile(username, profile)


def get_owned_titles(username: str) -> list:
    profile = load_profile(username)
    if not profile:
        return []
    return [b["title"] for b in profile["owned_books"]]


def get_taste_profile(username: str) -> dict:
    profile = load_profile(username)
    if not profile:
        return {}
    return profile.get("taste_profile", {})


# ── Iteration 3: Criterion Weights ───────────────────────────────

def save_criterion_weights(username: str, weights: dict):
    """Save user's custom criterion weights to their profile."""
    profile = load_profile(username)
    if not profile:
        return

    # Normalize so weights always sum to 1.0
    total = sum(weights.values())
    if total > 0:
        weights = {k: round(v / total, 4) for k, v in weights.items()}
    profile["criterion_weights"] = weights
    save_profile(username, profile)


def get_criterion_weights(username: str, has_history: bool) -> dict:
    """
    Return the user's saved weights, or defaults if none saved.
    """
    profile = load_profile(username)
    if not profile:
        return DEFAULT_WEIGHTS_RETURNING if has_history else DEFAULT_WEIGHTS_NEW
    saved = profile.get("criterion_weights")
    if saved:
        return saved
    return DEFAULT_WEIGHTS_RETURNING if has_history else DEFAULT_WEIGHTS_NEW


def reset_criterion_weights(username: str):
    """Reset weights back to defaults."""
    profile = load_profile(username)
    if not profile:
        return
    profile["criterion_weights"] = None
    save_profile(username, profile)


# ── Iteration 3: Recommendation Feedback ─────────────────────────

def log_recommendation_feedback(
    username: str,
    book_title: str,
    author: str,
    outcome: str,            # "saved" | "started" | "rated_high" | "rated_low" | "ignored"
    final_score: float,
    score_breakdown: dict
):
    """
    Log what happened to a recommended book.
    outcome values:
      - "saved"      → user added to reading list
      - "started"    → user set as currently reading
      - "rated_high" → user rated 4-5 stars
      - "rated_low"  → user rated 1-2 stars
      - "ignored"    → shown but never interacted with
    """
    profile = load_profile(username)
    if not profile:
        return
    profile.setdefault("recommendation_feedback", [])
    profile["recommendation_feedback"].append({
        "book_title": book_title,
        "author": author,
        "outcome": outcome,
        "final_score": final_score,
        "score_breakdown": score_breakdown,
        "timestamp": datetime.utcnow().isoformat()
    })
    save_profile(username, profile)


def get_recommendation_feedback(username: str) -> list:
    """Return all logged feedback events."""
    profile = load_profile(username)
    if not profile:
        return []
    return profile.get("recommendation_feedback", [])