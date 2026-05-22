import requests
import time
import random

OPENLIBRARY_SEARCH = "https://openlibrary.org/search.json"
OPENLIBRARY_COVERS = "https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"


def _fetch_cover_by_title(title: str, author: str) -> str | None:
    """
    Fallback cover fetcher — looks up a book by title+author
    and returns a cover URL if found.
    """
    try:
        params = {
            "title": title,
            "author": author,
            "fields": "cover_i",
            "limit": 1
        }
        response = requests.get(
            OPENLIBRARY_SEARCH,
            params=params,
            timeout=8
        )
        response.raise_for_status()
        docs = response.json().get("docs", [])
        if docs and docs[0].get("cover_i"):
            cover_id = docs[0]["cover_i"]
            return OPENLIBRARY_COVERS.format(cover_id=cover_id)
    except Exception as e:
        print(f"Cover fetch error for '{title}': {e}")
    return None


def search_books(query: str, limit: int = 10) -> list:
    """
    Search Open Library API — free, no key, no rate limits.
    """
    params = {
        "q": query,
        "limit": limit,
        "fields": "title,author_name,subject,first_sentence,cover_i",
        "language": "eng"
    }

    try:
        response = requests.get(
            OPENLIBRARY_SEARCH,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"Open Library API error: {e}")
        return []

    books = []
    for item in data.get("docs", []):
        title = item.get("title", "Unknown Title")
        authors = item.get("author_name", ["Unknown Author"])
        author = ", ".join(authors[:2])

        subjects = item.get("subject", ["General Fiction"])
        genre_str = ", ".join(subjects[:2])

        first_sentence = item.get("first_sentence", None)
        if isinstance(first_sentence, list):
            summary = first_sentence[0]
        elif isinstance(first_sentence, str):
            summary = first_sentence
        else:
            summary = f"A book about {genre_str.lower()}."

        if len(summary) > 300:
            summary = summary[:300] + "..."

        cover_id = item.get("cover_i")
        cover_url = (
            OPENLIBRARY_COVERS.format(cover_id=cover_id)
            if cover_id else None
        )

        books.append({
            "title": title,
            "author": author,
            "genre": genre_str,
            "summary": summary,
            "cover_url": cover_url
        })

    return books


def get_books_for_profile(taste_profile: dict, limit: int = 40) -> list:
    """
    Build a relevant book pool based on the user's taste profile.
    Uses Open Library with delays, falls back to hardcoded list if needed.
    Shuffles results for variety between generations.
    """
    queries = []

    genres = taste_profile.get("favorite_genres", [])
    themes = taste_profile.get("preferred_themes", [])
    liked = taste_profile.get("liked_books", [])
    authors = taste_profile.get("favorite_authors", [])

    # Build diverse queries so we get a wide pool
    if genres:
        for g in genres[:3]:
            queries.append(g)
    if themes:
        queries.append(" ".join(themes[:2]))
    if liked:
        for title in liked[:2]:
            queries.append(f"books like {title}")
    if authors:
        for author in authors[:2]:
            queries.append(f"author:{author}")

    if not queries:
        queries.append("popular fiction bestseller")

    all_books = []
    seen_titles = set()

    for i, query in enumerate(queries):
        if i > 0:
            time.sleep(0.8)
        results = search_books(query, limit=10)
        for book in results:
            if book["title"].lower() not in seen_titles:
                seen_titles.add(book["title"].lower())
                all_books.append(book)

    # Shuffle for variety between generations
    random.shuffle(all_books)

    # Full fallback
    if not all_books:
        return _get_fallback_books_with_covers()

    # Top up with fallback if not enough
    if len(all_books) < limit:
        fallback = _get_fallback_books_with_covers()
        for book in fallback:
            if book["title"].lower() not in seen_titles:
                seen_titles.add(book["title"].lower())
                all_books.append(book)
            if len(all_books) >= limit:
                break

    return all_books[:limit]


