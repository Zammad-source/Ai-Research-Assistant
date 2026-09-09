import logging

from groq import Groq

from app.config import get_settings
from app.core.exceptions import AnswerGenerationError

logger = logging.getLogger(__name__)
settings = get_settings()

_groq_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.groq_api_key)
    return _groq_client


def generate_answer(query: str, chunks: list[str], history: list[dict] | None = None) -> str:
    if not query or not query.strip():
        raise AnswerGenerationError("Cannot generate an answer for an empty query.")

    if not chunks:
        return (
            "I couldn't find reliable information on this topic to answer "
            "your question accurately."
        )

    context = "\n\n---\n\n".join(chunks)

    system_prompt = (
        "You are a factual research assistant. Answer the user's question "
        "using ONLY the information in the provided context. Do not use "
        "outside knowledge. If the context does not contain enough "
        "information to answer, say so honestly instead of guessing. "
        "Keep the answer clear, well-organized, and directly relevant to "
        "the question. Do not mention 'the context' explicitly in your "
        "answer — write as if you simply know this information. Use the "
        "conversation history only to understand follow-up questions, not "
        "as a source of facts."
    )

    messages = [{"role": "system", "content": system_prompt}]

    if history:
        messages.extend(history)

    user_prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
    messages.append({"role": "user", "content": user_prompt})

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            max_tokens=2048,
            temperature=0.2,
            extra_body={"reasoning_effort": "low"},
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.exception(f"Answer generation failed: {e}")
        raise AnswerGenerationError("Could not generate an answer. Please try again.")


def rewrite_query_with_history(query: str, history: list[dict] | None) -> str:
    if not history:
        return query

    try:
        client = _get_groq_client()
        history_text = "\n".join(
            f"{turn['role']}: {turn['content']}" for turn in history[-4:]
        )
        prompt = (
            "Given this conversation history and a follow-up question, "
            "rewrite the follow-up question as a standalone question that "
            "makes sense without the history. Resolve pronouns like 'it', "
            "'its', 'this', 'that' to the actual subject. "
            "Return ONLY the rewritten question, nothing else.\n\n"
            f"History:\n{history_text}\n\n"
            f"Follow-up question: {query}\n\n"
            f"Standalone question:"
        )
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.0,
            extra_body={"reasoning_effort": "low"},
        )
        rewritten = response.choices[0].message.content.strip()
        return rewritten if rewritten else query
    except Exception as e:
        logger.warning(f"Query rewriting failed, using original query: {e}")
        return query


def generate_answer_with_citations(
    query: str, numbered_sources: list[dict], history: list[dict] | None = None
) -> str:
    """
    Like generate_answer, but instructs the model to cite sources inline
    as [1], [2], ... matching the position of numbered_sources. Used by
    the frontend-facing /api/research/query endpoint.

    numbered_sources: [{"number": 1, "title": ..., "url": ..., "text": ...}, ...]
    """
    if not query or not query.strip():
        raise AnswerGenerationError("Cannot generate an answer for an empty query.")

    if not numbered_sources:
        return (
            "I couldn't find reliable information on this topic to answer "
            "your question accurately."
        )

    context_blocks = "\n\n".join(
        f"[{s['number']}] {s['title']}\n{s['text']}" for s in numbered_sources
    )

    system_prompt = (
        "You are a factual research assistant. Answer the user's question "
        "using ONLY the information in the numbered sources below. Do not "
        "use outside knowledge. Cite claims inline using the matching "
        "source number in square brackets, e.g. 'RAG combines retrieval "
        "and generation [1].' Use a citation for every factual claim you "
        "make, right after the sentence it supports. If the sources don't "
        "contain enough information, say so honestly. Keep the answer "
        "clear and well-organized. Use the conversation history only to "
        "understand follow-up questions, not as a source of facts."
    )

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)

    user_prompt = f"Sources:\n{context_blocks}\n\nQuestion: {query}\n\nAnswer:"
    messages.append({"role": "user", "content": user_prompt})

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            max_tokens=2048,
            temperature=0.2,
            extra_body={"reasoning_effort": "low"},
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.exception(f"Answer generation (citations) failed: {e}")
        raise AnswerGenerationError("Could not generate an answer. Please try again.")