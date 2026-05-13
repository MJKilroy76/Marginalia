import streamlit as st
from auth import render_auth_page, render_sidebar
from profile_manager import (
    load_profile,
    update_taste_profile,
    get_taste_profile,
    get_owned_titles,
    add_to_reading_list
)
from bookshelf_scanner import render_scanner_ui
from profiler import build_taste_profile
from recommender import get_recommendations
from book_pool import get_books_for_profile

# ── Page Config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Marginalia",
    page_icon="📚",
    layout="centered"
)

# ── Session State Defaults ───────────────────────────────────────
if "username" not in st.session_state:
    st.session_state.username = None

if "page" not in st.session_state:
    st.session_state.page = "auth"

if "taste_profile" not in st.session_state:
    st.session_state.taste_profile = None

if "recommendations" not in st.session_state:
    st.session_state.recommendations = []

if "messages" not in st.session_state:
    st.session_state.messages = []


# ── Router ───────────────────────────────────────────────────────
def route():
    username = st.session_state.username

    # Not logged in → show auth page
    if not username:
        st.session_state.page = "auth"

    page = st.session_state.page

    if page == "auth":
        render_auth_page()

    elif page == "profile_setup":
        render_profile_setup(username)

    elif page == "main":
        render_main_app(username)

    elif page == "scanner":
        render_sidebar(username)
        render_scanner_ui(username)
        st.markdown("---")
        if st.button("⬅️ Back to recommendations"):
            st.session_state.page = "main"
            st.rerun()

    elif page == "recommendations":
        render_sidebar(username)
        render_recommendations_page(username)

    elif page == "library":
        render_sidebar(username)
        render_library_page(username)


# ── Profile Setup ────────────────────────────────────────────────
def render_profile_setup(username: str):
    render_sidebar(username)

    profile = load_profile(username)
    existing_taste = profile.get("taste_profile", {})
    already_set_up = bool(existing_taste.get("favorite_genres"))

    st.markdown(f"## 👋 Welcome, {username.capitalize()}!")

    if already_set_up:
        st.markdown(
            "Your taste profile is already set up. "
            "You can update it below or jump straight in."
        )
        if st.button("📚 Go to My Dashboard", use_container_width=True):
            st.session_state.page = "main"
            st.rerun()
        st.markdown("---")
        st.markdown("### 🔄 Update Your Taste Profile")
    else:
        st.markdown(
            "Let's figure out what kinds of books you love "
            "so I can give you great recommendations."
        )

    # ── Taste Profile Form ───────────────────────────────────────
    genre_options = [
        "Science Fiction", "Fantasy", "Historical Fiction",
        "Literary Fiction", "Thriller", "Mystery", "Horror",
        "Romance", "Non-Fiction", "Biography", "Self-Help",
        "Psychology", "Philosophy", "Politics", "Classics"
    ]
    theme_options = [
        "Adventure", "Coming of Age", "Identity", "War",
        "Dystopia", "Love", "Survival", "Politics", "Magic",
        "Technology", "Family", "Friendship", "Redemption",
        "Power", "Nature", "Justice"
    ]

    selected_genres = st.multiselect(
        "What genres do you love?",
        genre_options,
        default=existing_taste.get("favorite_genres", [])
    )
    selected_themes = st.multiselect(
        "What themes resonate with you?",
        theme_options,
        default=existing_taste.get("preferred_themes", [])
    )
    liked_books_input = st.text_input(
        "Books you've loved (comma separated)",
        value=", ".join(existing_taste.get("liked_books", [])),
        placeholder="e.g. Dune, The Alchemist, 1984"
    )
    disliked_genres = st.multiselect(
        "Any genres you'd rather avoid?",
        genre_options,
        default=existing_taste.get("disliked_genres", [])
    )
    favorite_authors_input = st.text_input(
        "Favorite authors (comma separated)",
        value=", ".join(existing_taste.get("favorite_authors", [])),
        placeholder="e.g. Frank Herbert, Ursula K. Le Guin"
    )

    if st.button("✅ Save & Continue", use_container_width=True):
        if not selected_genres:
            st.error("Please select at least one genre.")
        else:
            taste_profile = {
                "favorite_genres": selected_genres,
                "preferred_themes": selected_themes,
                "liked_books": [
                    b.strip()
                    for b in liked_books_input.split(",")
                    if b.strip()
                ],
                "disliked_genres": disliked_genres,
                "favorite_authors": [
                    a.strip()
                    for a in favorite_authors_input.split(",")
                    if a.strip()
                ]
            }
            update_taste_profile(username, taste_profile)
            st.session_state.taste_profile = taste_profile
            st.success("Taste profile saved!")
            st.session_state.page = "main"
            st.rerun()


