"""
Zariya – Memory Manager
Handles persistent chat history, session management, and search.
"""

from __future__ import annotations
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"
HISTORY_FILE = DATA_DIR / "chat_history.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_all() -> list[dict]:
    """Load all chat sessions from disk."""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Support both old flat format and new sessions format
            if isinstance(data, list):
                if data and "session_id" not in data[0]:
                    # Old format — migrate to sessions
                    return [_migrate_old_format(data)]
                return data
            return []
    except (json.JSONDecodeError, Exception):
        return []


def _save_all(sessions: list[dict]) -> None:
    """Persist all sessions to disk."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)


def _migrate_old_format(old_data: list[dict]) -> dict:
    """Convert legacy flat chat list into a session object."""
    messages = []
    for entry in old_data:
        messages.append({"role": "user", "content": entry.get("user", "")})
        messages.append({"role": "assistant", "content": entry.get("bot", "")})
    return {
        "session_id": str(uuid.uuid4()),
        "title": "Previous conversation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "messages": messages,
    }


class MemoryManager:
    """Manages chat sessions and message history."""

    def __init__(self):
        self._sessions: list[dict] = _load_all()

    def _find_session(self, session_id: str) -> Optional[dict]:
        for s in self._sessions:
            if s["session_id"] == session_id:
                return s
        return None

    def new_session(self, title: Optional[str] = None) -> str:
        """Create a new chat session and return its ID."""
        session_id = str(uuid.uuid4())
        session = {
            "session_id": session_id,
            "title": title or "New conversation",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": [],
        }
        self._sessions.append(session)
        _save_all(self._sessions)
        return session_id

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message to a session."""
        session = self._find_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        session["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        session["updated_at"] = datetime.now().isoformat()

        # Auto-title from first user message
        if (
            role == "user"
            and session["title"] in ("New conversation",)
            and content.strip()
        ):
            session["title"] = content.strip()[:60]

        _save_all(self._sessions)

    def get_messages(self, session_id: str) -> list[dict]:
        """Return all messages for a session (role + content only)."""
        session = self._find_session(session_id)
        if session is None:
            return []
        return [{"role": m["role"], "content": m["content"]} for m in session["messages"]]

    def get_sessions(self) -> list[dict]:
        """Return sessions sorted newest first."""
        return sorted(
            self._sessions,
            key=lambda s: s.get("updated_at", ""),
            reverse=True,
        )

    def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID."""
        before = len(self._sessions)
        self._sessions = [s for s in self._sessions if s["session_id"] != session_id]
        if len(self._sessions) < before:
            _save_all(self._sessions)
            return True
        return False

    def clear_all(self) -> None:
        """Delete all sessions."""
        self._sessions = []
        _save_all(self._sessions)

    def rename_session(self, session_id: str, new_title: str) -> bool:
        session = self._find_session(session_id)
        if session:
            session["title"] = new_title[:80]
            _save_all(self._sessions)
            return True
        return False

    def search(self, query: str) -> list[dict]:
        """Full-text search across all sessions."""
        q = query.lower()
        results = []
        for session in self._sessions:
            for msg in session["messages"]:
                if q in msg["content"].lower():
                    results.append({
                        "session_id": session["session_id"],
                        "session_title": session["title"],
                        "role": msg["role"],
                        "snippet": msg["content"][:120],
                        "timestamp": msg.get("timestamp", ""),
                    })
        return results

    def export_session(self, session_id: str) -> Optional[str]:
        """Export a session as formatted text."""
        session = self._find_session(session_id)
        if not session:
            return None
        lines = [f"# {session['title']}", f"Date: {session['created_at'][:10]}", ""]
        for msg in session["messages"]:
            prefix = "You" if msg["role"] == "user" else "Zariya"
            lines.append(f"**{prefix}:** {msg['content']}")
            lines.append("")
        return "\n".join(lines)

    def get_stats(self) -> dict:
        total_msg = sum(len(s["messages"]) for s in self._sessions)
        return {
            "sessions": len(self._sessions),
            "messages": total_msg,
            "file_size_kb": round(HISTORY_FILE.stat().st_size / 1024, 1) if HISTORY_FILE.exists() else 0,
        }


# Module-level singleton
_manager: Optional[MemoryManager] = None


def get_memory() -> MemoryManager:
    global _manager
    if _manager is None:
        _manager = MemoryManager()
    return _manager
