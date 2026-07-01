import sys
import html
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from core.inference import get_engine, stream
from core.memory import get_memory
from core.notes import get_notes
from core.tts import get_tts
from core.summarizer import summarize_conversation, extract_key_points, generate_title
from core.flashcards import generate_flashcards, generate_flashcards_from_chat

st.set_page_config(
    page_title="Zariya",
    page_icon="assets/favicon.png" if Path("assets/favicon.png").exists() else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&family=Noto+Nastaliq+Urdu:wght@400;600&display=swap');

:root {
  --bg:       #0d1117;
  --surface:  #161b22;
  --surface2: #1c2128;
  --border:   #21262d;
  --border2:  #30363d;
  --accent:   #58a6ff;
  --accent-d: rgba(88,166,255,0.13);
  --accent-d2:rgba(88,166,255,0.06);
  --user:     #f0883e;
  --user-d:   rgba(240,136,62,0.10);
  --text:     #e6edf3;
  --muted:    #8b949e;
  --success:  #3fb950;
  --danger:   #f85149;
  --warn:     #d29922;
  --purple:   #bc8cff;
  --radius:   12px;
  --font:     'IBM Plex Sans', sans-serif;
  --mono:     'IBM Plex Mono', monospace;
  --urdu:     'Noto Nastaliq Urdu', serif;
}

html, body, [class*="css"] {
  font-family: var(--font) !important;
  background-color: var(--bg) !important;
  color: var(--text) !important;
}

.block-container { padding: 0 !important; }
.main .block-container { padding: 1.5rem 2rem 6rem !important; max-width: 900px; }

section[data-testid="stSidebar"] {
  background: var(--surface) !important;
  border-right: 1px solid var(--border) !important;
  min-width: 260px !important;
}
section[data-testid="stSidebar"] .block-container { padding: 1rem 0.75rem !important; }
.sidebar-brand { display:flex; align-items:center; gap:10px; padding:0 4px 1rem; border-bottom:1px solid var(--border); margin-bottom:1rem; }
.sidebar-brand .logo { font-size:26px; }
.sidebar-brand .name { font-size:15px; font-weight:600; }
.sidebar-brand .sub  { font-size:11px; color:var(--muted); font-family:var(--urdu); }
.nav-btn { display:flex; align-items:center; gap:8px; padding:8px 10px; border-radius:8px; cursor:pointer; font-size:13px; color:var(--muted); margin-bottom:2px; transition:all .15s; border:1px solid transparent; }
.nav-btn:hover { background:var(--surface2); color:var(--text); }
.nav-btn.active { background:var(--accent-d); color:var(--accent); border-color:rgba(88,166,255,.2); }
.nav-icon { font-size:15px; width:20px; text-align:center; }
.sidebar-section { font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:.7px; padding:8px 4px 4px; }
.sess-row { display:flex; align-items:center; gap:4px; margin-bottom:2px; }
.sess-btn { flex:1; text-align:left; background:transparent; border:1px solid transparent; border-radius:7px; padding:7px 9px; cursor:pointer; font-size:12.5px; color:var(--muted); font-family:var(--font); transition:all .12s; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.sess-btn:hover { background:var(--surface2); color:var(--text); }
.sess-btn.active { background:var(--accent-d); color:var(--accent); border-color:rgba(88,166,255,.18); }
.sess-del { background:transparent; border:none; color:var(--muted); font-size:12px; cursor:pointer; padding:4px 6px; border-radius:5px; }
.sess-del:hover { color:var(--danger); background:rgba(248,81,73,.1); }
.sidebar-stats { font-size:11px; color:var(--muted); line-height:2; padding:8px 4px; border-top:1px solid var(--border); margin-top:8px; }

.page-header { display:flex; align-items:center; gap:14px; padding-bottom:1.2rem; border-bottom:1px solid var(--border); margin-bottom:1.5rem; }
.page-logo { width:42px; height:42px; background:linear-gradient(135deg,#1a2a4a,#0d2137); border:1px solid var(--accent); border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:22px; }
.page-title { font-size:20px; font-weight:600; letter-spacing:-.3px; }
.page-sub { font-size:12px; color:var(--muted); }
.status-pill { margin-left:auto; display:flex; align-items:center; gap:6px; font-size:11px; color:var(--muted); background:var(--surface); border:1px solid var(--border); border-radius:20px; padding:4px 10px; }
.dot { width:7px; height:7px; border-radius:50%; }
.dot.on  { background:var(--success); box-shadow:0 0 5px var(--success); }
.dot.off { background:var(--danger);  box-shadow:0 0 5px var(--danger); }

.msg-wrap { margin-bottom:1rem; }
.msg-row { display:flex; gap:10px; }
.msg-row.user { flex-direction:row-reverse; }
.avatar { width:30px; height:30px; min-width:30px; border-radius:7px; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:600; margin-top:2px; }
.avatar.bot  { background:var(--accent-d); color:var(--accent); border:1px solid rgba(88,166,255,.2); }
.avatar.user { background:var(--user-d);   color:var(--user);   border:1px solid rgba(240,136,62,.2); }
.msg-body { max-width:80%; }
.bubble { padding:11px 15px; border-radius:var(--radius); line-height:1.7; font-size:14px; word-break:break-word; }
.bubble.bot  { background:var(--surface); border:1px solid var(--border); border-top-left-radius:3px; }
.bubble.user { background:var(--user-d);  border:1px solid rgba(240,136,62,.15); border-top-right-radius:3px; }
.bubble p { margin:0 0 .5em; }
.bubble p:last-child { margin:0; }
.bubble pre { background:#0d1117; border:1px solid var(--border); border-radius:7px; padding:12px; overflow-x:auto; margin:.5em 0; }
.bubble code { font-family:var(--mono); font-size:12.5px; }
.bubble :not(pre) > code { background:rgba(13,17,23,.8); padding:2px 6px; border-radius:4px; color:var(--purple); font-size:12.5px; }
.bubble ul, .bubble ol { padding-left:1.4em; margin:.4em 0; }
.bubble li { margin:.2em 0; }
.bubble h1,.bubble h2,.bubble h3 { margin:.6em 0 .3em; font-weight:600; }
.bubble blockquote { border-left:3px solid var(--border2); padding-left:.8em; color:var(--muted); margin:.5em 0; }
.msg-meta { display:flex; gap:8px; align-items:center; margin-top:5px; padding:0 2px; }
.msg-time { font-size:10.5px; color:var(--muted); }
.msg-actions { display:flex; gap:4px; opacity:0; transition:opacity .2s; }
.msg-wrap:hover .msg-actions { opacity:1; }
.action-btn { background:var(--surface); border:1px solid var(--border); border-radius:5px; padding:2px 7px; font-size:11px; color:var(--muted); cursor:pointer; }
.action-btn:hover { color:var(--text); border-color:var(--border2); }

.empty { text-align:center; padding:3.5rem 1rem 2rem; }
.empty-icon { font-size:48px; margin-bottom:1rem; }
.empty-title { font-size:19px; font-weight:600; margin-bottom:.4rem; }
.empty-sub { font-size:14px; color:var(--muted); line-height:1.8; }
.empty-urdu { font-family:var(--urdu); font-size:20px; color:var(--purple); margin:1rem 0; direction:rtl; }
.chips { display:flex; flex-wrap:wrap; gap:7px; justify-content:center; margin-top:1.5rem; }
.chip { background:var(--surface); border:1px solid var(--border); border-radius:18px; padding:6px 13px; font-size:13px; cursor:pointer; }
.chip.urdu { font-family:var(--urdu); direction:rtl; font-size:15px; }

.thinking { display:flex; gap:5px; align-items:center; padding:12px 15px; }
.thinking span { width:7px; height:7px; background:var(--accent); border-radius:50%; animation:bounce .9s ease-in-out infinite; }
.thinking span:nth-child(2) { animation-delay:.2s; }
.thinking span:nth-child(3) { animation-delay:.4s; }
@keyframes bounce { 0%,80%,100%{transform:translateY(0);opacity:.4} 40%{transform:translateY(-6px);opacity:1} }

.fc-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:12px; margin-top:1rem; }
.fc-card { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:16px; cursor:pointer; transition:border-color .15s,transform .1s; min-height:120px; display:flex; flex-direction:column; justify-content:center; }
.fc-card:hover { border-color:var(--accent); transform:translateY(-1px); }
.fc-card.flipped { background:var(--accent-d2); border-color:rgba(88,166,255,.3); }
.fc-label { font-size:10px; text-transform:uppercase; letter-spacing:.7px; color:var(--muted); margin-bottom:8px; }
.fc-text { font-size:14px; line-height:1.6; }
.fc-answer { color:var(--accent); }
.fc-progress { display:flex; gap:8px; align-items:center; margin:1rem 0; }
.fc-bar { flex:1; height:4px; background:var(--border); border-radius:2px; overflow:hidden; }
.fc-fill { height:100%; background:var(--accent); border-radius:2px; transition:width .3s; }

.note-card { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:14px 16px; margin-bottom:10px; cursor:pointer; transition:border-color .12s; }
.note-card:hover { border-color:var(--accent); }
.note-title { font-size:14px; font-weight:500; margin-bottom:4px; }
.note-preview { font-size:12.5px; color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.note-date { font-size:11px; color:var(--muted); margin-top:6px; }

.setting-group { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:16px 18px; margin-bottom:12px; }
.setting-title { font-size:13px; font-weight:600; color:var(--text); margin-bottom:12px; display:flex; align-items:center; gap:7px; }
.model-badge { display:inline-flex; align-items:center; gap:6px; background:rgba(63,185,80,.1); border:1px solid rgba(63,185,80,.3); border-radius:20px; padding:4px 12px; font-size:12px; color:var(--success); }
.model-badge.err { background:rgba(248,81,73,.1); border-color:rgba(248,81,73,.3); color:var(--danger); }

div[data-testid="stChatInput"] textarea { font-family:var(--font) !important; font-size:14px !important; }
.stTextInput > div > div { background:var(--surface) !important; border:1px solid var(--border) !important; border-radius:9px !important; }
.stTextInput input { color:var(--text) !important; font-family:var(--font) !important; font-size:14px !important; }
.stTextArea textarea { background:var(--surface) !important; border:1px solid var(--border) !important; color:var(--text) !important; font-family:var(--font) !important; border-radius:9px !important; }
.stButton > button { border-radius:7px !important; font-family:var(--font) !important; font-size:13px !important; }
.stSelectbox > div { background:var(--surface) !important; }
.stSlider > div > div { accent-color:var(--accent) !important; }
div[data-testid="stExpander"] { background:var(--surface); border:1px solid var(--border) !important; border-radius:var(--radius) !important; }
hr { border-color:var(--border) !important; }
.stAlert { border-radius:var(--radius) !important; }
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:var(--border2); border-radius:3px; }
</style>
""", unsafe_allow_html=True)


def _safe(text: str) -> str:
    return html.escape(str(text))


def render_bubble(content: str, role: str, timestamp: str = ""):
    avatar_class = "bot" if role == "assistant" else "user"
    avatar_letter = "Z" if role == "assistant" else "U"
    bubble_class = "bot" if role == "assistant" else "user"
    time_str = timestamp[11:16] if len(timestamp) > 15 else ""

    col_av, col_msg = (st.columns([1, 11]) if role == "assistant" else st.columns([11, 1]))

    if role == "assistant":
        with col_av:
            st.markdown(
                f'<div class="avatar {avatar_class}">{avatar_letter}</div>',
                unsafe_allow_html=True,
            )
        with col_msg:
            st.markdown(
                f'<div class="bubble {bubble_class}">\n\n{content}\n\n</div>',
                unsafe_allow_html=True,
            )
            if time_str:
                st.markdown(
                    f'<div class="msg-time">{time_str}</div>',
                    unsafe_allow_html=True,
                )
    else:
        with col_msg:
            st.markdown(
                f'<div class="bubble {bubble_class}">{_safe(content)}</div>',
                unsafe_allow_html=True,
            )
            if time_str:
                st.markdown(
                    f'<div class="msg-time" style="text-align:right">{time_str}</div>',
                    unsafe_allow_html=True,
                )
        with col_av:
            st.markdown(
                f'<div class="avatar {avatar_class}">{avatar_letter}</div>',
                unsafe_allow_html=True,
            )


memory  = get_memory()
engine  = get_engine()
notes   = get_notes()
tts     = get_tts()

def _init_state():
    defaults = {
        "page": "chat",
        "pending_input": "",
        "tts_rate": 160,
        "tts_enabled": False,
        "show_timestamps": False,
        "max_tokens": 512,
        "temperature": 0.7,
        "fc_cards": [],
        "fc_flipped": set(),
        "fc_known": set(),
        "editing_note": None,
        "regen_trigger": None,
    }
    sessions = memory.get_sessions()
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = (
            sessions[0]["session_id"] if sessions else memory.new_session()
        )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

engine._max_tokens  = st.session_state.max_tokens
engine._temperature = st.session_state.temperature


with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
      <div class="logo">Z</div>
      <div>
        <div class="name">Zariya</div>
        <div class="sub">ذریعہ</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    pages = [
        ("chat",       "Chat"),
        ("flashcards", "Flashcards"),
        ("notepad",    "Notepad"),
        ("settings",   "Settings"),
    ]
    for pid, label in pages:
        is_active = st.session_state.page == pid
        if st.button(
            label,
            key=f"nav_{pid}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.page = pid
            st.rerun()

    st.markdown("---")

    if st.button("New Conversation", use_container_width=True, type="primary"):
        st.session_state.session_id = memory.new_session()
        st.session_state.page = "chat"
        st.rerun()

    st.markdown('<div class="sidebar-section">Recent</div>', unsafe_allow_html=True)
    sessions = memory.get_sessions()
    for s in sessions[:30]:
        sid    = s["session_id"]
        active = "active" if sid == st.session_state.session_id else ""
        title  = s.get("title", "Untitled")[:34]
        c1, c2 = st.columns([5, 1])
        with c1:
            label = ("-> " if active else "") + title
            if st.button(label, key=f"s_{sid}", use_container_width=True):
                st.session_state.session_id = sid
                st.session_state.page = "chat"
                st.rerun()
        with c2:
            if st.button("x", key=f"d_{sid}"):
                memory.delete_session(sid)
                remaining = [x for x in sessions if x["session_id"] != sid]
                st.session_state.session_id = (
                    remaining[0]["session_id"] if remaining else memory.new_session()
                )
                st.rerun()

    stats = memory.get_stats()
    st.markdown(
        f'<div class="sidebar-stats">'
        f'{stats["sessions"]} conversations &nbsp;·&nbsp; '
        f'{stats["messages"]} messages<br>'
        f'{stats["file_size_kb"]} KB on disk'
        f'</div>',
        unsafe_allow_html=True,
    )


page = st.session_state.page


if page == "chat":
    model_info  = engine.get_model_info()
    ready       = model_info["status"] == "loaded"
    dot_class   = "on" if ready else "off"
    dot_label   = model_info.get("name", "No model") if ready else "Model missing"

    st.markdown(f"""
    <div class="page-header">
      <div class="page-logo">Z</div>
      <div>
        <div class="page-title">Zariya</div>
        <div class="page-sub">ذریعہ &nbsp;·&nbsp; Urdu & English &nbsp;·&nbsp; Offline</div>
      </div>
      <div class="status-pill">
        <span class="dot {dot_class}"></span>
        {_safe(dot_label)}
      </div>
    </div>
    """, unsafe_allow_html=True)

    tc1, tc2, tc3, tc4, tc5 = st.columns([2, 2, 2, 2, 4])
    with tc1:
        if st.button("Summarize", use_container_width=True):
            st.session_state.pending_input = "__SUMMARIZE__"
    with tc2:
        if st.button("Key Points", use_container_width=True):
            st.session_state.pending_input = "__KEYPOINTS__"
    with tc3:
        if st.button("Flashcards", use_container_width=True):
            st.session_state.pending_input = "__FLASHCARDS__"
    with tc4:
        if st.button("Auto-Title", use_container_width=True):
            st.session_state.pending_input = "__AUTOTITLE__"

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    session     = next((s for s in memory.get_sessions() if s["session_id"] == st.session_state.session_id), None)
    raw_msgs    = session.get("messages", []) if session else []
    messages    = [{"role": m["role"], "content": m["content"]} for m in raw_msgs]

    if not messages:
        st.markdown("""
        <div class="empty">
          <div class="empty-title">Assalam-o-Alaikum</div>
          <div class="empty-sub">Ask anything in Urdu or English.</div>
          <div class="empty-urdu">کچھ بھی پوچھیں</div>
        </div>
        """, unsafe_allow_html=True)

        suggestions = [
            ("اردو میں کہانی لکھو", True),
            ("Explain machine learning", False),
            ("Python mein loop kaise likhte hain?", False),
            ("پاکستان کی تاریخ", True),
            ("Write a professional email", False),
            ("مجھے ریاضی سکھاؤ", True),
            ("What is quantum computing?", False),
            ("Translate: Good morning", False),
        ]
        cols = st.columns(4)
        for i, (sug, is_urdu) in enumerate(suggestions):
            with cols[i % 4]:
                if st.button(sug, key=f"sug_{i}", use_container_width=True):
                    st.session_state.pending_input = sug
                    st.rerun()

    else:
        show_ts = st.session_state.show_timestamps
        for i, raw_msg in enumerate(raw_msgs):
            role    = raw_msg["role"]
            content = raw_msg["content"]
            ts      = raw_msg.get("timestamp", "") if show_ts else ""
            render_bubble(content, role, ts)

        last_bot = next((m for m in reversed(raw_msgs) if m["role"] == "assistant"), None)
        if last_bot:
            b1, b2, b3, b4, _ = st.columns([1.5, 1.5, 1.5, 1.5, 5])
            with b1:
                show_copy = st.button("Copy", key="copy_last")
            with b2:
                if st.button("Regenerate", key="regen_last"):
                    sess = memory._find_session(st.session_state.session_id)
                    if sess and sess["messages"] and sess["messages"][-1]["role"] == "assistant":
                        sess["messages"].pop()
                        from core.memory import _save_all
                        _save_all(memory._sessions)
                    st.session_state.regen_trigger = True
                    st.rerun()
            with b3:
                if tts.available:
                    if st.button("Read aloud", key="tts_last"):
                        tts.speak(last_bot["content"])
            with b4:
                if st.button("Auto-title", key="pin_sess"):
                    st.session_state.pending_input = "__AUTOTITLE__"
                    st.rerun()
            if show_copy:
                st.code(last_bot["content"], language=None, wrap_lines=True)

    if st.session_state.get("regen_trigger"):
        st.session_state.regen_trigger = False
        messages = memory.get_messages(st.session_state.session_id)
        if ready and messages:
            with st.chat_message("assistant", avatar="Z"):
                placeholder = st.empty()
                full = ""
                for tok in engine.stream_with_settings(messages,
                        max_tokens=st.session_state.max_tokens,
                        temperature=st.session_state.temperature):
                    full += tok
                    placeholder.markdown(full + "▌")
                placeholder.markdown(full)
                memory.add_message(st.session_state.session_id, "assistant", full)
                if tts.available and st.session_state.tts_enabled:
                    tts.speak(full)
            st.rerun()

    user_input = st.chat_input("Ask anything in Urdu or English...")

    if st.session_state.pending_input:
        user_input = st.session_state.pending_input
        st.session_state.pending_input = ""

    if user_input:
        if user_input == "__SUMMARIZE__":
            msgs = memory.get_messages(st.session_state.session_id)
            if msgs and ready:
                with st.spinner("Summarizing..."):
                    summary = summarize_conversation(msgs, engine)
                memory.add_message(st.session_state.session_id, "assistant",
                    f"**Conversation Summary**\n\n{summary}")
                st.rerun()
            else:
                st.info("Start a conversation first, or check model status.")

        elif user_input == "__KEYPOINTS__":
            msgs = memory.get_messages(st.session_state.session_id)
            if msgs and ready:
                with st.spinner("Extracting key points..."):
                    kp = extract_key_points(msgs, engine)
                memory.add_message(st.session_state.session_id, "assistant",
                    f"**Key Points**\n\n{kp}")
                st.rerun()
            else:
                st.info("Start a conversation first, or check model status.")

        elif user_input == "__FLASHCARDS__":
            msgs = memory.get_messages(st.session_state.session_id)
            if msgs and ready:
                with st.spinner("Generating flashcards..."):
                    cards = generate_flashcards_from_chat(msgs, engine)
                if cards:
                    st.session_state.fc_cards   = cards
                    st.session_state.fc_flipped = set()
                    st.session_state.fc_known   = set()
                    st.session_state.page       = "flashcards"
                    st.rerun()
                else:
                    st.warning("Couldn't generate flashcards. Try asking about a specific topic first.")
            else:
                st.info("Start a conversation first, or check model status.")

        elif user_input == "__AUTOTITLE__":
            msgs = memory.get_messages(st.session_state.session_id)
            if msgs and ready:
                with st.spinner("Generating title..."):
                    new_title = generate_title(msgs, engine)
                memory.rename_session(st.session_state.session_id, new_title)
                st.success(f'Renamed to: "{new_title}"')
                st.rerun()

        else:
            memory.add_message(st.session_state.session_id, "user", user_input.strip())
            render_bubble(user_input.strip(), "user")

            msgs = memory.get_messages(st.session_state.session_id)

            if ready:
                with st.chat_message("assistant", avatar="Z"):
                    placeholder = st.empty()
                    placeholder.markdown(
                        '<div class="bubble bot thinking"><span></span><span></span><span></span></div>',
                        unsafe_allow_html=True,
                    )
                    full = ""
                    for tok in engine.stream_with_settings(
                        msgs,
                        max_tokens=st.session_state.max_tokens,
                        temperature=st.session_state.temperature,
                    ):
                        full += tok
                        placeholder.markdown(full + "▌")
                    placeholder.markdown(full)
                memory.add_message(st.session_state.session_id, "assistant", full)
                if tts.available and st.session_state.tts_enabled:
                    tts.speak(full)
            else:
                err = ("**No model loaded.** Go to Settings for setup instructions.")
                render_bubble(err, "assistant")
                memory.add_message(st.session_state.session_id, "assistant", err)
            st.rerun()


elif page == "flashcards":
    st.markdown("""
    <div class="page-header">
      <div class="page-logo">FC</div>
      <div>
        <div class="page-title">Flashcards</div>
        <div class="page-sub">AI-generated study cards</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Generate new flashcards", expanded=not st.session_state.fc_cards):
        col_t, col_n = st.columns([4, 1])
        with col_t:
            topic = st.text_input("Topic", placeholder="e.g. Python decorators, WW2 causes, Photosynthesis...")
        with col_n:
            count = st.selectbox("Cards", [6, 8, 10, 12], index=1)
        if st.button("Generate", type="primary", use_container_width=True):
            if not topic.strip():
                st.warning("Enter a topic first.")
            elif engine.get_model_info()["status"] != "loaded":
                st.error("Model not loaded. Check Settings.")
            else:
                with st.spinner(f"Generating {count} flashcards on '{topic}'..."):
                    cards = generate_flashcards(topic, engine, count=count)
                if cards:
                    st.session_state.fc_cards   = cards
                    st.session_state.fc_flipped = set()
                    st.session_state.fc_known   = set()
                    st.success(f"Generated {len(cards)} cards.")
                    st.rerun()
                else:
                    st.error("Failed to generate cards. Try a more specific topic.")

    cards = st.session_state.fc_cards
    if cards:
        known  = st.session_state.fc_known
        total  = len(cards)
        pct    = int(len(known) / total * 100) if total else 0

        st.markdown(f"""
        <div class="fc-progress">
          <span style="font-size:12px; color:var(--muted)">{len(known)}/{total} known</span>
          <div class="fc-bar"><div class="fc-fill" style="width:{pct}%"></div></div>
          <span style="font-size:12px; color:var(--accent)">{pct}%</span>
        </div>
        """, unsafe_allow_html=True)

        if len(known) == total:
            st.success("All cards reviewed. Generate a new set to keep going.")

        b1, b2, b3 = st.columns([1, 1, 4])
        with b1:
            if st.button("Shuffle"):
                import random
                random.shuffle(st.session_state.fc_cards)
                st.session_state.fc_flipped = set()
                st.rerun()
        with b2:
            if st.button("Reset"):
                st.session_state.fc_flipped = set()
                st.session_state.fc_known   = set()
                st.rerun()

        cols = st.columns(2)
        for i, card in enumerate(cards):
            flipped = i in st.session_state.fc_flipped
            is_known = i in st.session_state.fc_known
            card_class = "fc-card flipped" if flipped else "fc-card"
            border_extra = "border-color:var(--success);" if is_known else ""

            with cols[i % 2]:
                if flipped:
                    st.markdown(f"""
                    <div class="{card_class}" style="{border_extra}">
                      <div class="fc-label">Answer</div>
                      <div class="fc-text fc-answer">{_safe(card['back'])}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="{card_class}">
                      <div class="fc-label">Question {i+1}</div>
                      <div class="fc-text">{_safe(card['front'])}</div>
                    </div>
                    """, unsafe_allow_html=True)

                c1, c2, c3 = st.columns(3)
                with c1:
                    label = "Hide" if flipped else "Reveal"
                    if st.button(label, key=f"flip_{i}", use_container_width=True):
                        flipped_set = st.session_state.fc_flipped
                        if i in flipped_set:
                            flipped_set.discard(i)
                        else:
                            flipped_set.add(i)
                        st.session_state.fc_flipped = flipped_set
                        st.rerun()
                with c2:
                    if st.button("Know it", key=f"know_{i}", use_container_width=True):
                        st.session_state.fc_known.add(i)
                        st.session_state.fc_flipped.discard(i)
                        st.rerun()
                with c3:
                    if st.button("Again", key=f"again_{i}", use_container_width=True):
                        st.session_state.fc_known.discard(i)
                        st.session_state.fc_flipped.discard(i)
                        st.rerun()


elif page == "notepad":
    st.markdown("""
    <div class="page-header">
      <div class="page-logo">NP</div>
      <div>
        <div class="page-title">Notepad</div>
        <div class="page-sub">Quick offline notes, saved to disk</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    all_notes = notes.get_all()
    editing   = st.session_state.editing_note

    col_list, col_edit = st.columns([2, 3])

    with col_list:
        if st.button("New Note", use_container_width=True, type="primary"):
            new_note = notes.create()
            st.session_state.editing_note = new_note["id"]
            st.rerun()

        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

        if not all_notes:
            st.markdown("<div style='color:var(--muted); font-size:13px; padding:1rem 0;'>No notes yet.</div>", unsafe_allow_html=True)

        for note in all_notes:
            nid     = note["id"]
            active  = "border-color:var(--accent);" if nid == editing else ""
            preview = note["body"][:60].replace("\n", " ") or "Empty note"
            date    = note.get("updated_at", note.get("created_at", ""))[:10]

            st.markdown(f"""
            <div class="note-card" style="{active}">
              <div class="note-title">{_safe(note['title'])}</div>
              <div class="note-preview">{_safe(preview)}</div>
              <div class="note-date">{date}</div>
            </div>
            """, unsafe_allow_html=True)

            nb1, nb2 = st.columns([3, 1])
            with nb1:
                if st.button("Open", key=f"open_{nid}", use_container_width=True):
                    st.session_state.editing_note = nid
                    st.rerun()
            with nb2:
                if st.button("Del", key=f"del_note_{nid}", use_container_width=True):
                    notes.delete(nid)
                    if editing == nid:
                        st.session_state.editing_note = None
                    st.rerun()

    with col_edit:
        if editing:
            note = notes.get(editing)
            if note:
                new_title = st.text_input("Title", value=note["title"], key=f"nt_{editing}")
                new_body  = st.text_area("Content", value=note["body"], height=380, key=f"nb_{editing}")

                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    if st.button("Save", use_container_width=True, type="primary"):
                        notes.update(editing, new_title, new_body)
                        st.success("Saved.")
                with ec2:
                    show_copy = st.button("Copy", use_container_width=True)
                with ec3:
                    if st.button("Improve with AI", use_container_width=True):
                        if engine.get_model_info()["status"] == "loaded" and new_body.strip():
                            with st.spinner("Thinking..."):
                                ai_resp = engine.chat([{
                                    "role": "user",
                                    "content": f"Improve and expand this note, keeping the original meaning:\n\n{new_body}"
                                }])
                            notes.update(editing, new_title, ai_resp)
                            st.rerun()
                        else:
                            st.warning("Model not loaded or note is empty.")
                if show_copy:
                    st.code(new_body, language=None, wrap_lines=True)
            else:
                st.session_state.editing_note = None
                st.rerun()
        else:
            st.markdown("""
            <div style="display:flex; align-items:center; justify-content:center; height:300px; color:var(--muted); font-size:14px;">
              Select a note or create a new one
            </div>
            """, unsafe_allow_html=True)


elif page == "settings":
    st.markdown("""
    <div class="page-header">
      <div class="page-logo">Cfg</div>
      <div>
        <div class="page-title">Settings</div>
        <div class="page-sub">Model, interface, TTS, data</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="setting-group">', unsafe_allow_html=True)
        st.markdown('<div class="setting-title">Model</div>', unsafe_allow_html=True)
        info = engine.get_model_info()
        if info["status"] == "loaded":
            st.markdown(f"""
            <div class="model-badge">{_safe(info['name'])} &nbsp;·&nbsp; {info['size_mb']} MB</div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div class="model-badge err">No model loaded</div>', unsafe_allow_html=True)
            st.markdown("""
**Setup:**
1. Download a `.gguf` model from [huggingface.co/TheBloke](https://huggingface.co/TheBloke)
2. Place it in the `models/` folder as `model.gguf`
3. Restart the app

**Recommended models:**
- `Mistral-7B-Instruct-v0.2.Q4_K_M.gguf` (~4.4 GB)
- `Meta-Llama-3-8B-Instruct.Q4_K_M.gguf` (~4.9 GB)
- `phi-3-mini-4k-instruct.Q4_K_M.gguf` (~2.2 GB, fastest)

**GPU acceleration:**
```bash
# NVIDIA
CMAKE_ARGS="-DLLAMA_CUDA=on" pip install llama-cpp-python --force-reinstall
# Apple Silicon
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python --force-reinstall
```
            """)
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="setting-group">', unsafe_allow_html=True)
        st.markdown('<div class="setting-title">Generation</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            new_temp = st.slider("Temperature", 0.0, 1.5, st.session_state.temperature, 0.05,
                help="Higher = more creative. Lower = more focused.")
            st.session_state.temperature = new_temp
        with c2:
            new_tok = st.slider("Max tokens", 128, 2048, st.session_state.max_tokens, 64,
                help="Maximum length of each response.")
            st.session_state.max_tokens = new_tok
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="setting-group">', unsafe_allow_html=True)
        st.markdown('<div class="setting-title">Text-to-Speech</div>', unsafe_allow_html=True)
        if tts.available:
            st.session_state.tts_enabled = st.toggle("Auto read-aloud", st.session_state.tts_enabled)
            voices = tts.get_voices()
            if voices:
                voice_names = [v["name"] for v in voices]
                sel = st.selectbox("Voice", voice_names)
                chosen = next((v for v in voices if v["name"] == sel), None)
                if chosen:
                    tts.set_voice(chosen["id"])
            new_rate = st.slider("Speed (wpm)", 80, 280, st.session_state.tts_rate, 10)
            st.session_state.tts_rate = new_rate
            tts.set_rate(new_rate)
            if st.button("Test voice"):
                tts.speak("Assalam-o-Alaikum. Main Zariya hoon, aap ka offline AI assistant.")
        else:
            st.info("TTS not available. Install: `pip install pyttsx3`")
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="setting-group">', unsafe_allow_html=True)
        st.markdown('<div class="setting-title">Interface</div>', unsafe_allow_html=True)
        st.session_state.show_timestamps = st.toggle(
            "Show message timestamps", st.session_state.show_timestamps)
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="setting-group">', unsafe_allow_html=True)
        st.markdown('<div class="setting-title">Data</div>', unsafe_allow_html=True)
        stats = memory.get_stats()
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.metric("Conversations", stats["sessions"])
        with sc2:
            st.metric("Messages", stats["messages"])
        with sc3:
            st.metric("Storage", f"{stats['file_size_kb']} KB")

        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

        sid     = st.session_state.session_id
        session = next((s for s in memory.get_sessions() if s["session_id"] == sid), None)
        if session:
            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                text = memory.export_session(sid)
                if text:
                    st.download_button("Export chat (.txt)", text,
                        file_name=f"zariya_{session['title'][:20]}.txt",
                        mime="text/plain", use_container_width=True)
            with ec2:
                import json as _json
                all_data = _json.dumps(memory.get_sessions(), ensure_ascii=False, indent=2)
                st.download_button("Export all (.json)", all_data,
                    file_name="zariya_all_chats.json",
                    mime="application/json", use_container_width=True)
            with ec3:
                if st.button("Clear all history", use_container_width=True):
                    memory.clear_all()
                    st.session_state.session_id = memory.new_session()
                    st.success("Cleared.")
                    st.rerun()

        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
        if session:
            new_name = st.text_input("Rename current conversation", value=session.get("title",""))
            if st.button("Rename"):
                memory.rename_session(sid, new_name)
                st.success(f'Renamed to "{new_name}"')
                st.rerun()

        st.markdown("**Search all conversations**")
        q = st.text_input("Search", placeholder="Type to search...", label_visibility="collapsed")
        if q:
            results = memory.search(q)
            if results:
                for r in results[:12]:
                    prefix = "You" if r["role"] == "user" else "Zariya"
                    st.markdown(f"""
                    <div style="background:var(--surface2); border:1px solid var(--border); border-radius:8px; padding:9px 13px; margin-bottom:7px;">
                      <div style="font-size:11px; color:var(--muted);">{_safe(r['session_title'])} &nbsp;·&nbsp; {prefix}</div>
                      <div style="font-size:13px; margin-top:3px;">{_safe(r['snippet'])}...</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("Open", key=f"sr_{r['session_id']}_{r['snippet'][:10]}"):
                        st.session_state.session_id = r["session_id"]
                        st.session_state.page = "chat"
                        st.rerun()
            else:
                st.info("No results found.")
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="setting-group">', unsafe_allow_html=True)
        st.markdown('<div class="setting-title">About</div>', unsafe_allow_html=True)
        st.markdown("""
**Zariya v2** — Offline AI Assistant for Urdu & English

Built with `llama-cpp-python`, `Streamlit`, `pyttsx3`

Fully local — no data leaves your device.
Supports Urdu, Roman Urdu, and English.

[GitHub](https://github.com/aayanahmed20/zariya) · MIT License
        """)
        st.markdown('</div>', unsafe_allow_html=True)
