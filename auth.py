import hashlib
import streamlit as st
from profile_manager import (
    profile_exists,
    create_profile,
    load_profile
)


def _hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def _verify_password(password: str, password_hash: str) -> bool:
    """Check if a password matches the stored hash."""
    return _hash_password(password) == password_hash


def register_user(username: str, password: str) -> tuple[bool, str]:
    """
    Register a new user.
    Returns (success: bool, message: str)
    """
    username = username.strip().lower()

    if not username:
        return False, "Username cannot be empty."

    if len(username) < 3:
        return False, "Username must be at least 3 characters."

    if not password:
        return False, "Password cannot be empty."

    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    if profile_exists(username):
        return False, "That username is already taken. Please choose another."

    password_hash = _hash_password(password)
    create_profile(username, password_hash)

    return True, "Account created successfully!"


def login_user(username: str, password: str) -> tuple[bool, str]:
    """
    Authenticate a user.
    Returns (success: bool, message: str)
    """
    username = username.strip().lower()

    if not profile_exists(username):
        return False, "No account found with that username."

    profile = load_profile(username)
    if not profile:
        return False, "Error loading profile. Please try again."

    if not _verify_password(password, profile["password_hash"]):
        return False, "Incorrect password. Please try again."

    return True, "Login successful!"


def render_auth_page():
    """
    Render the login / registration UI.
    Sets st.session_state.username on success.
    """
    st.markdown("""
        <h1 style='text-align: center; font-size: 2.5rem;'>📚 Marginalia</h1>
        <p style='text-align: center; color: gray;'>
            Your personal AI reading companion
        </p>
        <br>
    """, unsafe_allow_html=True)

    # Tab switcher
    tab_login, tab_register = st.tabs(["Log In", "Create Account"])

    # ── Login Tab ────────────────────────────────────────────────
    with tab_login:
        st.subheader("Welcome back!")

        login_username = st.text_input(
            "Username",
            key="login_username",
            placeholder="Enter your username"
        )
        login_password = st.text_input(
            "Password",
            type="password",
            key="login_password",
            placeholder="Enter your password"
        )

        if st.button("Log In", use_container_width=True, key="login_btn"):
            if not login_username or not login_password:
                st.error("Please fill in both fields.")
            else:
                success, message = login_user(login_username, login_password)
                if success:
                    st.session_state.username = login_username.strip().lower()
                    st.session_state.page = "profile_setup"
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    # ── Register Tab ─────────────────────────────────────────────
    with tab_register:
        st.subheader("Create your account")

        reg_username = st.text_input(
            "Choose a username",
            key="reg_username",
            placeholder="At least 3 characters"
        )
        reg_password = st.text_input(
            "Choose a password",
            type="password",
            key="reg_password",
            placeholder="At least 6 characters"
        )
        reg_password_confirm = st.text_input(
            "Confirm password",
            type="password",
            key="reg_password_confirm",
            placeholder="Repeat your password"
        )

        if st.button("Create Account", use_container_width=True, key="reg_btn"):
            if not reg_username or not reg_password or not reg_password_confirm:
                st.error("Please fill in all fields.")
            elif reg_password != reg_password_confirm:
                st.error("Passwords do not match.")
            else:
                success, message = register_user(reg_username, reg_password)
                if success:
                    st.session_state.username = reg_username.strip().lower()
                    st.session_state.page = "profile_setup"
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


def render_sidebar(username: str):
    """Render a full sidebar with navigation, profile summary, and logout."""
    from profile_manager import load_profile

    profile = load_profile(username)
    taste = profile.get("taste_profile", {})
    owned = profile.get("owned_books", [])
    reading_list = profile.get("reading_list", [])
    read_books = profile.get("read_books", [])

    with st.sidebar:

        # ── Identity ─────────────────────────────────────────
        st.markdown(f"### 👤 {username.capitalize()}")
        genres = taste.get("favorite_genres", [])
        if genres:
            st.caption(", ".join(genres[:3]))
        else:
            st.caption("No taste profile yet")

        st.markdown("---")

        # ── Navigation ───────────────────────────────────────
        st.markdown("### 🧭 Navigate")

        if st.button("🏠 Dashboard", use_container_width=True):
            st.session_state.page = "main"
            st.rerun()

        if st.button("🤖 Recommendations", use_container_width=True):
            st.session_state.page = "recommendations"
            st.rerun()

        if st.button("📸 Scan Bookshelf", use_container_width=True):
            st.session_state.page = "scanner"
            st.rerun()

        if st.button("🗂️ My Library", use_container_width=True):
            st.session_state.page = "library"
            st.rerun()

        st.markdown("---")

        # ── Quick Stats ──────────────────────────────────────
        st.markdown("### 📊 My Stats")
        col1, col2, col3 = st.columns(3)
        col1.metric("🗃️ Shelf", len(owned))
        col2.metric("🔖 Saved", len(reading_list))
        col3.metric("✅ Read", len(read_books))

        st.markdown("---")

        # ── Profile ──────────────────────────────────────────
        st.markdown("### ⚙️ Profile")

        if taste.get("liked_books"):
            st.caption(f"❤️ Loved: {', '.join(taste['liked_books'][:2])}")

        if taste.get("favorite_authors"):
            st.caption(f"✍️ Authors: {', '.join(taste['favorite_authors'][:2])}")

        if st.button("✏️ Edit Taste Profile", use_container_width=True):
            st.session_state.page = "profile_setup"
            st.rerun()

        st.markdown("---")

        # ── Logout ───────────────────────────────────────────
        if st.button("🚪 Log Out", use_container_width=True):
            username_copy = username
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success(f"See you soon, {username_copy}! 👋")
            st.rerun()