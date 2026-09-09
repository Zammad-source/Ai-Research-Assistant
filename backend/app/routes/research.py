import uuid
import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.services.language_detection import detect_language
from app.services.translation import translate_text
from app.services.retrieval import retrieve_relevant_context
from app.services.answer_generation import generate_answer, rewrite_query_with_history
from app.services import memory
from app.core.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


class LangTestRequest(BaseModel):
    text: str


@router.post("/test-language-detection")
async def test_language_detection(payload: LangTestRequest):
    result = detect_language(payload.text)
    return {"success": True, "data": result}


class TranslateTestRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str


@router.post("/test-translation")
async def test_translation(payload: TranslateTestRequest):
    result = translate_text(payload.text, payload.source_lang, payload.target_lang)
    return {"success": True, "translated_text": result}


class RetrievalTestRequest(BaseModel):
    query: str


@router.post("/test-retrieval")
async def test_retrieval(payload: RetrievalTestRequest):
    result = retrieve_relevant_context(payload.query)
    return {"success": True, "data": result}


class AnswerTestRequest(BaseModel):
    query: str


@router.post("/test-answer-generation")
async def test_answer_generation(payload: AnswerTestRequest):
    retrieval_result = retrieve_relevant_context(payload.query)
    answer = generate_answer(payload.query, retrieval_result["chunks"])
    return {
        "success": True,
        "answer": answer,
        "sources": retrieval_result["sources"],
    }


class ResearchRequest(BaseModel):
    text: str
    session_id: str | None = None


@router.post("")
@limiter.limit("15/minute")
async def research(request: Request, payload: ResearchRequest):
    session_id = payload.session_id or str(uuid.uuid4())

    detected = detect_language(payload.text)
    source_lang = detected["language_code"]

    if source_lang == "en":
        english_query = payload.text
    else:
        english_query = translate_text(payload.text, source_lang, "en")

    history = memory.get_history(session_id)
    standalone_query = rewrite_query_with_history(english_query, history)
    retrieval_result = retrieve_relevant_context(standalone_query)
    english_answer = generate_answer(english_query, retrieval_result["chunks"], history)

    if source_lang == "en":
        final_answer = english_answer
    else:
        final_answer = translate_text(english_answer, "en", source_lang)

    memory.add_turn(session_id, "user", english_query)
    memory.add_turn(session_id, "assistant", english_answer)

    return {
        "success": True,
        "session_id": session_id,
        "detected_language": detected,
        "answer": final_answer,
        "sources": retrieval_result["sources"],
    }