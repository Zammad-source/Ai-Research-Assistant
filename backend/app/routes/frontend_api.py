import os
import uuid
import logging
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.language_detection import detect_language
from app.services.translation import translate_text
from app.services.retrieval import retrieve_relevant_context
from app.services.answer_generation import generate_answer_with_citations, rewrite_query_with_history
from app.services.speech_to_text import transcribe_audio_with_language
from app.services.text_to_speech import generate_speech
from app.services import memory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["frontend"])


# ---------- /api/research/query ----------

class ResearchQueryRequest(BaseModel):
    conversation_id: str | None = None
    query: str


def _build_numbered_sources(chunk_details: list[dict]) -> list[dict]:
    seen_urls = {}
    order = []
    for cd in chunk_details:
        url = cd["url"]
        if url not in seen_urls:
            seen_urls[url] = {"title": cd["title"], "url": url, "texts": [cd["text"]]}
            order.append(url)
        else:
            seen_urls[url]["texts"].append(cd["text"])

    numbered = []
    for i, url in enumerate(order, start=1):
        entry = seen_urls[url]
        numbered.append({
            "number": i,
            "title": entry["title"],
            "url": url,
            "text": "\n".join(entry["texts"]),
        })
    return numbered


@router.post("/research/query")
async def research_query(payload: ResearchQueryRequest):
    conversation_id = payload.conversation_id or str(uuid.uuid4())

    detected = detect_language(payload.query)
    source_lang = detected["language_code"]

    if source_lang == "en":
        english_query = payload.query
    else:
        english_query = translate_text(payload.query, source_lang, "en")

    history = memory.get_history(conversation_id)
    standalone_query = rewrite_query_with_history(english_query, history)

    retrieval_result = retrieve_relevant_context(standalone_query)
    numbered_sources = _build_numbered_sources(retrieval_result["chunk_details"])

    english_answer = generate_answer_with_citations(english_query, numbered_sources, history)

    if source_lang == "en":
        final_answer = english_answer
    else:
        final_answer = translate_text(english_answer, "en", source_lang)

    memory.add_turn(conversation_id, "user", english_query)
    memory.add_turn(conversation_id, "assistant", english_answer)

    sources_out = []
    for s in numbered_sources:
        snippet = s["text"][:200] + ("..." if len(s["text"]) > 200 else "")
        sources_out.append({
            "id": f"s{s['number']}",
            "title": s["title"],
            "url": s["url"],
            "domain": urlparse(s["url"]).netloc,
            "snippet": snippet,
        })

    return {
        "conversation_id": conversation_id,
        "message_id": str(uuid.uuid4()),
        "answer": final_answer,
        "sources": sources_out,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------- /api/voice/transcribe ----------

@router.post("/voice/transcribe")
async def voice_transcribe(audio: UploadFile = File(...)):
    suffix = os.path.splitext(audio.filename or "recording.webm")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = transcribe_audio_with_language(tmp_path)
        return {"text": result["text"], "language": result.get("language")}
    finally:
        os.remove(tmp_path)


# ---------- /api/voice/speech ----------

class VoiceSpeechRequest(BaseModel):
    text: str


@router.post("/voice/speech")
async def voice_speech(payload: VoiceSpeechRequest):
    output_path = generate_speech(payload.text)
    return FileResponse(output_path, media_type="audio/mpeg")