# ── Main Dashboard ───────────────────────────────────────────────
def render_main_app(username: str):
    render_sidebar(username)

    st.markdown(f"## 📚 Hey, {username.capitalize()}!")

    profile = load_profile(username)
    owned_books = profile.get("owned_books", [])
    reading_list = profile.get("reading_list", [])
    read_books = profile.get("read_books", [])

    # ── Stats Row ────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    col1.metric("📖 On Your Shelf", len(owned_books))
    col2.metric("🔖 Reading List", len(reading_list))
    col3.metric("✅ Read", len(read_books))

    st.markdown("---")

    # ── Navigation ───────────────────────────────────────────────
    st.markdown("### What would you like to do?")

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if st.button(
            "🤖 Get Recommendations",
            use_container_width=True
        ):
            st.session_state.page = "recommendations"
            st.rerun()

    with col_b:
        if st.button(
            "📸 Scan My Bookshelf",
            use_container_width=True
        ):
            st.session_state.page = "scanner"
            st.rerun()

    with col_c:
        if st.button(
            "🗂️ My Library",
            use_container_width=True
        ):
            st.session_state.page = "library"
            st.rerun()

    # ── Quick Chat ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 💬 Ask Marginalia Anything")
    st.caption("Ask about books, authors, genres, or get a quick suggestion.")

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("What are you in the mood for?"):
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        with st.chat_message("user"):
            st.markdown(prompt)

        taste = get_taste_profile(username)
        owned = get_owned_titles(username)

        system_prompt = f"""
        You are Marginalia, a warm and knowledgeable AI reading companion.
        You help readers discover books they'll love.

        User's taste profile:
        - Favorite genres: {taste.get('favorite_genres', [])}
        - Preferred themes: {taste.get('preferred_themes', [])}
        - Books they've loved: {taste.get('liked_books', [])}
        - Genres to avoid: {taste.get('disliked_genres', [])}
        - Favorite authors: {taste.get('favorite_authors', [])}

        Books they already own: {owned[:20] if owned else 'None scanned yet'}

        Guidelines:
        - Be conversational, warm, and enthusiastic about books
        - Give specific recommendations with brief reasons why
        - If they own a book already, acknowledge it
        - Never recommend books in their disliked genres
        - Keep responses concise but helpful
        """

        from config import client
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Build conversation history as a single string for Gemini
                history = "\n".join([
                    f"{'User' if m['role'] == 'user' else 'Marginalia'}: {m['content']}"
                    for m in st.session_state.messages
                ])

                full_prompt = f"{system_prompt}\n\n## Conversation so far:\n{history}"

                response = client.generate_content(
                    full_prompt,
                    generation_config={
                        "temperature": 0.7,
                        "max_output_tokens": 512
                    }
                )
                reply = response.text
                st.markdown(reply)

        st.session_state.messages.append({
            "role": "assistant",
            "content": reply
        })


