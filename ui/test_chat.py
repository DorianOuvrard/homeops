"""Quick Streamlit chat to test OpenAI integration before wiring the Telegram bot."""

import base64
import os

import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="homeops AI test", layout="centered")
st.title("homeops AI test")

api_key = os.environ.get("OPENAI_API_KEY", "")
if not api_key:
    st.error("OPENAI_API_KEY not set. Run with: OPENAI_API_KEY=sk-... streamlit run test_chat.py")
    st.stop()

client = OpenAI(api_key=api_key)

if "messages" not in st.session_state:
    st.session_state.messages = []

# File uploader in sidebar
uploaded = st.sidebar.file_uploader(
    "Joindre un fichier",
    type=["png", "jpg", "jpeg", "gif", "webp", "pdf", "txt", "md", "csv", "json"],
)

if uploaded:
    st.sidebar.success(f"{uploaded.name} ({uploaded.size // 1024} KB)")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if isinstance(msg["content"], str):
            st.markdown(msg["content"])
        else:
            for part in msg["content"]:
                if part["type"] == "text":
                    st.markdown(part["text"])
                elif part["type"] == "image_url":
                    st.image(part["image_url"]["url"], width=300)

if prompt := st.chat_input("Envoie un message..."):
    # Build user message content
    user_content = []
    display_parts = []

    if uploaded:
        file_bytes = uploaded.getvalue()
        mime = uploaded.type or "application/octet-stream"

        if mime.startswith("image/"):
            b64 = base64.b64encode(file_bytes).decode()
            data_url = f"data:{mime};base64,{b64}"
            user_content.append({"type": "image_url", "image_url": {"url": data_url}})
            display_parts.append(("image", data_url))
        else:
            text = file_bytes.decode("utf-8", errors="replace")
            user_content.append({"type": "text", "text": f"[Fichier: {uploaded.name}]\n\n{text}"})
            display_parts.append(("file", uploaded.name))

    user_content.append({"type": "text", "text": prompt})

    st.session_state.messages.append({"role": "user", "content": user_content})
    with st.chat_message("user"):
        for kind, val in display_parts:
            if kind == "image":
                st.image(val, width=300)
            else:
                st.caption(f"📎 {val}")
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("..."):
            response = client.chat.completions.create(
                model="gpt-5.4-mini-2026-03-17",
                messages=[
                    {"role": "system", "content": "You are a helpful personal assistant. Be concise. Answer in the same language as the user."},
                    *st.session_state.messages,
                ],
            )
            reply = response.choices[0].message.content or ""
            st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
