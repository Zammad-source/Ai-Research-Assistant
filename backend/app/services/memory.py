import logging
from collections import defaultdict
from threading import Lock

from app.db.supabase_client import save_chat_turn

logger = logging.getLogger(__name__)

_sessions = defaultdict(list)
_lock = Lock()

MAX_HISTORY_TURNS = 6


def add_turn(session_id: str, role: str, content: str):
    with _lock:
        _sessions[session_id].append({"role": role, "content": content})
        max_entries = MAX_HISTORY_TURNS * 2
        if len(_sessions[session_id]) > max_entries:
            _sessions[session_id] = _sessions[session_id][-max_entries:]

    # Persist to Supabase too (best-effort, never blocks/breaks the main flow)
    save_chat_turn(session_id, role, content)


def get_history(session_id: str) -> list[dict]:
    with _lock:
        return list(_sessions.get(session_id, []))


def clear_session(session_id: str):
    with _lock:
        _sessions.pop(session_id, None)