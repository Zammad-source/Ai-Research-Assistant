import logging
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.language_detection import detect_language
from app.services.translation import translate_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/translator", tags=["translator"])

# The frontend connects to /ws/translator/{room_id}, while the original
# Postman/manual client used /translator/ws/{room_id}. Both are registered
# on the same handler so neither client breaks.
frontend_router = APIRouter(tags=["translator"])

# In-memory room registry: { room_id: { websocket: connection metadata } }
_rooms: dict[str, dict[WebSocket, dict]] = {}

# Frontend speaks long language names ("urdu"), the backend speaks short
# codes ("ur"). Normalize on the way in and out.
LANGUAGE_NAME_TO_CODE = {
    "urdu": "ur",
    "roman urdu": "ur-roman",
    "ur-roman": "ur-roman",
    "punjabi": "pa",
    "sindhi": "sd",
    "pashto": "ps",
    "english": "en",
    "ur": "ur",
    "pa": "pa",
    "sd": "sd",
    "ps": "ps",
    "en": "en",
}

LANGUAGE_CODE_TO_NAME = {
    "ur": "urdu",
    "ur-roman": "urdu",
    "pa": "punjabi",
    "sd": "sindhi",
    "ps": "pashto",
    "en": "english",
}

# Languages the translation pipeline can actually handle. Anything else
# (langdetect can return French, Croatian, Indonesian...) falls back to
# English rather than failing the whole message.
SUPPORTED_CODES = {"ur", "ur-roman", "pa", "sd", "ps", "en"}


def _normalize_code(value: str | None, default: str = "en") -> str:
    if not value:
        return default
    key = str(value).strip().lower()
    return LANGUAGE_NAME_TO_CODE.get(key, key)


def _to_frontend_name(code: str | None) -> str:
    if not code:
        return "english"
    return LANGUAGE_CODE_TO_NAME.get(code, code)


def _extract_text_and_languages(raw: str) -> tuple[str, str | None, str | None]:
    """
    Accepts every shape clients have used for this endpoint:
      - plain text:                      "hello"
      - {text: "hello"}
      - {type: "message", original_text: "hello", translated_language: "english"}
    Returns (text, original_language, target_language) with languages
    normalized to backend codes (or None when not supplied).
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw, None, None

    if not isinstance(data, dict):
        return str(data), None, None

    text = data.get("text") or data.get("original_text") or ""
    original = data.get("original_language") or data.get("source_language")
    target = (
        data.get("translated_language")
        or data.get("target_language")
        or data.get("target_lang")
    )

    return (
        str(text),
        _normalize_code(original, "en") if original else None,
        _normalize_code(target, "en") if target else None,
    )


async def _handle_translator_socket(websocket: WebSocket, room_id: str, target_lang: str | None):
    """
    Connect with either of:
      ws://host/translator/ws/{room_id}?target_lang=ur
      ws://host/ws/translator/{room_id}
    Two users join the same room_id to talk to each other. The language a
    participant wants to receive can be pinned per connection with
    target_lang, or supplied per message via "translated_language".
    """
    await websocket.accept()

    if target_lang:
        target_lang = _normalize_code(target_lang)

    if room_id not in _rooms:
        _rooms[room_id] = {}

    if len(_rooms[room_id]) >= 2:
        await websocket.send_json({
            "type": "error",
            "code": "room_full",
            "message": "This room already has 2 participants.",
            "success": False,
        })
        await websocket.close()
        return

    _rooms[room_id][websocket] = {"target_lang": target_lang}
    logger.info(
        f"Client joined room '{room_id}' (target_lang={target_lang}). "
        f"Room size: {len(_rooms[room_id])}"
    )

    await websocket.send_json({
        "type": "connection",
        "status": "connected",
        "participant": "self",
    })

    try:
        while True:
            raw = await websocket.receive_text()

            text, original_lang, message_target = _extract_text_and_languages(raw)

            if not text or not text.strip():
                continue

            # Remember a per-message target language for this connection so
            # later messages from the same client can omit it.
            if message_target:
                _rooms[room_id][websocket]["target_lang"] = message_target
            message_target = message_target or target_lang

            # Detect sender's language (honour an explicit hint if given).
            if original_lang:
                detected = {
                    "language_code": original_lang,
                    "language_name": _to_frontend_name(original_lang),
                    "confidence_method": "client_hint",
                }
            else:
                try:
                    detected = detect_language(text)
                except Exception:
                    detected = {
                        "language_code": "en",
                        "language_name": "English",
                        "confidence_method": "fallback",
                    }

            sender_lang = detected["language_code"]

            # Languages the pipeline can't translate would otherwise fail
            # every message — treat them as English.
            if sender_lang not in SUPPORTED_CODES:
                logger.info(
                    f"Unsupported detected language '{sender_lang}', treating as English."
                )
                sender_lang = "en"

            # Forward translated message to the OTHER participant(s) in the room
            for peer_ws, peer_meta in list(_rooms.get(room_id, {}).items()):
                if peer_ws is websocket:
                    continue  # don't echo back to sender

                peer_target = message_target or peer_meta.get("target_lang") or "en"

                if peer_target not in SUPPORTED_CODES:
                    peer_target = "en"

                try:
                    if sender_lang == peer_target:
                        translated = text
                    else:
                        translated = translate_text(text, sender_lang, peer_target)

                    await peer_ws.send_json({
                        "type": "message",
                        "message_id": str(uuid.uuid4()),
                        "original_text": text,
                        "translated_text": translated,
                        "original_language": _to_frontend_name(sender_lang),
                        "translated_language": _to_frontend_name(peer_target),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        # Legacy fields kept for the original client.
                        "success": True,
                        "sender_detected_language": detected,
                    })
                except Exception as e:
                    logger.exception(
                        f"Failed to translate/forward message in room '{room_id}': {e}"
                    )
                    try:
                        await peer_ws.send_json({
                            "type": "error",
                            "code": "translation_failed",
                            "message": "Failed to translate incoming message.",
                            "success": False,
                        })
                    except Exception:
                        # Peer already gone — nothing else to do.
                        pass

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from room '{room_id}'.")
    finally:
        if room_id in _rooms and websocket in _rooms[room_id]:
            del _rooms[room_id][websocket]
        if room_id in _rooms and not _rooms[room_id]:
            del _rooms[room_id]


@router.websocket("/ws/{room_id}")
async def translator_websocket(websocket: WebSocket, room_id: str, target_lang: str = None):
    await _handle_translator_socket(websocket, room_id, target_lang)


@frontend_router.websocket("/ws/translator/{room_id}")
async def translator_websocket_frontend(websocket: WebSocket, room_id: str, target_lang: str = None):
    await _handle_translator_socket(websocket, room_id, target_lang)