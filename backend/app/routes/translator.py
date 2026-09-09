import logging
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.language_detection import detect_language
from app.services.translation import translate_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/translator", tags=["translator"])

# In-memory room registry: { room_id: { websocket: target_lang_code } }
_rooms: dict[str, dict[WebSocket, str]] = {}


@router.websocket("/ws/{room_id}")
async def translator_websocket(websocket: WebSocket, room_id: str, target_lang: str):
    """
    Connect with: ws://host/translator/ws/{room_id}?target_lang=ur
    target_lang is the language THIS user wants to receive messages in.
    Two users join the same room_id to talk to each other.
    """
    await websocket.accept()

    if room_id not in _rooms:
        _rooms[room_id] = {}

    if len(_rooms[room_id]) >= 2:
        await websocket.send_json({
            "success": False,
            "error": "This room already has 2 participants."
        })
        await websocket.close()
        return

    _rooms[room_id][websocket] = target_lang
    logger.info(f"Client joined room '{room_id}' (target_lang={target_lang}). Room size: {len(_rooms[room_id])}")

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
                text = data.get("text", "")
            except json.JSONDecodeError:
                text = raw

            if not text or not text.strip():
                continue

            # Detect sender's language
            detected = detect_language(text)
            sender_lang = detected["language_code"]

            # Forward translated message to the OTHER participant(s) in the room
            for peer_ws, peer_target_lang in _rooms[room_id].items():
                if peer_ws is websocket:
                    continue  # don't echo back to sender

                try:
                    if sender_lang == peer_target_lang:
                        translated = text
                    else:
                        translated = translate_text(text, sender_lang, peer_target_lang)

                    await peer_ws.send_json({
                        "success": True,
                        "original_text": text,
                        "translated_text": translated,
                        "sender_detected_language": detected,
                    })
                except Exception as e:
                    logger.exception(f"Failed to translate/forward message in room '{room_id}': {e}")
                    await peer_ws.send_json({
                        "success": False,
                        "error": "Failed to translate incoming message."
                    })

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from room '{room_id}'.")
    finally:
        if room_id in _rooms and websocket in _rooms[room_id]:
            del _rooms[room_id][websocket]
        if room_id in _rooms and not _rooms[room_id]:
            del _rooms[room_id]