# ── Recommendations Page ─────────────────────────────────────────
def render_recommendations_page(username: str):
    st.markdown("## 🤖 Your Recommendations")

    profile = load_profile(username)
    taste = profile.get("taste_profile", {})
    owned_books = profile.get("owned_books", [])
    owned_titles = {b["title"].lower() for b in owned_books}

    # Source toggle
    source = st.radio(
        "Recommend from:",
        ["🌐 General pool", "📚 My bookshelf"],
        horizontal=True
    )

    if st.button("🔄 Generate Recommendations", use_container_width=True):
        with st.spinner("Finding your next great read..."):

            if source == "📚 My bookshelf":
                if not owned_books:
                    st.warning(
                        "Your shelf is empty! "
                        "Scan your bookshelf first so I know what you own."
                    )
                    if st.button("📸 Scan My Bookshelf"):
                        st.session_state.page = "scanner"
                        st.rerun()
                    return

                # Recommend FROM owned books based on taste
                book_pool = owned_books
                result = get_recommendations(taste, book_pool)
                recs = result.get("recommendations", [])

                # Merge back the full book data (cover_url, genre, summary) from the pool
                pool_lookup = {b["title"].lower(): b for b in book_pool}
                for rec in recs:
                    match = pool_lookup.get(rec["title"].lower(), {})
                    rec["genre"] = match.get("genre", "Unknown")
                    rec["summary"] = rec.get("reason", match.get("summary", ""))
                    rec["cover_url"] = match.get("cover_url", None)

                st.session_state.recommendations = recs
            else:

                # General pool — filter out owned books
                book_pool = get_books_for_profile(taste, limit=20)
                book_pool = [
                    b for b in book_pool
                    if b["title"].lower() not in owned_titles
                ]
                result = get_recommendations(taste, book_pool)
                recs = result.get("recommendations", [])

                # Merge back the full book data (cover_url, genre, summary) from the pool
                pool_lookup = {b["title"].lower(): b for b in book_pool}
                for rec in recs:
                    match = pool_lookup.get(rec["title"].lower(), {})
                    rec["genre"] = match.get("genre", "Unknown")
                    rec["summary"] = rec.get("reason", match.get("summary", ""))
                    rec["cover_url"] = match.get("cover_url", None)

                st.session_state.recommendations = recs

    # Display recommendations
    if st.session_state.recommendations:
        st.markdown("---")
        for i, book in enumerate(st.session_state.recommendations, 1):
            with st.container():
                col1, col2 = st.columns([1, 4])

                with col1:
                    if book.get("cover_url"):
                        st.image(
                            book["cover_url"],
                            width=80
                        )
                    else:
                        st.markdown("📖")

                with col2:
                    st.markdown(f"### {i}. {book['title']}")
                    st.markdown(f"*by {book['author']}*")
                    st.markdown(f"**Genre:** {book['genre']}")
                    st.markdown(book['summary'])

                    if st.button(
                        "🔖 Save to Reading List",
                        key=f"save_{i}"
                    ):
                        add_to_reading_list(username, book)
                        st.success(f"Added *{book['title']}* to your reading list!")

                st.markdown("---")

    if st.button("⬅️ Back to Dashboard", use_container_width=True):
        st.session_state.page = "main"
        st.rerun()


# ── Library Page ─────────────────────────────────────────────────
def render_library_page(username: str):
    st.markdown("## 🗂️ My Library")

    profile = load_profile(username)

    tab1, tab2, tab3 = st.tabs([
        "📚 My Shelf",
        "🔖 Reading List",
        "✅ Read"
    ])

    # ── Owned Books ──────────────────────────────────────────────
    with tab1:
        owned = profile.get("owned_books", [])
        if not owned:
            st.info("No books scanned yet. Use the bookshelf scanner to add books!")
            if st.button("📸 Scan My Bookshelf"):
                st.session_state.page = "scanner"
                st.rerun()
        else:
            st.markdown(f"**{len(owned)} books on your shelf:**")
            for book in owned:
                st.markdown(f"- **{book['title']}** — *{book['author']}*")

    # ── Reading List ─────────────────────────────────────────────
    with tab2:
        reading_list = profile.get("reading_list", [])
        if not reading_list:
            st.info("Nothing saved yet. Get recommendations and save ones you like!")
        else:
            st.markdown(f"**{len(reading_list)} books saved:**")
            for book in reading_list:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"- **{book['title']}** — *{book['author']}*")
                with col2:
                    if st.button("✅ Mark Read", key=f"read_{book['title']}"):
                        from profile_manager import mark_as_read
                        mark_as_read(username, book["title"])
                        st.rerun()

    # ── Read Books ───────────────────────────────────────────────
    with tab3:
        read = profile.get("read_books", [])
        if not read:
            st.info("No books marked as read yet.")
        else:
            st.markdown(f"**{len(read)} books read:**")
            for book in read:
                st.markdown(f"- **{book['title']}** — *{book['author']}*")

    st.markdown("---")
    if st.button("⬅️ Back to Dashboard", use_container_width=True):
        st.session_state.page = "main"
        st.rerun()


# ── Run ──────────────────────────────────────────────────────────
route()