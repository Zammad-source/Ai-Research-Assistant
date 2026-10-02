import logging
import re
import time as time_module

import requests

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
_embedder_unavailable = False

_tavily_cache: dict[str, tuple[float, list[dict]]] = {}


# ---------------------------------------------------------------------------
# Embeddings (optional)
# ---------------------------------------------------------------------------
#
# Semantic ranking needs sentence-transformers, which drags in torch (~800 MB)
# and a ~90 MB model. That does not fit on free hosting (Railway's free
# container has 512 MB RAM), and it is not in requirements.txt by design.
#
# So the import is optional: when the package is present we rank with real
# embeddings, and when it is absent we fall back to the lexical ranker below.
# Either way the endpoint returns ranked chunks -- the frontend never has to
# know which one ran.

def _get_embedder():
    """Return a SentenceTransformer, or None when it is not installed."""
    global _embedder, _embedder_unavailable

    if _embedder is not None or _embedder_unavailable:
        return _embedder

    try:
        from sentence_transformers import SentenceTransformer

        logger.info("Loading sentence-transformer embedding model...")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Embedding model loaded.")
        return _embedder

    except Exception as e:
        # Log once, not on every query.
        _embedder_unavailable = True
        logger.warning(
            "sentence-transformers unavailable (%s); "
            "falling back to lexical chunk ranking.",
            e,
        )
        return None


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

# Words too common to say anything about relevance.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "of", "at", "by", "for",
    "with", "about", "into", "to", "from", "in", "on", "is", "are", "was",
    "were", "be", "been", "being", "it", "its", "this", "that", "these",
    "those", "as", "than", "then", "there", "here", "what", "which", "who",
    "whom", "how", "why", "when", "where", "do", "does", "did", "can",
    "could", "will", "would", "should", "not", "no", "yes", "you", "your",
    "i", "me", "my", "we", "our", "they", "them", "their", "he", "she",
    "his", "her", "have", "has", "had", "so", "such", "also", "more",
    "most", "some", "any", "all", "both", "each", "very", "just", "up",
    "out", "over", "under", "again", "tell", "give", "give", "know",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Weight of the phrase (bigram) signal relative to the bag-of-words signal.
# Phrases are what separate "Karachi is the largest city of Pakistan" from
# "Islamabad is the capital of Pakistan" -- both contain the same query terms,
# so unigrams alone tie.
_BIGRAM_WEIGHT = 1.5


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokens, stopwords and 1-char noise removed."""
    return [
        t for t in _TOKEN_RE.findall((text or "").lower())
        if len(t) > 1 and t not in _STOPWORDS
    ]


def _bigrams(text: str) -> set[tuple[str, str]]:
    """
    Adjacent word pairs, built from the RAW token stream.

    Stopwords are deliberately kept here: the phrase "capital of pakistan"
    only exists as adjacent pairs in raw text, and stripping "of" would
    destroy it.
    """
    tokens = _TOKEN_RE.findall((text or "").lower())
    return {(tokens[i], tokens[i + 1]) for i in range(len(tokens) - 1)}


def _lexical_rank(query: str, chunks: list[str], top_k: int) -> list[int]:
    """
    Rank chunk indices by how well they match the query.

    Stands in for embedding similarity when torch is not installed. The score
    has three parts:

      coverage  what fraction of the query's content words a chunk covers
      density   matched terms per sqrt(chunk length), so a long chunk cannot
                win on volume alone
      phrases   fraction of the query's word pairs that appear adjacently

    Ties keep Tavily's original relevance order.
    """
    q_terms = set(_tokenize(query))
    if not q_terms or not chunks:
        return list(range(len(chunks)))[:top_k]

    q_bigrams = _bigrams(query)
    total_bigrams = len(q_bigrams)

    scored: list[tuple[float, int]] = []
    for index, chunk in enumerate(chunks):
        c_terms = _tokenize(chunk)

        if not c_terms:
            scored.append((0.0, index))
            continue

        overlap = q_terms & set(c_terms)
        if not overlap:
            scored.append((0.0, index))
            continue

        coverage = len(overlap) / len(q_terms)
        density = len(overlap) / (len(c_terms) ** 0.5)

        phrase_score = 0.0
        if total_bigrams:
            matched = len(q_bigrams & _bigrams(chunk))
            phrase_score = _BIGRAM_WEIGHT * (matched / total_bigrams)

        scored.append((coverage + 0.5 * density + phrase_score, index))

    # Sort by score descending, then by original position ascending.
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [index for _, index in scored[:top_k]]


def _cosine_similarity(query_vec, chunk_vecs):
    """Cosine similarity of one query vector against a matrix of chunk vectors."""
    import numpy as np

    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)

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
    # 3. Semantic ranking, with a lexical fallback
    # ------------------------------------------------------------------

    # Do not request more chunks than actually exist.
    actual_top_k = min(
        max(1, top_k),
        len(all_chunks),
    )

    embedder = _get_embedder()

    top_indices: list[int] | None = None

    if embedder is not None:
        try:
            import numpy as np

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

            top_indices = list(
                np.argsort(similarities)[::-1][:actual_top_k]
            )

        except Exception as e:
            # A failing embedder must not fail the request -- ranking is a
            # quality improvement, not a correctness requirement.
            logger.exception("Embedding ranking failed: %s", e)
            top_indices = None

    if top_indices is None:
        top_indices = _lexical_rank(query, all_chunks, actual_top_k)

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