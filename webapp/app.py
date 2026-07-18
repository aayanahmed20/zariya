"""
Zariya -- offline-first, privacy-focused AI platform for Urdu and low-resource languages.

Architecture, and why it's built this way:
  - All API keys (Anthropic, Google, GitHub OAuth) live server-side in environment
    variables. The browser never sees them, never stores them, and never has to
    ask the person using the app for anything -- that's configured once by whoever
    deploys it, not per visitor.
  - The offline knowledge engine (kb_engine.py) has zero dependencies and zero
    network calls. It's the guaranteed fallback if no keys are configured, and it's
    what makes this genuinely offline-capable, not just "offline until the API key
    runs out."
  - GitHub sign-in is real OAuth (authorization-code flow), not a public-profile
    lookup -- the client secret is exchanged server-side, exactly the way GitHub's
    own docs require, and is never exposed to the browser.
"""
import os
import secrets
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, request, session, url_for, render_template

import kb_engine
import local_model

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CX = os.environ.get("GOOGLE_CX", "")
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")

DATA_DIR = Path(__file__).parent / "server"
STORE_PATH = DATA_DIR / "store.json"

SYSTEM_PROMPT = (
    "You are Zariya, a warm, concise bilingual Urdu/English assistant built as a "
    "privacy-first, offline-first platform for Urdu and other low-resource languages. "
    "Reply in whichever language the user writes in, mixing naturally if they mix."
)


# ---------------------------------------------------------------------------
# Tiny JSON-file store for notes/flashcards/sessions (per logged-in GitHub user
# if signed in, otherwise a shared local/anonymous bucket -- this is a uni-scale
# demo, not a multi-tenant production database).
# ---------------------------------------------------------------------------
def _load_store():
    if STORE_PATH.exists():
        import json
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    return {"users": {}}


def _save_store(store):
    import json
    STORE_PATH.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def _current_user_key():
    return session.get("github_login", "anonymous")


def _user_bucket(store):
    key = _current_user_key()
    store["users"].setdefault(key, {"sessions": [], "notes": [], "decks": []})
    return store["users"][key]


# ---------------------------------------------------------------------------
# Auth: real GitHub OAuth (authorization-code flow), client secret stays server-side
# ---------------------------------------------------------------------------
@app.route("/auth/github/login")
def github_login():
    if not GITHUB_CLIENT_ID:
        return jsonify({"error": "GitHub OAuth isn't configured on this server yet. "
                                  "Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in .env."}), 400
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    redirect_uri = f"{APP_BASE_URL}/auth/github/callback"
    authorize_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}&redirect_uri={redirect_uri}"
        f"&scope=read:user&state={state}"
    )
    return redirect(authorize_url)


@app.route("/auth/github/callback")
def github_callback():
    if request.args.get("state") != session.get("oauth_state"):
        return jsonify({"error": "State mismatch -- possible CSRF, or your session expired. Try signing in again."}), 400
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "GitHub didn't return an authorization code."}), 400

    token_res = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,  # server-side only, never sent to the browser
            "code": code,
            "redirect_uri": f"{APP_BASE_URL}/auth/github/callback",
        },
        timeout=10,
    )
    token_data = token_res.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return jsonify({"error": "GitHub token exchange failed", "details": token_data}), 400

    user_res = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        timeout=10,
    )
    profile = user_res.json()

    session["github_login"] = profile.get("login")
    session["github_name"] = profile.get("name") or profile.get("login")
    session["github_avatar"] = profile.get("avatar_url")
    session["github_bio"] = profile.get("bio") or ""
    return redirect("/")


@app.route("/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/me")
def me():
    if session.get("github_login"):
        return jsonify({
            "signedIn": True,
            "login": session["github_login"],
            "name": session.get("github_name"),
            "avatar": session.get("github_avatar"),
            "bio": session.get("github_bio"),
            "githubConfigured": bool(GITHUB_CLIENT_ID),
        })
    return jsonify({"signedIn": False, "githubConfigured": bool(GITHUB_CLIENT_ID)})


