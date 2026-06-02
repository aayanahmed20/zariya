"""
Zariya – Full UI
A polished, full-featured Streamlit interface for the offline AI assistant.
"""

import sys
from pathlib import Path

# Ensure project root is on the path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from core.inference import get_engine, stream
from core.memory import get_memory

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Zariya – Offline AI",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Import fonts */
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

  /* Root variables */
  :root {
    --clr-bg: #0d1117;
    --clr-surface: #161b22;
    --clr-border: #21262d;
    --clr-accent: #58a6ff;
    --clr-accent-dim: rgba(88, 166, 255, 0.12);
    --clr-user: #f0883e;
    --clr-user-dim: rgba(240, 136, 62, 0.10);
    --clr-text: #e6edf3;
    --clr-muted: #8b949e;
    --clr-success: #3fb950;
    --clr-urdu: #bc8cff;
    --radius: 12px;
    --font: 'IBM Plex Sans', sans-serif;
    --font-mono: 'IBM Plex Mono', monospace;
  }

  /* Global */
  html, body, [class*="css"] {
    font-family: var(--font) !important;
    background-color: var(--clr-bg) !important;
    color: var(--clr-text) !important;
  }

  /* Remove default streamlit padding */
  .block-container { padding: 0 !important; }
  .main .block-container { padding: 1.5rem 2rem !important; max-width: 860px; }

  /* Header */
  .zariya-header {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 0 0 1.2rem 0;
    border-bottom: 1px solid var(--clr-border);
    margin-bottom: 1.5rem;
  }
  .zariya-logo {
    width: 42px; height: 42px;
    background: linear-gradient(135deg, #1a2a4a 0%, #0d2137 100%);
    border: 1px solid var(--clr-accent);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px;
  }
  .zariya-title { font-size: 22px; font-weight: 600; letter-spacing: -0.3px; }
  .zariya-sub { font-size: 12px; color: var(--clr-muted); margin-top: 1px; }
  .status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--clr-success);
    box-shadow: 0 0 6px var(--clr-success);
    margin-left: auto;
  }
  .status-dot.offline { background: #f85149; box-shadow: 0 0 6px #f85149; }

  /* Chat messages */
  .chat-container { display: flex; flex-direction: column; gap: 1rem; padding-bottom: 6rem; }

  .msg-row { display: flex; gap: 12px; }
  .msg-row.user { flex-direction: row-reverse; }

  .msg-avatar {
    width: 32px; height: 32px; min-width: 32px;
    border-radius: 8px; display: flex; align-items: center;
    justify-content: center; font-size: 14px; font-weight: 600;
    margin-top: 2px;
  }
  .msg-avatar.bot { background: var(--clr-accent-dim); color: var(--clr-accent); border: 1px solid rgba(88,166,255,0.2); }
  .msg-avatar.user { background: var(--clr-user-dim); color: var(--clr-user); border: 1px solid rgba(240,136,62,0.2); }

  .msg-bubble {
    max-width: 78%;
    padding: 12px 16px;
    border-radius: var(--radius);
    line-height: 1.65;
    font-size: 14.5px;
  }
  .msg-bubble.bot {
    background: var(--clr-surface);
    border: 1px solid var(--clr-border);
    border-top-left-radius: 4px;
  }
  .msg-bubble.user {
    background: var(--clr-user-dim);
    border: 1px solid rgba(240,136,62,0.15);
    border-top-right-radius: 4px;
  }
  .msg-time { font-size: 10.5px; color: var(--clr-muted); margin-top: 5px; }

  /* Empty state */
  .empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: var(--clr-muted);
  }
  .empty-logo { font-size: 52px; margin-bottom: 1rem; }
  .empty-title { font-size: 20px; font-weight: 600; color: var(--clr-text); margin-bottom: 0.4rem; }
  .empty-sub { font-size: 14px; line-height: 1.7; }
  .suggestion-grid { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 1.5rem; }
  .suggestion-chip {
    background: var(--clr-surface);
    border: 1px solid var(--clr-border);
    border-radius: 20px;
    padding: 7px 14px;
    font-size: 13px;
    cursor: pointer;
    transition: border-color 0.15s;
  }
  .suggestion-chip:hover { border-color: var(--clr-accent); }

  /* Input area */
  .input-area {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: linear-gradient(transparent, var(--clr-bg) 30%);
    padding: 1rem 0 1.5rem;
    z-index: 100;
  }
  .input-inner { max-width: 860px; margin: 0 auto; padding: 0 2rem; }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    background: var(--clr-surface) !important;
    border-right: 1px solid var(--clr-border) !important;
  }
  section[data-testid="stSidebar"] .block-container { padding: 1rem !important; }

  .session-item {
    padding: 9px 12px;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.12s;
    border: 1px solid transparent;
    margin-bottom: 4px;
    font-size: 13px;
  }
  .session-item:hover { background: var(--clr-accent-dim); }
  .session-item.active { background: var(--clr-accent-dim); border-color: rgba(88,166,255,0.2); }
  .session-title { font-weight: 500; color: var(--clr-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .session-meta { font-size: 11px; color: var(--clr-muted); margin-top: 2px; }

  /* Streamlit overrides */
  .stTextInput > div > div { background: var(--clr-surface) !important; border: 1px solid var(--clr-border) !important; border-radius: 10px !important; }
  .stTextInput input { color: var(--clr-text) !important; font-family: var(--font) !important; }
  .stButton > button { border-radius: 8px !important; font-family: var(--font) !important; }
  .stSelectbox > div { background: var(--clr-surface) !important; }

  /* Divider */
  hr { border-color: var(--clr-border) !important; }

  /* Code blocks in messages */
  .msg-bubble code {
    background: #0d1117;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--clr-urdu);
  }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--clr-border); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ─── State Init ─────────────────────────────────────────────────────────────
memory = get_memory()
engine = get_engine()

if "session_id" not in st.session_state:
    sessions = memory.get_sessions()
    if sessions:
        st.session_state.session_id = sessions[0]["session_id"]
    else:
        st.session_state.session_id = memory.new_session()

if "pending_input" not in st.session_state:
    st.session_state.pending_input = ""

if "page" not in st.session_state:
    st.session_state.page = "chat"


# ─── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    # Branding
    st.markdown("""
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:1rem;">
      <div style="font-size:24px;">🌙</div>
      <div>
        <div style="font-size:16px; font-weight:600;">Zariya</div>
        <div style="font-size:11px; color:var(--clr-muted);">ذریعہ — Offline AI</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # New chat button
    if st.button("✦ New Conversation", use_container_width=True, type="primary"):
        st.session_state.session_id = memory.new_session()
        st.rerun()

    st.markdown("---")

    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💬 Chat", use_container_width=True):
            st.session_state.page = "chat"
    with col2:
        if st.button("⚙️ Settings", use_container_width=True):
            st.session_state.page = "settings"

    st.markdown("---")
    st.markdown("<div style='font-size:11px; color:var(--clr-muted); margin-bottom:6px; text-transform:uppercase; letter-spacing:.5px;'>Recent Conversations</div>", unsafe_allow_html=True)

    # Session list
    sessions = memory.get_sessions()
    for session in sessions[:25]:
        sid = session["session_id"]
        is_active = sid == st.session_state.session_id
        title = session.get("title", "Untitled")[:38]
        updated = session.get("updated_at", "")[:10]
        msg_count = len(session.get("messages", []))

        col_btn, col_del = st.columns([5, 1])
        with col_btn:
            label = f"{'▶ ' if is_active else ''}{title}"
            if st.button(label, key=f"sess_{sid}", use_container_width=True):
                st.session_state.session_id = sid
                st.session_state.page = "chat"
                st.rerun()
        with col_del:
            if st.button("✕", key=f"del_{sid}"):
                memory.delete_session(sid)
                if is_active:
                    remaining = [s for s in sessions if s["session_id"] != sid]
                    st.session_state.session_id = remaining[0]["session_id"] if remaining else memory.new_session()
                st.rerun()

    st.markdown("---")
    # Stats
    stats = memory.get_stats()
    st.markdown(f"""
    <div style="font-size:11px; color:var(--clr-muted); line-height:2;">
      📁 {stats['sessions']} conversations<br>
      💬 {stats['messages']} messages<br>
      💾 {stats['file_size_kb']} KB stored
    </div>
    """, unsafe_allow_html=True)


# ─── Main Content ────────────────────────────────────────────────────────────

if st.session_state.page == "settings":
    # ─── Settings Page ──────────────────────────────────────────────────────
    st.markdown("## ⚙️ Settings")
    st.markdown("---")

    info = engine.get_model_info()
    st.markdown("### 🤖 Model Status")

    if info["status"] == "loaded":
        st.success(f"✅ **{info['name']}** loaded successfully ({info['size_mb']} MB)")
    else:
        st.error("❌ No model loaded")
        st.markdown("""
**Setup Instructions:**

1. Download a GGUF model from [HuggingFace](https://huggingface.co/TheBloke)
   - Recommended: `Mistral-7B-Instruct-v0.2-GGUF` or `Meta-Llama-3-8B-Instruct-GGUF`
   - Use Q4_K_M quantization for best balance of speed and quality

2. Place the `.gguf` file inside the `models/` folder

3. Rename it to `model.gguf`

4. Restart the app

**Install dependencies:**
```
pip install llama-cpp-python streamlit
```
For GPU acceleration:
```
CMAKE_ARGS="-DLLAMA_CUDA=on" pip install llama-cpp-python --force-reinstall
```
        """)

    st.markdown("---")
    st.markdown("### 💬 Session Management")

    col1, col2 = st.columns(2)
    with col1:
        session_id = st.session_state.session_id
        session = next((s for s in memory.get_sessions() if s["session_id"] == session_id), None)
        if session:
            new_title = st.text_input("Rename current conversation", value=session.get("title", ""))
            if st.button("Rename"):
                memory.rename_session(session_id, new_title)
                st.success("Renamed!")
                st.rerun()

    with col2:
        st.markdown("**Export current conversation**")
        if st.button("📄 Export as Text"):
            text = memory.export_session(session_id)
            if text:
                st.download_button("⬇ Download .txt", text, file_name="zariya_chat.txt", mime="text/plain")

    st.markdown("---")
    st.markdown("### 🔍 Search History")
    query = st.text_input("Search across all conversations", placeholder="Type to search…")
    if query:
        results = memory.search(query)
        if results:
            for r in results[:10]:
                prefix = "You" if r["role"] == "user" else "Zariya"
                st.markdown(f"""
                <div style="background:var(--clr-surface); border:1px solid var(--clr-border); border-radius:8px; padding:10px 14px; margin-bottom:8px;">
                  <div style="font-size:11px; color:var(--clr-muted);">{r['session_title']} · {prefix}</div>
                  <div style="font-size:13px; margin-top:4px;">{r['snippet']}…</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No results found.")

    st.markdown("---")
    st.markdown("### 🗑️ Danger Zone")
    st.warning("This will permanently delete all conversations.")
    if st.button("🗑️ Clear All History", type="secondary"):
        memory.clear_all()
        st.session_state.session_id = memory.new_session()
        st.success("All history cleared.")
        st.rerun()

else:
    # ─── Chat Page ──────────────────────────────────────────────────────────

    # Header
    model_info = engine.get_model_info()
    ready = model_info["status"] == "loaded"
    status_class = "" if ready else "offline"
    st.markdown(f"""
    <div class="zariya-header">
      <div class="zariya-logo">🌙</div>
      <div>
        <div class="zariya-title">Zariya</div>
        <div class="zariya-sub">ذریعہ — Urdu & English AI · Fully Offline</div>
      </div>
      <div class="status-dot {status_class}" title="{'Model ready' if ready else 'Model not loaded'}"></div>
    </div>
    """, unsafe_allow_html=True)

    # Load messages for current session
    messages = memory.get_messages(st.session_state.session_id)

    # ── Suggestion prompts (empty state) ──
    if not messages:
        st.markdown("""
        <div class="empty-state">
          <div class="empty-logo">🌙</div>
          <div class="empty-title">Assalam-o-Alaikum!</div>
          <div class="empty-sub">
            I am Zariya — your offline AI assistant.<br>
            I speak Urdu and English. Ask me anything.
          </div>
          <div style="font-size:22px; margin:1rem 0; color:#bc8cff;">ذریعہ</div>
        </div>
        """, unsafe_allow_html=True)

        suggestions = [
            "اردو میں ایک کہانی لکھو",
            "Explain AI in simple terms",
            "Python code likhne mein madad karo",
            "Pakistan ki tarikh batao",
            "Help me write a formal email",
            "مجھے ریاضی سکھاؤ",
        ]
        cols = st.columns(3)
        for i, suggestion in enumerate(suggestions):
            with cols[i % 3]:
                if st.button(suggestion, key=f"sug_{i}", use_container_width=True):
                    st.session_state.pending_input = suggestion
                    st.rerun()

    # ── Display messages ──
    else:
        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "user":
                st.markdown(f"""
                <div class="msg-row user">
                  <div class="msg-avatar user">U</div>
                  <div>
                    <div class="msg-bubble user">{content}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="msg-row">
                  <div class="msg-avatar bot">Z</div>
                  <div>
                    <div class="msg-bubble bot">{content}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

    # ── Input ──
    st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)

    col_input, col_send = st.columns([9, 1])
    with col_input:
        user_input = st.chat_input(
            "Kuch bhi poochho… (Ask anything in Urdu or English)",
            key="chat_input",
        )

    # Handle suggestion click
    if st.session_state.pending_input:
        user_input = st.session_state.pending_input
        st.session_state.pending_input = ""

    # ── Process input ──
    if user_input and user_input.strip():
        user_text = user_input.strip()

        # Save user message
        memory.add_message(st.session_state.session_id, "user", user_text)

        # Show user message immediately
        st.markdown(f"""
        <div class="msg-row user">
          <div class="msg-avatar user">U</div>
          <div>
            <div class="msg-bubble user">{user_text}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Stream the response
        st.markdown("""
        <div class="msg-row">
          <div class="msg-avatar bot">Z</div>
          <div>
        """, unsafe_allow_html=True)

        msg_history = memory.get_messages(st.session_state.session_id)

        if ready:
            response_placeholder = st.empty()
            full_response = ""

            with st.spinner(""):
                for token in stream(msg_history):
                    full_response += token
                    response_placeholder.markdown(f"""
                    <div class="msg-bubble bot">{full_response}▌</div>
                    """, unsafe_allow_html=True)

            response_placeholder.markdown(f"""
            <div class="msg-bubble bot">{full_response}</div>
            """, unsafe_allow_html=True)

            memory.add_message(st.session_state.session_id, "assistant", full_response)
        else:
            # Model not loaded — show setup message
            setup_msg = (
                "⚠️ **Model not loaded.** Please add a GGUF model to the `models/` folder "
                "and restart the app. Go to ⚙️ Settings for instructions."
            )
            st.markdown(f"""
            <div class="msg-bubble bot">{setup_msg}</div>
            """, unsafe_allow_html=True)
            memory.add_message(st.session_state.session_id, "assistant", setup_msg)

        st.markdown("</div></div>", unsafe_allow_html=True)
        st.rerun()
