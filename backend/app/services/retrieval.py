import logging
import time as time_module

import numpy as np
import requests
from sentence_transformers import SentenceTransformer

from app.config import get_settings
from app.core.exceptions import RetrievalError

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Tavily configuration
# ---------------------------------------------------------------------------

TAVILY_API_URL = "https://api.tavily.com/search"

TAVILY_TIMEOUT_SECONDS = 15
TAVILY_MAX_RESULTS = 5

# Keep cache short enough for research freshness, while reducing API calls.
TAVILY_CACHE_TTL_SECONDS = 300  # 5 minutes

# Small retry count so the app does not hang for a long time.
MAX_TAVILY_ATTEMPTS = 2

_embedder = None

_tavily_cache: dict[str, tuple[float, list[dict]]] = {}


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

def _get_embedder():
    global _embedder

    if _embedder is None:
        logger.info("Loading sentence-transformer embedding model...")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Embedding model loaded.")

    return _embedder


# ---------------------------------------------------------------------------
# Text chunking
# ---------------------------------------------------------------------------

def _chunk_text(
    text: str,
    chunk_size: int = 300,
    overlap: int = 40,
) -> list[str]:
    """
    Split retrieved web content into overlapping chunks.

    Keeping this function compatible with the previous Wikipedia
    implementation means the downstream answer-generation pipeline
    receives the same type of context.
    """

    text = (text or "").strip()

    if not text:
        return []

    words = text.split()

    if len(words) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    step = max(1, chunk_size - overlap)

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end]).strip()

        if chunk:
            chunks.append(chunk)

        start += step

    return chunks


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _cache_key(query: str) -> str:
    return " ".join(query.lower().strip().split())


def _get_cached_results(query: str) -> list[dict] | None:
    key = _cache_key(query)

    cached = _tavily_cache.get(key)

    if cached is None:
        return None

    timestamp, results = cached

    if time_module.time() - timestamp > TAVILY_CACHE_TTL_SECONDS:
        del _tavily_cache[key]
        return None

    return results


def _set_cached_results(query: str, results: list[dict]) -> None:
    _tavily_cache[_cache_key(query)] = (
        time_module.time(),
        results,
    )


# ---------------------------------------------------------------------------
# Tavily API
# ---------------------------------------------------------------------------

def _get_tavily_api_key() -> str:
    api_key = settings.tavily_api_key

    if not api_key:
        raise RetrievalError(
            "TAVILY_API_KEY is not configured. "
            "Please add it to the .env file."
        )

    return api_key

def _search_tavily(
    query: str,
    max_results: int = TAVILY_MAX_RESULTS,
) -> list[dict]:
    """
    Search the web using Tavily.

    Tavily is used only as the retrieval/evidence layer.
    The existing answer-generation pipeline remains unchanged.
    """

    api_key = _get_tavily_api_key()

    cached = _get_cached_results(query)

    if cached is not None:
        logger.info("Using cached Tavily results for: %s", query)
        return cached

    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "topic": "general",
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
    }

    last_error = None

    for attempt in range(1, MAX_TAVILY_ATTEMPTS + 1):
        try:
            response = requests.post(
                TAVILY_API_URL,
                json=payload,
                timeout=TAVILY_TIMEOUT_SECONDS,
            )

            # Rate limit / temporary server errors.
            if response.status_code == 429 or response.status_code >= 500:
                last_error = RuntimeError(
                    f"Tavily returned HTTP {response.status_code}"
                )

                logger.warning(
                    "Tavily temporary error %s "
                    "(attempt %s/%s)",
                    response.status_code,
                    attempt,
                    MAX_TAVILY_ATTEMPTS,
                )

                if attempt < MAX_TAVILY_ATTEMPTS:
                    time_module.sleep(1.5)

                continue

            response.raise_for_status()

            data = response.json()

            raw_results = data.get("results", [])

            results = []

            for item in raw_results:
                title = (item.get("title") or "").strip()
                url = (item.get("url") or "").strip()

                # Tavily normally provides "content" as the relevant
                # search-result text/snippet.
                content = (item.get("content") or "").strip()

                if not content:
                    continue

                if not url:
                    continue

                results.append(
                    {
                        "title": title or "Web Source",
                        "content": content,
                        "url": url,
                    }
                )

            _set_cached_results(query, results)

            logger.info(
                "Tavily returned %d usable results for query: %s",
                len(results),
                query,
            )

            return results

        except requests.exceptions.Timeout as e:
            last_error = e

            logger.warning(
                "Tavily request timed out "
                "(attempt %s/%s)",
                attempt,
                MAX_TAVILY_ATTEMPTS,
            )

            if attempt < MAX_TAVILY_ATTEMPTS:
                time_module.sleep(1.0)

        except requests.exceptions.RequestException as e:
            last_error = e

            logger.warning(
                "Tavily request failed "
                "(attempt %s/%s): %s",
                attempt,
                MAX_TAVILY_ATTEMPTS,
                e,
            )

            if attempt < MAX_TAVILY_ATTEMPTS:
                time_module.sleep(1.0)

        except ValueError as e:
            # Invalid JSON response.
            last_error = e
            logger.exception("Invalid JSON returned by Tavily.")
            break

    logger.error("Tavily retrieval failed: %s", last_error)

    # IMPORTANT:
    # Do not crash the entire research endpoint because an external
    # retrieval provider temporarily failed.
    return []


