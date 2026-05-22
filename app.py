import streamlit as st
import json
from auth import render_auth_page, render_sidebar
from profile_manager import (
    load_profile,
    update_taste_profile,
    update_user_info,
    get_taste_profile,
    get_owned_titles,
    add_to_reading_list,
    mark_as_read,
    rate_book,
    set_currently_reading,
    mark_dnf,
    set_reading_goal
)
from bookshelf_scanner import render_scanner_ui
from recommender import get_recommendations, SCORING_CRITERIA
from book_pool import get_books_for_profile

# ── Page Config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Marginalia",
    page_icon="📚",
    layout="centered"
)

# ── Session State Defaults ───────────────────────────────────────
for key, default in {
    "username": None,
    "page": "auth",
    "taste_profile": None,
    "recommendations": [],
    "messages": []
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Router ───────────────────────────────────────────────────────
def route():
    username = st.session_state.username
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
        if st.button("⬅️ Back to Dashboard"):
            st.session_state.page = "main"
            st.rerun()
    elif page == "recommendations":
        render_sidebar(username)
        render_recommendations_page(username)
    elif page == "library":
        render_sidebar(username)
        render_library_page(username)


# ── Scoring Help Dialog ──────────────────────────────────────────
def render_scoring_help():
    with st.expander("ℹ️ How are scores calculated?", expanded=False):
        st.markdown("### 📊 Scoring System")
        st.markdown(
            "Each book is scored using a **weighted multi-criteria model** "
            "on a scale of **0–10**. The system has two phases:"
        )

        st.markdown("#### 🆕 Phase 1: New Users (no rating history)")
        rows = []
        for key, meta in SCORING_CRITERIA["new_user"].items():
            rows.append({
                "Criterion": key.replace("_", " ").title(),
                "Weight": f"{int(meta['weight']*100)}%",
                "What it measures": meta["description"]
            })
        st.table(rows)

        st.markdown("#### ⭐ Phase 2: Returning Users (has ratings)")
        rows = []
        for key, meta in SCORING_CRITERIA["returning_user"].items():
            rows.append({
                "Criterion": key.replace("_", " ").title(),
                "Weight": f"{int(meta['weight']*100)}%",
                "What it measures": meta["description"]
            })
        st.table(rows)

        st.markdown(
            "_The system automatically detects which phase to use based on "
            "whether you have rated any books yet._"
        )


# ── Profile Setup ────────────────────────────────────────────────
def render_profile_setup(username: str):
    render_sidebar(username)

    profile = load_profile(username)
    existing_taste = profile.get("taste_profile", {})
    already_set_up = bool(existing_taste.get("favorite_genres"))

    st.markdown(f"## 👋 Welcome, {username.capitalize()}!")

    if already_set_up:
        st.markdown("Your taste profile is already set up. You can update it below or jump straight in.")
        if st.button("📚 Go to My Dashboard", use_container_width=True):
            st.session_state.page = "main"
            st.rerun()
        st.markdown("---")
        st.markdown("### 🔄 Update Your Taste Profile")
    else:
        st.markdown("Let's figure out what kinds of books you love so I can give you great recommendations.")

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

    st.markdown("---")
    st.markdown("### 🙋 A bit about you *(optional)*")

    age_val = st.number_input(
        "Your age",
        min_value=5, max_value=120,
        value=profile.get("age") or 18,
        step=1,
        help="Helps us filter out age-inappropriate content."
    )
    reading_pace = st.selectbox(
        "How fast do you read?",
        ["Not specified", "Slow (1-2 books/year)", "Moderate (3-10 books/year)", "Fast (10+ books/year)"],
        index=["Not specified", "Slow (1-2 books/year)", "Moderate (3-10 books/year)", "Fast (10+ books/year)"].index(
            profile.get("reading_pace") or "Not specified"
        )
    )

    if st.button("✅ Save & Continue", use_container_width=True):
        if not selected_genres:
            st.error("Please select at least one genre.")
        else:
            taste_profile = {
                "favorite_genres": selected_genres,
                "preferred_themes": selected_themes,
                "liked_books": [b.strip() for b in liked_books_input.split(",") if b.strip()],
                "disliked_genres": disliked_genres,
                "favorite_authors": [a.strip() for a in favorite_authors_input.split(",") if a.strip()]
            }
            update_taste_profile(username, taste_profile)
            update_user_info(
                username,
                age=age_val,
                reading_pace=None if reading_pace == "Not specified" else reading_pace
            )
            st.session_state.taste_profile = taste_profile
            st.success("Profile saved!")
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
    goal = profile.get("reading_goal", {})
    currently = profile.get("currently_reading")

    # ── Reading Goal Progress ────────────────────────────────────
    if goal.get("target") and goal.get("target") > 0:
        progress = len(read_books) / goal["target"]
        st.markdown(f"### 🎯 Reading Goal: {len(read_books)} / {goal['target']} books in {goal.get('year','this year')}")
        st.progress(min(progress, 1.0))
        st.markdown("---")

    # ── Currently Reading ────────────────────────────────────────
    if currently:
        st.markdown(f"📖 **Currently reading:** *{currently['title']}* by {currently['author']}")
        st.markdown("---")

    # ── Stats Row ────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📖 On Shelf", len(owned_books))
    col2.metric("🔖 Reading List", len(reading_list))
    col3.metric("✅ Read", len(read_books))
    col4.metric("⭐ Rated", len(profile.get("ratings", {})))

    st.markdown("---")

    # ── Navigation ───────────────────────────────────────────────
    st.markdown("### What would you like to do?")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if st.button("🤖 Get Recommendations", use_container_width=True):
            st.session_state.page = "recommendations"
            st.rerun()
    with col_b:
        if st.button("📸 Scan My Bookshelf", use_container_width=True):
            st.session_state.page = "scanner"
            st.rerun()
    with col_c:
        if st.button("🗂️ My Library", use_container_width=True):
            st.session_state.page = "library"
            st.rerun()

    # ── Reading Goal Setter ──────────────────────────────────────
    st.markdown("---")
    with st.expander("🎯 Set / Update Reading Goal"):
        import datetime
        current_year = datetime.datetime.now().year
        goal_target = st.number_input(
            "How many books do you want to read this year?",
            min_value=1, max_value=365,
            value=goal.get("target") or 12,
            step=1
        )
        if st.button("💾 Save Goal", use_container_width=True):
            set_reading_goal(username, goal_target, current_year)
            st.success(f"Goal set: {goal_target} books in {current_year}!")
            st.rerun()

    # ── Quick Chat ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 💬 Ask Marginalia Anything")
    st.caption("Ask about books, authors, genres, or get a quick suggestion.")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("What are you in the mood for?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        taste = get_taste_profile(username)
        owned = get_owned_titles(username)

        from config import client
        system_msg = {
            "role": "system",
            "content": f"""You are Marginalia, a warm and knowledgeable AI reading companion.
You help readers discover books they'll love.

User's taste profile:
- Favorite genres: {taste.get('favorite_genres', [])}
- Preferred themes: {taste.get('preferred_themes', [])}
- Books they've loved: {taste.get('liked_books', [])}
- Genres to avoid: {taste.get('disliked_genres', [])}
- Favorite authors: {taste.get('favorite_authors', [])}
- Age: {profile.get('age', 'unspecified')}

Books they already own: {owned[:20] if owned else 'None scanned yet'}

Guidelines:
- Be conversational, warm, and enthusiastic about books
- Give specific recommendations with brief reasons why
- If they own a book already, acknowledge it
- Never recommend books in their disliked genres
- Keep responses concise but helpful"""
        }

        history = [system_msg] + [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
        ]

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = client.chat.completions.create(
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    messages=history,
                    temperature=0.7,
                    max_tokens=512
                )
                reply = response.choices[0].message.content
                st.markdown(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})


# ── Recommendations Page ─────────────────────────────────────────
def render_recommendations_page(username: str):
    st.markdown("## 🤖 Your Recommendations")

    render_scoring_help()

    profile = load_profile(username)
    taste = profile.get("taste_profile", {})
    owned_books = profile.get("owned_books", [])
    ratings = profile.get("ratings", {})
    dnf_books = profile.get("dnf_books", [])
    age = profile.get("age")

    # ── Build exclusion set ──────────────────────────────────────

    # Exclude: owned, read, saved, DNF, and liked books from taste profile
    read_titles = {b["title"].lower() for b in profile.get("read_books", [])}
    dnf_titles = {b["title"].lower() for b in dnf_books}
    saved_titles = {b["title"].lower() for b in profile.get("reading_list", [])}
    owned_titles = {b["title"].lower() for b in owned_books}
    liked_titles = {
        t.lower() for t in taste.get("liked_books", [])
    }

    excluded_titles = read_titles | dnf_titles | saved_titles | liked_titles

    # ── Optional filters ─────────────────────────────────────────
    with st.expander("🎛️ Filters *(optional)*"):
        mood = st.selectbox(
            "What's your reading mood right now?",
            ["Not specified", "Light & fun", "Moderate", "Dark & challenging"]
        )
        pace_override = st.selectbox(
            "Reading pace for this recommendation?",
            ["Use my profile setting", "Slow", "Moderate", "Fast"]
        )
        surprise = st.checkbox("🎲 Surprise me! (include a wildcard pick)")

    current_mood = None if mood == "Not specified" else mood
    reading_pace = (
        profile.get("reading_pace")
        if pace_override == "Use my profile setting"
        else pace_override
    )

    source = st.radio(
        "Recommend from:",
        ["🌐 General pool", "📚 My bookshelf"],
        horizontal=True
    )

    if st.button("🔄 Generate Recommendations", use_container_width=True):
        with st.spinner("Finding your next great read..."):

            if source == "📚 My bookshelf":
                if not owned_books:
                    st.warning("Your shelf is empty! Scan your bookshelf first.")
                    return

                # From shelf: exclude read, DNF, and saved — but keep owned
                book_pool = [
                    b for b in owned_books
                    if b["title"].lower() not in excluded_titles
                ]
                if not book_pool:
                    st.info(
                        "You've already read, saved, or DNF'd everything on "
                        "your shelf! Scan more books to get new recommendations."
                    )
                    return
            else:

                # General pool: exclude owned, read, DNF, and saved
                all_excluded = excluded_titles | owned_titles
                book_pool = get_books_for_profile(taste, limit=40)
                book_pool = [
                    b for b in book_pool
                    if b["title"].lower() not in all_excluded
                ]
                if not book_pool:
                    st.info("No new books to recommend right now. Try updating your taste profile!")
                    return

            result = get_recommendations(
                taste_profile=taste,
                book_pool=book_pool,
                age=age,
                reading_pace=reading_pace,
                current_mood=current_mood,
                ratings=ratings,
                dnf_books=dnf_books,
                surprise=surprise
            )
            recs = result.get("recommendations", [])

            pool_lookup = {b["title"].lower(): b for b in book_pool}
            for rec in recs:
                match = pool_lookup.get(rec["title"].lower(), {})
                rec["genre"] = match.get("genre", "Unknown")
                rec["summary"] = rec.get("reason", match.get("summary", ""))

                # Use pool cover first, fetch live only if missing, fail silently
                cover = match.get("cover_url")
                if not cover:
                    try:
                        cover = _fetch_cover_by_title(rec["title"], rec["author"])
                    except Exception:
                        cover = None
                rec["cover_url"] = cover

            # Always replace — never append — so every generation is fresh
            st.session_state.recommendations = recs

    # ── Display Recommendations ──────────────────────────────────
    if st.session_state.recommendations:
        st.markdown("---")
        for i, book in enumerate(st.session_state.recommendations, 1):
            with st.container():
                col1, col2 = st.columns([1, 4])

                with col1:
                    if book.get("cover_url"):
                        st.image(book["cover_url"], width=80)
                    else:
                        st.markdown("📖")

                with col2:
                    title_line = f"### {i}. {book['title']}"
                    if book.get("surprise"):
                        title_line += " 🎲"
                    st.markdown(title_line)
                    st.markdown(f"*by {book['author']}*")
                    st.markdown(f"**Genre:** {book['genre']}")

                    if book.get("is_series"):
                        series_note = f"📚 Part of *{book.get('series_name', 'a series')}*"
                        if book.get("series_position"):
                            series_note += f" (Book {book['series_position']})"
                        st.info(series_note)

                    st.markdown(book["summary"])

                    score = book.get("final_score")
                    if score is not None:
                        st.markdown(f"**Match Score: {score}/10**")
                        st.progress(score / 10)
                        with st.expander("📊 Score breakdown"):
                            breakdown = book.get("score_breakdown", {})
                            has_history = bool(ratings)
                            criteria = (
                                SCORING_CRITERIA["returning_user"]
                                if has_history
                                else SCORING_CRITERIA["new_user"]
                            )
                            for key, meta in criteria.items():
                                raw = breakdown.get(key, 0)
                                st.markdown(
                                    f"**{key.replace('_',' ').title()}** "
                                    f"({int(meta['weight']*100)}%): {raw}/10"
                                )

                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    with btn_col1:
                        if st.button("🔖 Save", key=f"save_{i}"):
                            add_to_reading_list(username, book)
                            st.success(f"Saved *{book['title']}*!")
                    with btn_col2:
                        if st.button("📖 Reading now", key=f"reading_{i}"):
                            set_currently_reading(username, book)
                            st.success("Set as currently reading!")
                    with btn_col3:
                        rating = st.selectbox(
                            "Rate",
                            ["—", "⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"],
                            key=f"rate_{i}"
                        )
                        if rating != "—":
                            rate_book(username, book["title"], len(rating.replace(" ", "")))
                            st.success("Rating saved!")

                st.markdown("---")

    if st.button("⬅️ Back to Dashboard", use_container_width=True):
        st.session_state.page = "main"
        st.rerun()


# ── Library Page ─────────────────────────────────────────────────
def render_library_page(username: str):
    st.markdown("## 🗂️ My Library")

    profile = load_profile(username)

    tab1, tab2, tab3, tab4 = st.tabs([
        "📚 My Shelf",
        "🔖 Reading List",
        "✅ Read",
        "🚫 Did Not Finish"
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

            # Export button
            export_data = json.dumps(owned, indent=2)
            st.download_button(
                "⬇️ Export shelf as JSON",
                data=export_data,
                file_name="my_shelf.json",
                mime="application/json"
            )
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
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    st.markdown(f"**{book['title']}** — *{book['author']}*")
                with col2:
                    if st.button("✅ Read", key=f"read_{book['title']}"):
                        mark_as_read(username, book["title"])
                        st.rerun()
                with col3:
                    if st.button("📖 Now", key=f"now_{book['title']}"):
                        set_currently_reading(username, book)
                        st.success("Set!")
                        st.rerun()
                with col4:
                    if st.button("🚫 DNF", key=f"dnf_{book['title']}"):
                        mark_dnf(username, book["title"])
                        st.rerun()

    # ── Read Books ───────────────────────────────────────────────
    with tab3:
        read = profile.get("read_books", [])
        ratings = profile.get("ratings", {})
        if not read:
            st.info("No books marked as read yet.")
        else:
            st.markdown(f"**{len(read)} books read:**")
            for book in read:
                col1, col2 = st.columns([4, 1])
                with col1:
                    existing_rating = ratings.get(book["title"])
                    stars = "⭐" * existing_rating if existing_rating else "Not rated"
                    st.markdown(f"- **{book['title']}** — *{book['author']}* {stars}")
                with col2:
                    rating = st.selectbox(
                        "Rate",
                        ["—", "⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"],
                        key=f"rateread_{book['title']}"
                    )
                    if rating != "—":
                        rate_book(username, book["title"], len(rating.replace(" ", "")))
                        st.rerun()

    # ── DNF Books ────────────────────────────────────────────────
    with tab4:
        dnf = profile.get("dnf_books", [])
        if not dnf:
            st.info("No DNF books yet — hope that stays empty! 😄")
        else:
            st.markdown(f"**{len(dnf)} books you didn't finish:**")
            for book in dnf:
                st.markdown(f"- **{book['title']}** — *{book['author']}*")

    st.markdown("---")
    if st.button("⬅️ Back to Dashboard", use_container_width=True):
        st.session_state.page = "main"
        st.rerun()


# ── Run ──────────────────────────────────────────────────────────
route()