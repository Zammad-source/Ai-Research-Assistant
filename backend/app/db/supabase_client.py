import logging
from supabase import create_client, Client

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_supabase_client: Client | None = None


def get_supabase_client() -> Client | None:
    """
    Returns a cached Supabase client. Returns None (instead of raising)
    if initialization fails, so the app can keep working without
    persistence rather than crashing.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    try:
        _supabase_client = create_client(settings.supabase_url, settings.supabase_key)
        logger.info("Supabase client initialized.")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None


def save_chat_turn(session_id: str, role: str, content: str) -> bool:
    """
    Persists a single chat turn to Supabase. Never raises — if this
    fails, we log it and move on, since chat history persistence is
    a nice-to-have, not something that should ever break a live demo.
    """
    client = get_supabase_client()
    if client is None:
        return False

    try:
        client.table("chat_history").insert({
            "session_id": session_id,
            "role": role,
            "content": content,
        }).execute()
        return True
    except Exception as e:
        logger.warning(f"Failed to save chat turn to Supabase: {e}")
        return False


def get_chat_history_from_db(session_id: str, limit: int = 20) -> list[dict]:
    """
    Fetches chat history for a session from Supabase (used as a backup /
    for displaying history across server restarts, e.g. in the frontend).
    Returns an empty list on failure instead of raising.
    """
    client = get_supabase_client()
    if client is None:
        return []

    try:
        response = (
            client.table("chat_history")
            .select("role, content, created_at")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.warning(f"Failed to fetch chat history from Supabase: {e}")
        return []