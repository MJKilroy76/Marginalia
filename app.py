import streamlit as st
import json
from profiler import build_taste_profile
from recommender import get_recommendations
from book_pool import get_books_for_profile

# ── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Marginalia",
    page_icon="📚",
    layout="wide"
)

# ── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title {
        font-size: 2.8rem;
        font-weight: 700;
        color: #2C3E50;
        margin-bottom: 0;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #7F8C8D;
        margin-top: 0;
    }
    .book-card {
        background: #f9f9f9;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 4px solid #3498DB;
    }
    .poor-match-card {
        background: #fff5f5;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 8px;
        border-left: 4px solid #E74C3C;
    }
    .confidence-badge {
        background: #3498DB;
        color: white;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .profile-box {
        background: #EBF5FB;
        border-radius: 10px;
        padding: 16px;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Session State Init ────────────────────────────────────────
if "taste_profile" not in st.session_state:
    st.session_state.taste_profile = None
if "recommendations" not in st.session_state:
    st.session_state.recommendations = None
if "book_pool" not in st.session_state:
    st.session_state.book_pool = None
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = {}

# ── Header ────────────────────────────────────────────────────
st.markdown('<p class="main-title">📚 Marginalia</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">Your AI-powered personal book recommender</p>',
    unsafe_allow_html=True
)
st.divider()

# ── Step 1: User Input ────────────────────────────────────────
st.subheader("🗣️ Tell me about your reading taste")
st.caption(
    "Mention books you loved, genres you hate, "
    "themes you enjoy — anything helps."
)

user_input = st.text_area(
    label="Your reading preferences",
    placeholder=(
        "e.g. I loved Dune and 1984. I hate romance novels. "
        "I enjoy fast-paced sci-fi with political themes and complex worlds."
    ),
    height=120,
    label_visibility="collapsed"
)

col1, col2 = st.columns([1, 4])
with col1:
    run_button = st.button(
        "🔍 Find My Books",
        type="primary",
        use_container_width=True
    )

# ── Step 2: Run Pipeline ──────────────────────────────────────
if run_button:
    if not user_input.strip():
        st.warning("Please tell me a bit about your reading taste first!")
    else:
        try:
            st.session_state.feedback_given = {}

            st.info("🧠 Building your taste profile...")
            st.session_state.taste_profile = build_taste_profile(user_input)
            st.success("✅ Taste profile ready!")

            st.info("📚 Searching for matching books...")
            st.session_state.book_pool = get_books_for_profile(
                st.session_state.taste_profile
            )
            st.success("✅ Books found!")

            st.info("🤖 Generating recommendations...")
            st.session_state.recommendations = get_recommendations(
                st.session_state.taste_profile,
                st.session_state.book_pool
            )
            st.success("✅ Done! Scroll down to see your recommendations.")

            st.rerun()

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                st.error(
                    "⚠️ API quota exceeded. You've hit the free tier limit. "
                    "Please wait a few hours for it to reset, or use a new API key."
                )
            else:
                st.error(f"Something went wrong: {error_msg}")

# ── Step 3: Display Results ───────────────────────────────────
if st.session_state.recommendations:
    st.divider()

    rec_col, profile_col = st.columns([2, 1])

    with rec_col:
        st.subheader("📖 Your Recommendations")

        recs = st.session_state.recommendations.get("recommendations", [])

        for i, book in enumerate(recs):
            cover_url = next(
                (
                    b.get("cover_url")
                    for b in (st.session_state.book_pool or [])
                    if b["title"].lower() == book["title"].lower()
                ),
                None
            )

            with st.container():
                img_col, text_col = st.columns([1, 4])

                with img_col:
                    if cover_url:
                        st.image(cover_url, width=80)
                    else:
                        st.markdown("📗")

                with text_col:
                    st.markdown(
                        f'<div class="book-card">'
                        f'<strong>#{i+1} — {book["title"]}</strong> '
                        f'<em>by {book["author"]}</em><br>'
                        f'<span class="confidence-badge">'
                        f'⭐ {book["confidence"]}/10</span><br><br>'
                        f'{book["reason"]}'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                    fb_key = f"feedback_{i}"
                    if fb_key not in st.session_state.feedback_given:
                        fb1, fb2, fb3, _ = st.columns([1, 1, 1, 3])
                        with fb1:
                            if st.button("👍 Yes", key=f"yes_{i}"):
                                st.session_state.feedback_given[fb_key] = "yes"
                                st.rerun()
                        with fb2:
                            if st.button("🤔 Maybe", key=f"maybe_{i}"):
                                st.session_state.feedback_given[fb_key] = "maybe"
                                st.rerun()
                        with fb3:
                            if st.button("👎 No", key=f"no_{i}"):
                                st.session_state.feedback_given[fb_key] = "no"
                                st.rerun()
                    else:
                        feedback = st.session_state.feedback_given[fb_key]
                        emoji = {
                            "yes": "👍 Noted!",
                            "maybe": "🤔 Maybe!",
                            "no": "👎 Got it!"
                        }
                        st.caption(emoji.get(feedback, ""))

        poor = st.session_state.recommendations.get("poor_matches", [])
        if poor:
            with st.expander("❌ Poor Matches (based on your taste)"):
                for book in poor:
                    st.markdown(
                        f'<div class="poor-match-card">'
                        f'<strong>{book["title"]}</strong><br>'
                        f'<small>{book["reason"]}</small>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

    with profile_col:
        st.subheader("🧠 Your Taste Profile")
        profile = st.session_state.taste_profile

        st.markdown(
            f'<div class="profile-box">'
            f'<b>Favorite Genres:</b> '
            f'{", ".join(profile.get("favorite_genres", []) or ["None detected"])}'
            f'<br><br>'
            f'<b>Disliked Genres:</b> '
            f'{", ".join(profile.get("disliked_genres", []) or ["None detected"])}'
            f'<br><br>'
            f'<b>Preferred Themes:</b> '
            f'{", ".join(profile.get("preferred_themes", []) or ["None detected"])}'
            f'<br><br>'
            f'<b>Pacing:</b> '
            f'{profile.get("pacing_preference", "mixed").capitalize()}<br><br>'
            f'<b>Mood:</b> {profile.get("mood", "mixed").capitalize()}<br><br>'
            f'<b>Liked Books:</b> '
            f'{", ".join(profile.get("liked_books", []) or ["None mentioned"])}'
            f'<br><br>'
            f'<b>Notes:</b> {profile.get("notes", "")}'
            f'</div>',
            unsafe_allow_html=True
        )