# ---------------------------------------------------------------------------
# Chat: Claude API (server-side key) -> offline knowledge engine.
# The person using the app is never asked for a key -- whoever deploys the
# server configures it once in .env.
# ---------------------------------------------------------------------------
@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True) or {}
    messages = body.get("messages", [])
    if not messages:
        return jsonify({"error": "No messages provided"}), 400

    used_real_model = False
    reply = None

    if ANTHROPIC_API_KEY:
        try:
            res = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 1000,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
                },
                timeout=30,
            )
            res.raise_for_status()
            data = res.json()
            text_block = next((b for b in data.get("content", []) if b.get("type") == "text"), None)
            reply = text_block["text"] if text_block else None
            used_real_model = reply is not None
        except Exception as e:
            app.logger.warning("Claude API call failed, falling back to offline: %s", e)

    if reply is None and local_model.is_available():
        local_reply = local_model.generate_reply(messages, SYSTEM_PROMPT)
        if local_reply:
            reply = local_reply
            used_real_model = True

    if reply is None:
        reply = kb_engine.offline_reply(messages)

    if used_real_model:
        last_user = next((m for m in reversed(messages) if m["role"] == "user"), None)
        if last_user and last_user.get("content", "").strip():
            kb_engine.remember_answer(last_user["content"], reply)

    return jsonify({"reply": reply, "usedRealModel": used_real_model})

@app.route("/api/feedback", methods=["POST"])
def feedback():
  body = request.get_json(force=True) or {}
  question = body.get("question", "")
  rating = body.get("rating", "")
  if rating not in ("up", "down"):
    return jsonify({"error": "rating must be 'up' or 'down'"}), 400
  updated = kb_engine.rate_learned_answer(question, rating)
  return jsonify({"ok": True, "updated": updated})
# ---------------------------------------------------------------------------
# Web search: Google Custom Search (server-side key)
# ---------------------------------------------------------------------------
@app.route("/api/search", methods=["POST"])
def web_search():
    body = request.get_json(force=True) or {}
    query = body.get("query", "").strip()
    if not query:
        return jsonify({"error": "No query provided"}), 400
    if not (GOOGLE_API_KEY and GOOGLE_CX):
        return jsonify({"error": "Web search isn't configured on this server. "
                                  "Set GOOGLE_API_KEY and GOOGLE_CX in .env."}), 400
    try:
        res = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={"key": GOOGLE_API_KEY, "cx": GOOGLE_CX, "q": query},
            timeout=15,
        )
        res.raise_for_status()
        data = res.json()
        items = [
            {"title": i.get("title"), "link": i.get("link"), "snippet": i.get("snippet", "")}
            for i in data.get("items", [])[:5]
        ]
        return jsonify({"results": items})
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": f"Google Search API error: {e}"}), 502
    except Exception as e:
        return jsonify({"error": f"Web search failed: {e}"}), 502


# ---------------------------------------------------------------------------
# Notes / Flashcards / Sessions -- simple per-user JSON storage
# ---------------------------------------------------------------------------
@app.route("/api/state", methods=["GET"])
def get_state():
    store = _load_store()
    bucket = _user_bucket(store)
    _save_store(store)
    return jsonify(bucket)


@app.route("/api/state", methods=["POST"])
def save_state():
    body = request.get_json(force=True) or {}
    store = _load_store()
    key = _current_user_key()
    store["users"][key] = {
        "sessions": body.get("sessions", []),
        "notes": body.get("notes", []),
        "decks": body.get("decks", []),
    }
    _save_store(store)
    return jsonify({"ok": True})


@app.route("/api/tools/<name>", methods=["POST"])
def run_tool(name):
    body = request.get_json(force=True) or {}
    messages = body.get("messages", [])
    if name == "summarize":
        return jsonify({"result": kb_engine.summarize_messages(messages)})
    if name == "keypoints":
        return jsonify({"result": kb_engine.key_points(messages)})
    if name == "translate":
        last_user = next((m for m in reversed(messages) if m["role"] == "user"), None)
        if not last_user:
            return jsonify({"result": ""})
        return jsonify({"result": kb_engine.translate_words(last_user["content"])})
    if name == "flashcards":
        return jsonify({"cards": kb_engine.flashcards_from_messages(messages)})
    return jsonify({"error": f"Unknown tool '{name}'"}), 404


@app.route("/api/kb-stats")
def kb_stats():
    return jsonify(kb_engine.knowledge_base_stats())


@app.route("/api/config")
def config():
    """Tells the frontend what's available server-side, without ever revealing keys."""
    return jsonify({
        "claudeConfigured": bool(ANTHROPIC_API_KEY),
        "searchConfigured": bool(GOOGLE_API_KEY and GOOGLE_CX),
        "githubConfigured": bool(GITHUB_CLIENT_ID),
        "localModelAvailable": local_model.is_available(),
        "localModelStatus": local_model.load_status(),
    })


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    DATA_DIR.mkdir(exist_ok=True)
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