# ---------------------------------------------------------------------------
# Similarity
# ---------------------------------------------------------------------------

def _cosine_similarity(
    query_vec: np.ndarray,
    chunk_vecs: np.ndarray,
) -> np.ndarray:
    query_norm = query_vec / (
        np.linalg.norm(query_vec) + 1e-10
    )

    chunk_norms = chunk_vecs / (
        np.linalg.norm(
            chunk_vecs,
            axis=1,
            keepdims=True,
        )
        + 1e-10
    )

    return chunk_norms @ query_norm


# ---------------------------------------------------------------------------
# Main retrieval function
# ---------------------------------------------------------------------------

def retrieve_relevant_context(
    query: str,
    top_k: int = 5,
) -> dict:
    """
    Retrieve relevant multilingual web context using Tavily.

    Returns the same structure expected by the existing
    answer-generation pipeline:

    {
        "chunks": [text, ...],
        "sources": [
            {
                "title": "...",
                "url": "..."
            }
        ],
        "chunk_details": [
            {
                "text": "...",
                "title": "...",
                "url": "..."
            }
        ]
    }
    """

    if not query or not query.strip():
        raise RetrievalError(
            "Cannot retrieve context for an empty query."
        )

    query = query.strip()

    # ------------------------------------------------------------------
    # 1. Tavily web retrieval
    # ------------------------------------------------------------------

    results = _search_tavily(
        query=query,
        max_results=TAVILY_MAX_RESULTS,
    )

    if not results:
        logger.warning(
            "No Tavily results found for query: %s",
            query,
        )

        return {
            "chunks": [],
            "sources": [],
            "chunk_details": [],
        }

    # ------------------------------------------------------------------
    # 2. Convert Tavily results into chunks
    # ------------------------------------------------------------------

    all_chunks: list[str] = []
    all_meta: list[dict] = []

    for result in results:
        content = result.get("content", "").strip()

        if not content:
            continue

        chunks = _chunk_text(content)

        for chunk in chunks:
            all_chunks.append(chunk)

            all_meta.append(
                {
                    "title": result.get("title", "Web Source"),
                    "url": result.get("url", ""),
                }
            )

    if not all_chunks:
        logger.warning(
            "Tavily returned results but no usable text "
            "was available for query: %s",
            query,
        )

        return {
            "chunks": [],
            "sources": [],
            "chunk_details": [],
        }

    # ------------------------------------------------------------------
    # 3. Existing semantic ranking
    # ------------------------------------------------------------------

    try:
        embedder = _get_embedder()

        chunk_vecs = embedder.encode(
            all_chunks,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        query_vec = embedder.encode(
            query,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        similarities = _cosine_similarity(
            query_vec,
            chunk_vecs,
        )

        # Do not request more chunks than actually exist.
        actual_top_k = min(
            max(1, top_k),
            len(all_chunks),
        )

        top_indices = np.argsort(
            similarities
        )[::-1][:actual_top_k]

        retrieved_chunks = [
            all_chunks[i]
            for i in top_indices
        ]

        chunk_details = [
            {
                "text": all_chunks[i],
                "title": all_meta[i]["title"],
                "url": all_meta[i]["url"],
            }
            for i in top_indices
        ]

        # ------------------------------------------------------------------
        # 4. Unique source list
        # ------------------------------------------------------------------

        sources = []
        seen_urls = set()

        for i in top_indices:
            meta = all_meta[i]
            url = meta["url"]

            if not url or url in seen_urls:
                continue

            sources.append(
                {
                    "title": meta["title"],
                    "url": url,
                }
            )

            seen_urls.add(url)

        logger.info(
            "Retrieved %d chunks from %d sources for: %s",
            len(retrieved_chunks),
            len(sources),
            query,
        )

        return {
            "chunks": retrieved_chunks,
            "sources": sources,
            "chunk_details": chunk_details,
        }

    except Exception as e:
        logger.exception(
            "Retrieval/embedding failed: %s",
            e,
        )

        raise RetrievalError(
            "Could not retrieve relevant information."
        ) from e