"""Streamlit chat UI with Odoo tool calling, sharing the bot's tools."""

import base64
import os

import streamlit as st
from openai import OpenAI

from bot.odoo import OdooClient, OdooConfig
from bot.tools import TOOLS, dispatch

st.set_page_config(page_title="homeops AI test", layout="centered")
st.title("homeops AI test")

api_key = os.environ.get("OPENAI_API_KEY", "")
if not api_key:
    st.error("OPENAI_API_KEY not set.")
    st.stop()

client = OpenAI(api_key=api_key)

MODEL = "gpt-5.4-mini-2026-03-17"
from bot.config import _load_prompt

SYSTEM_PROMPT = _load_prompt("system")
MAX_TOOL_ROUNDS = 10


@st.cache_resource
def get_odoo_client() -> OdooClient:
    return OdooClient(OdooConfig(
        url=os.environ.get("ODOO_URL", "http://localhost:8069"),
        db=os.environ.get("ODOO_DB", "homeops"),
        user=os.environ.get("ODOO_USER", ""),
        password=os.environ.get("ODOO_PASSWORD", ""),
    ))


odoo = get_odoo_client()

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
    if msg["role"] in ("user", "assistant"):
        with st.chat_message(msg["role"]):
            if isinstance(msg["content"], str):
                st.markdown(msg["content"])
            elif isinstance(msg["content"], list):
                for part in msg["content"]:
                    if part.get("type") == "text":
                        st.markdown(part["text"])
                    elif part.get("type") == "image_url":
                        st.image(part["image_url"]["url"], width=300)

if prompt := st.chat_input("Envoie un message..."):
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
                st.caption(f"\U0001f4ce {val}")
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("..."):
            # Build API messages (system + history, skipping tool messages for display)
            api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            api_messages.extend(st.session_state.messages)

            # Tool calling loop
            reply = ""
            for _ in range(MAX_TOOL_ROUNDS):
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=api_messages,
                    tools=TOOLS,
                )
                msg = response.choices[0].message

                if not msg.tool_calls:
                    reply = msg.content or ""
                    break

                # Append assistant message with tool calls
                api_messages.append(msg)

                for tc in msg.tool_calls:
                    result = dispatch(odoo, tc.function.name, tc.function.arguments)
                    api_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })
            else:
                reply = "Too many tool calls. Please try a simpler question."

            st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