def _get_fallback_books_with_covers() -> list:
    """
    Hardcoded fallback books with covers fetched live from Open Library.
    cover_url is populated at runtime so fallback books always show covers.
    """
    books = [

        # ── Science Fiction ──────────────────────────────────────
        {"title": "Dune", "author": "Frank Herbert", "genre": "Science Fiction",
         "summary": "A sweeping epic about politics, religion, and ecology on a desert planet that controls the universe's most valuable resource."},
        {"title": "Project Hail Mary", "author": "Andy Weir", "genre": "Science Fiction",
         "summary": "An astronaut wakes up alone in space with no memory and must piece together his mission to save Earth."},
        {"title": "The Hitchhiker's Guide to the Galaxy", "author": "Douglas Adams", "genre": "Science Fiction / Comedy",
         "summary": "A comedic sci-fi adventure about the absurdity of life, the universe, and everything — including the number 42."},
        {"title": "Ender's Game", "author": "Orson Scott Card", "genre": "Science Fiction",
         "summary": "A child prodigy is trained at a military school in space to lead humanity's defense against an alien invasion."},
        {"title": "The Martian", "author": "Andy Weir", "genre": "Science Fiction",
         "summary": "An astronaut is stranded alone on Mars and must use science and dark humor to survive until rescue."},

        # ── Dystopian ────────────────────────────────────────────
        {"title": "1984", "author": "George Orwell", "genre": "Dystopian Fiction",
         "summary": "A chilling portrayal of a totalitarian society where Big Brother surveils every thought and action."},
        {"title": "Brave New World", "author": "Aldous Huxley", "genre": "Dystopian Fiction",
         "summary": "A future society built on pleasure and conformity raises questions about freedom, identity, and what it means to be human."},
        {"title": "The Handmaid's Tale", "author": "Margaret Atwood", "genre": "Dystopian Fiction",
         "summary": "In a theocratic future America, a woman navigates a world where women have lost all rights and autonomy."},

        # ── Fantasy ──────────────────────────────────────────────
        {"title": "The Name of the Wind", "author": "Patrick Rothfuss", "genre": "Fantasy",
         "summary": "A legendary wizard recounts his extraordinary life story from orphaned street kid to the most feared man alive."},
        {"title": "The Way of Kings", "author": "Brandon Sanderson", "genre": "Fantasy",
         "summary": "An epic fantasy set on a storm-ravaged world where ancient evils return and three lives converge on a collision course."},
        {"title": "The Hobbit", "author": "J.R.R. Tolkien", "genre": "Fantasy",
         "summary": "A reluctant hobbit is swept into an epic quest to reclaim a dwarven kingdom from a fearsome dragon."},
        {"title": "American Gods", "author": "Neil Gaiman", "genre": "Fantasy / Mythology",
         "summary": "An ex-convict is drawn into a brewing war between ancient gods brought to America by immigrants and the new gods of technology."},

        # ── Historical Fiction ───────────────────────────────────
        {"title": "All the Light We Cannot See", "author": "Anthony Doerr", "genre": "Historical Fiction",
         "summary": "A blind French girl and a German soldier's lives intertwine in occupied France during World War II."},
        {"title": "The Pillars of the Earth", "author": "Ken Follett", "genre": "Historical Fiction",
         "summary": "An epic tale of ambition, faith, and power set against the building of a cathedral in 12th century England."},
        {"title": "Wolf Hall", "author": "Hilary Mantel", "genre": "Historical Fiction",
         "summary": "The rise of Thomas Cromwell through the treacherous court of Henry VIII, told with stunning psychological depth."},

        # ── Non-Fiction / History ────────────────────────────────
        {"title": "Sapiens", "author": "Yuval Noah Harari", "genre": "Non-Fiction / History",
         "summary": "A sweeping history of humankind from the Stone Age to the modern era, asking big questions about who we are."},
        {"title": "The Guns of August", "author": "Barbara Tuchman", "genre": "Non-Fiction / History",
         "summary": "A gripping account of the opening weeks of World War I and the decisions that shaped the entire conflict."},
        {"title": "Educated", "author": "Tara Westover", "genre": "Memoir / Non-Fiction",
         "summary": "A woman's remarkable journey from a survivalist family in rural Idaho to earning a PhD at Cambridge University."},

        # ── Thriller / Mystery ───────────────────────────────────
        {"title": "The Girl with the Dragon Tattoo", "author": "Stieg Larsson", "genre": "Thriller / Mystery",
         "summary": "A journalist and a brilliant hacker investigate a decades-old disappearance tied to a powerful Swedish family's dark secrets."},
        {"title": "Gone Girl", "author": "Gillian Flynn", "genre": "Psychological Thriller",
         "summary": "When a woman vanishes on her wedding anniversary, her husband becomes the prime suspect in a twisting tale of deception."},
        {"title": "The Da Vinci Code", "author": "Dan Brown", "genre": "Thriller / Mystery",
         "summary": "A symbologist is drawn into a deadly conspiracy involving secret societies, hidden codes, and the history of Christianity."},

        # ── Literary Fiction ─────────────────────────────────────
        {"title": "The Alchemist", "author": "Paulo Coelho", "genre": "Literary Fiction / Philosophy",
         "summary": "A shepherd boy's journey across the desert becomes a meditation on destiny, dreams, and the language of the universe."},
        {"title": "The Kite Runner", "author": "Khaled Hosseini", "genre": "Literary Fiction",
         "summary": "A story of friendship, betrayal, and redemption set against the turbulent history of Afghanistan."},

        # ── Self-Help / Psychology ───────────────────────────────
        {"title": "Atomic Habits", "author": "James Clear", "genre": "Self-Help",
         "summary": "A practical guide to building good habits and breaking bad ones through small, incremental changes."},
        {"title": "Thinking, Fast and Slow", "author": "Daniel Kahneman", "genre": "Psychology / Non-Fiction",
         "summary": "A Nobel laureate explores the two systems of thinking that drive human decisions, judgments, and biases."},
        {"title": "Man's Search for Meaning", "author": "Viktor Frankl", "genre": "Psychology / Memoir",
         "summary": "A psychiatrist's account of surviving the Holocaust and the philosophy of finding meaning even in suffering."},

        # ── International Relations / Politics ───────────────────
        {"title": "The Prince", "author": "Niccolò Machiavelli", "genre": "Politics / Philosophy",
         "summary": "A ruthlessly pragmatic guide to acquiring and maintaining political power, written in Renaissance Italy."},
        {"title": "Prisoners of Geography", "author": "Tim Marshall", "genre": "International Relations / Non-Fiction",
         "summary": "How mountains, rivers, and seas have shaped world history and continue to drive geopolitical decisions today."},
        {"title": "The Clash of Civilizations", "author": "Samuel P. Huntington", "genre": "International Relations / Politics",
         "summary": "A landmark theory arguing that cultural and religious identities will be the primary source of global conflict after the Cold War."},
    ]

    # Fetch covers live for all fallback books
    print("Fetching covers for fallback books...")
    for i, book in enumerate(books):
        if i > 0:
            time.sleep(0.5)       # be polite to Open Library
        book["cover_url"] = _fetch_cover_by_title(book["title"], book["author"])

    return books