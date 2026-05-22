import json
import re
import base64
import pandas as pd
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)


def _encode_image(image_bytes: bytes) -> str:
    """Convert image bytes to base64 string for the API."""
    return base64.b64encode(image_bytes).decode("utf-8")


def _clean_json_response(text: str) -> str:
    """Strip markdown code fences if the model wraps JSON in ``` blocks."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```$", "", text)
    return text.strip()


def scan_bookshelf(image_bytes: bytes) -> list[dict]:
    """
    Send a bookshelf photo to Groq Vision and extract
    book titles and authors from the spines.

    Returns a list of dicts: [{
        "title": ...,
        "author": ...,
        "author_confidence": "high" | "low"
    }, ...]
    """

    base64_image = _encode_image(image_bytes)

    prompt = """
    You are an expert book spine reader with sharp attention to detail.
    Carefully examine this bookshelf photo.

    Your job:
    1. Read every book spine you can see clearly.
    2. For EACH spine, look carefully for TWO pieces of text:
       - TITLE: usually the largest text on the spine
       - AUTHOR NAME: usually smaller text, often at the bottom or top of
         the spine. Both are almost always present — look harder before
         marking author as "Unknown".
    3. For each book, also set "author_confidence":
       - "high" if you can clearly read the author name
       - "low" if you are guessing or the author text is unclear
    4. If a spine is too blurry or angled to read at all, skip it entirely.
    5. Do NOT make up titles or authors — only include what you can actually read.

    Respond ONLY with a valid JSON array, no explanation, no markdown.
    Format:
    [
      {
        "title": "Book Title Here",
        "author": "Author Name Here",
        "author_confidence": "high"
      },
      {
        "title": "Blurry Title",
        "author": "Unknown",
        "author_confidence": "low"
      }
    ]

    If you cannot read any spines at all, return an empty array: []
    """

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            max_tokens=1024,
            temperature=0.1
        )

        raw = response.choices[0].message.content
        cleaned = _clean_json_response(raw)
        books = json.loads(cleaned)

        valid_books = []
        for book in books:
            if isinstance(book, dict) and "title" in book:
                valid_books.append({
                    "title": book.get("title", "Unknown Title").strip(),
                    "author": book.get("author", "Unknown").strip(),
                    "author_confidence": book.get("author_confidence", "low"),
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
    Handles upload, scanning, review/correction, and saving to profile.
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
            st.session_state["scanned_books"] = found_books

    # ── Review & Correct ─────────────────────────────────────────
    if st.session_state.get("scanned_books"):
        found_books = st.session_state["scanned_books"]

        if not found_books:
            st.warning(
                "I couldn't read any spines clearly. "
                "Try a closer or better-lit photo."
            )
        else:
            st.success(f"Found **{len(found_books)}** books on your shelf!")

            # Count low confidence authors and warn user
            low_confidence = [
                b for b in found_books
                if b.get("author_confidence") == "low"
            ]
            if low_confidence:
                st.warning(
                    f"⚠️ **{len(low_confidence)} author(s)** could not be read "
                    f"clearly and are marked below. Please correct them before saving."
                )

            st.markdown("### ✏️ Review & correct before saving")
            st.caption(
                "You can edit any title or author directly in the table. "
                "Authors marked ⚠️ had low confidence — double-check those."
            )

            # Build dataframe with a visual flag for low confidence
            df = pd.DataFrame([
                {
                    "title": b["title"],
                    "author": b["author"],
                    "author_confidence": (
                        "⚠️ low" if b.get("author_confidence") == "low"
                        else "✅ high"
                    )
                }
                for b in found_books
            ])

            edited_df = st.data_editor(
                df,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "title": st.column_config.TextColumn("Title", width="large"),
                    "author": st.column_config.TextColumn("Author", width="medium"),
                    "author_confidence": st.column_config.TextColumn(
                        "Confidence", width="small", disabled=True
                    )
                }
            )

            if st.button("✅ Save to my library", use_container_width=True):

                # Merge edited data back with original metadata
                saved_books = []
                for i, row in edited_df.iterrows():
                    original = found_books[i] if i < len(found_books) else {}
                    saved_books.append({
                        "title": row["title"].strip(),
                        "author": row["author"].strip(),
                        "genre": original.get("genre", "Unknown"),
                        "summary": original.get("summary", "Scanned from your bookshelf."),
                        "cover_url": original.get("cover_url", None),
                        "source": "shelf_scan"
                    })

                add_owned_books(username, saved_books)
                st.success("✅ Added to your library!")
                st.session_state["scanned_books"] = []

                all_owned = get_owned_titles(username)
                st.info(
                    f"📚 Your library now has **{len(all_owned)}** book(s) total."
                )

                if st.button("🤖 Get Recommendations From My Shelf"):
                    st.session_state.page = "recommendations"
                    st.rerun()