import json
import re
import google.generativeai as genai
from PIL import Image
import io
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
vision_client = genai.GenerativeModel("gemini-2.5-flash")


def _clean_json_response(text: str) -> str:
    """Strip markdown code fences if the model wraps JSON in ``` blocks."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```$", "", text)
    return text.strip()


def scan_bookshelf(image_bytes: bytes) -> list[dict]:
    """
    Send a bookshelf photo to Gemini Vision and extract
    book titles and authors from the spines.

    Returns a list of dicts: [{"title": ..., "author": ...}, ...]
    """

    # Convert bytes to PIL Image for Gemini
    image = Image.open(io.BytesIO(image_bytes))

    prompt = """
    You are a book spine reader. Carefully examine this bookshelf photo.

    Your job:
    1. Read every book spine you can see clearly
    2. Extract the title and author from each spine
    3. If you can only read the title but not the author, still include it with author as "Unknown"
    4. If a spine is too blurry or angled to read, skip it
    5. Do NOT guess or make up titles — only include what you can actually read

    Respond ONLY with a valid JSON array, no explanation, no markdown.
    Format:
    [
      {"title": "Book Title Here", "author": "Author Name Here"},
      {"title": "Another Book", "author": "Unknown"}
    ]

    If you cannot read any spines at all, return an empty array: []
    """

    try:
        response = vision_client.generate_content(
            [prompt, image],
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 1024
            }
        )

        raw = response.text
        cleaned = _clean_json_response(raw)
        books = json.loads(cleaned)

        # Validate structure — filter out malformed entries
        valid_books = []
        for book in books:
            if isinstance(book, dict) and "title" in book:
                valid_books.append({
                    "title": book.get("title", "Unknown Title").strip(),
                    "author": book.get("author", "Unknown").strip(),
                    "genre": "Unknown",
                    "summary": "Scanned from your bookshelf.",
                    "cover_url": None,
                    "source": "shelf_scan"
                })

        return valid_books

    except json.JSONDecodeError:
        print(f"JSON parse error. Raw response was:\n{raw}")
        return []
    except Exception as e:
        print(f"Bookshelf scan error: {e}")
        return []


def render_scanner_ui(username: str):
    """
    Streamlit UI for the bookshelf scanner.
    Handles upload, scanning, and saving to profile.
    """
    import streamlit as st
    from profile_manager import add_owned_books, get_owned_titles

    st.markdown("## 📸 Scan Your Bookshelf")
    st.markdown(
        "Upload a photo of your bookshelf and I'll read the spines "
        "to build your personal library."
    )

    with st.expander("📌 Tips for best results"):
        st.markdown("""
        - 📷 Take the photo straight-on, not at an angle
        - 💡 Make sure the lighting is even — avoid harsh shadows
        - 🔍 Get close enough that titles are legible
        - 📚 One shelf at a time works better than a wide shot
        - 🖼️ JPG or PNG both work fine
        """)

    uploaded_file = st.file_uploader(
        "Upload your bookshelf photo",
        type=["jpg", "jpeg", "png", "webp"],
        key="shelf_upload"
    )

    if uploaded_file:
        st.image(uploaded_file, caption="Your bookshelf", use_container_width=True)

        if st.button("🔍 Scan Spines", use_container_width=True):
            with st.spinner("Reading your book spines..."):
                image_bytes = uploaded_file.read()
                found_books = scan_bookshelf(image_bytes)

            if not found_books:
                st.warning(
                    "I couldn't read any spines clearly. "
                    "Try a closer or better-lit photo."
                )
            else:
                st.success(f"Found **{len(found_books)}** books on your shelf!")

                st.markdown("### 📖 Books Detected")
                for i, book in enumerate(found_books, 1):
                    st.markdown(f"**{i}.** {book['title']} — *{book['author']}*")

                add_owned_books(username, found_books)
                st.success("✅ Added to your library!")

                all_owned = get_owned_titles(username)
                st.info(
                    f"📚 Your library now has **{len(all_owned)}** "
                    f"book(s) total."
                )

                if st.button("📖 Get Recommendations From My Shelf"):
                    st.session_state.page = "recommendations"
                    st.rerun()