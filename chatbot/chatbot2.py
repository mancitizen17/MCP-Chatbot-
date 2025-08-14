import streamlit as st
from llama_index.core.llms import ChatMessage
from llama_index.llms.ollama import Ollama
import logging, time, requests, json, pandas as pd
from typing import List, Dict, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Config & logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(name)s:%(message)s")

OLLAMA_BASE_URL = "http://localhost:11434"   # make sure this matches `ollama serve`
MCP_SERVER_URL  = "http://localhost:8000"

# ─────────────────────────────────────────────────────────────────────────────
# Streamlit session state
# ─────────────────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "mcp_collections" not in st.session_state:
    st.session_state.mcp_collections = []
    st.session_state.active_collection = None

# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────
def get_models() -> List[str]:
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json()["models"]]
    except Exception as e:
        logging.error(f"Could not fetch models: {e}")
        return ["codellama:7b-instruct"]    # fallback so UI still works

def get_mcp_collections():
    try:
        r = requests.get(f"{MCP_SERVER_URL}/collections", timeout=5)
        if r.status_code == 200:
            return r.json()["collections"]
    except Exception as e:
        st.error(f"Failed to fetch collections: {e}")
    return []

def upload_to_mcp(file):
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        r = requests.post(f"{MCP_SERVER_URL}/upload/", files=files, timeout=60)
        if r.status_code == 200:
            return r.json()
        st.error(f"Upload failed: {r.text}")
    except Exception as e:
        st.error(f"Upload error: {e}")
    return None

def get_mcp_context(collection_id: str, query: str):
    try:
        r = requests.post(
            f"{MCP_SERVER_URL}/query/",
            json={"collection_id": collection_id, "query": query},
            timeout=20
        )
        if r.status_code == 200:
            return r.json()["results"]
    except Exception as e:
        logging.error(f"MCP query error: {e}")
    return None

# ─────────────────────────────────────────────────────────────────────────────
# Core chat routine
# ─────────────────────────────────────────────────────────────────────────────
def prepare_chat(model: str, messages: List[Dict], user_query: str) -> str:
    try:
        llm = Ollama(model=model, base_url=OLLAMA_BASE_URL, request_timeout=180)

        # ── 1. Optionally append MCP context ────────────────────────────────
        if st.session_state.active_collection:
            hits = get_mcp_context(st.session_state.active_collection, user_query)
            if hits:
                context = "\n\nRelevant context:\n" + "\n".join(map(str, hits[:3]))
                if messages and messages[-1]["role"] == "user":
                    messages[-1]["content"] += context

        # ── 2. Convert to ChatMessage objects ───────────────────────────────
        chat_messages = [ChatMessage(role=m["role"], content=m["content"]) for m in messages]
        logging.info(f"chat_messages: {chat_messages}")

        # ── 3. Try streaming first, fall back to non-streaming  ─────────────
        streamed_answer = ""
        placeholder = st.empty()

        resp = llm.stream_chat(chat_messages)
        if resp is None:
            logging.warning("stream_chat returned None → falling back to llm.chat()")
            result = llm.chat(chat_messages)
            return result.message.content
            raise ValueError("llm.stream_chat returned None (no response from model)")

        for chunk in resp:
            streamed_answer += chunk.delta
            placeholder.write(streamed_answer)

        return streamed_answer
   
    except Exception as e:
        logging.error(f"Error during chat: {e}")
        raise

# ─────────────────────────────────────────────────────────────────────────────
# Streamlit UI
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    st.set_page_config("LLM Client with MCP", layout="wide")

    # Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Configuration")
        model = st.selectbox("Model", get_models())
        st.success(f"Current Model: {model}")

        st.header("MCP Document Management")
        uploaded = st.file_uploader("Upload doc", type=["json", "csv", "xlsx", "txt"])
        if uploaded:
            if upload_to_mcp(uploaded):
                st.success(f"Uploaded {uploaded.name}")
                st.session_state.mcp_collections = get_mcp_collections()

        st.session_state.mcp_collections = get_mcp_collections()
        if st.session_state.mcp_collections:
            opts = {c["id"]: f"{c['metadata']['filename']} ({c['metadata']['type']})"
                    for c in st.session_state.mcp_collections}
            sel = st.selectbox("Active collection", list(opts.keys()), format_func=lambda x: opts[x])
            st.session_state.active_collection = sel
            st.info(f"Selected: {opts[sel]}")
        else:
            st.info("No collections in MCP")

    # Chat history display ─────────────────────────────────────────────────
    st.markdown("#### Chat")
    with st.container():
        for m in st.session_state.messages:
            who = "User" if m["role"] == "user" else "Assistant"
            color = "#d4f1f9" if m["role"] == "user" else "#e0ffe0"
            st.markdown(f"<div style='background:#222;padding:8px;border-radius:6px;color:{color};'>"
                        f"**{who}:** {m['content']}</div>", unsafe_allow_html=True)

    # Input box ────────────────────────────────────────────────────────────
    if prompt := st.chat_input("Type your message…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("assistant"):
            start = time.time()
            try:
                reply = prepare_chat(model, st.session_state.messages.copy(), prompt)
                elapsed = time.time() - start
                st.session_state.messages.append({"role": "assistant",
                                                  "content": f"{reply}\n\nTook {elapsed:.2f}s"})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": str(e)})
                st.error("❌ Error while generating response")

if __name__ == "__main__":
    main()
