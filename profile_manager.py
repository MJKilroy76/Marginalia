import json
import os

USERS_DIR = "users"


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
        "reading_pace": None,          # "slow" | "moderate" | "fast"
        "current_mood": None,          # "light" | "moderate" | "challenging"
        "owned_books": [],
        "read_books": [],
        "reading_list": [],
        "currently_reading": None,     # single book dict or None
        "dnf_books": [],               # did not finish
        "ratings": {},                 # {"Book Title": 1-5}
        "reading_goal": {
            "target": 0,
            "year": None
        }
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


def update_taste_profile(username: str, taste_profile: dict):
    profile = load_profile(username)
    if profile:
        profile["taste_profile"] = taste_profile
        save_profile(username, profile)


def update_user_info(username: str, age: int = None, reading_pace: str = None, current_mood: str = None):
    """Update optional user info fields."""
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

    # Also clear currently_reading if it matches
    if (profile.get("currently_reading") and
            profile["currently_reading"]["title"].lower() == book_title.lower()):
        profile["currently_reading"] = None
    save_profile(username, profile)


def rate_book(username: str, book_title: str, rating: int):
    """Rate a book 1-5 stars."""
    profile = load_profile(username)
    if not profile:
        return
    if "ratings" not in profile:
        profile["ratings"] = {}
    profile["ratings"][book_title] = max(1, min(5, rating))
    save_profile(username, profile)


def set_currently_reading(username: str, book: dict | None):
    """Set or clear the currently reading book."""
    profile = load_profile(username)
    if not profile:
        return
    profile["currently_reading"] = book
    save_profile(username, profile)


def mark_dnf(username: str, book_title: str):
    """Mark a book as Did Not Finish."""
    profile = load_profile(username)
    if not profile:
        return

    # Remove from reading list if present
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

    # Also clear currently reading
    if (profile.get("currently_reading") and
            profile["currently_reading"]["title"].lower() == book_title.lower()):
        profile["currently_reading"] = None
    save_profile(username, profile)


def set_reading_goal(username: str, target: int, year: int):
    """Set annual reading goal."""
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