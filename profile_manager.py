import json
import os

USERS_DIR = "users"


def _ensure_users_dir():
    """Create the users directory if it doesn't exist."""
    if not os.path.exists(USERS_DIR):
        os.makedirs(USERS_DIR)


def _profile_path(username: str) -> str:
    """Return the file path for a user's profile."""
    return os.path.join(USERS_DIR, f"{username}.json")


def profile_exists(username: str) -> bool:
    """Check if a profile exists for the given username."""
    return os.path.exists(_profile_path(username))


def create_profile(username: str, password_hash: str) -> dict:
    """
    Create a new user profile and save it to disk.
    Returns the new profile dict.
    """
    _ensure_users_dir()

    profile = {
        "username": username,
        "password_hash": password_hash,
        "taste_profile": {
            "favorite_genres": [],
            "preferred_themes": [],
            "liked_books": [],
            "disliked_genres": [],
            "favorite_authors": []
        },
        "owned_books": [],       # books scanned from their shelf
        "read_books": [],        # books they've marked as read
        "reading_list": []       # books saved for later
    }

    save_profile(username, profile)
    return profile


def save_profile(username: str, profile: dict):
    """Save a user's profile to disk."""
    _ensure_users_dir()
    with open(_profile_path(username), "w") as f:
        json.dump(profile, f, indent=2)


def load_profile(username: str) -> dict | None:
    """
    Load a user's profile from disk.
    Returns None if the profile doesn't exist.
    """
    path = _profile_path(username)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def update_taste_profile(username: str, taste_profile: dict):
    """Update just the taste profile section of a user's profile."""
    profile = load_profile(username)
    if profile:
        profile["taste_profile"] = taste_profile
        save_profile(username, profile)


def add_owned_books(username: str, books: list):
    """
    Add books scanned from the user's shelf.
    Avoids duplicates by title.
    """
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
    """Save a recommended book to the user's reading list."""
    profile = load_profile(username)
    if not profile:
        return

    existing_titles = {b["title"].lower() for b in profile["reading_list"]}
    if book["title"].lower() not in existing_titles:
        profile["reading_list"].append(book)
        save_profile(username, profile)


def mark_as_read(username: str, book_title: str):
    """Move a book from reading list to read books."""
    profile = load_profile(username)
    if not profile:
        return

    # Find the book in reading list
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

    save_profile(username, profile)


def get_owned_titles(username: str) -> list:
    """Return a flat list of owned book titles for quick lookup."""
    profile = load_profile(username)
    if not profile:
        return []
    return [b["title"] for b in profile["owned_books"]]


def get_taste_profile(username: str) -> dict:
    """Return just the taste profile for a user."""
    profile = load_profile(username)
    if not profile:
        return {}
    return profile.get("taste_profile", {})