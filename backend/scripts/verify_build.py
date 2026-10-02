"""
Verify the backend imports and works with ONLY the packages listed in
requirements.txt.

Run this before every deploy. It blocks torch, transformers,
sentence-transformers and numpy at import time, reproducing the Railway
container exactly. If this passes, the Railway build cannot fail on a missing
dependency.

    python scripts/verify_build.py
"""

import os
import sys
from pathlib import Path

# Allow running as `python scripts/verify_build.py` from anywhere.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# Packages that are NOT in requirements.txt (they need torch, which does not
# fit on Railway's free 512 MB container). Blocking them proves the app has no
# hard dependency on any of it.
BLOCKED = {
    "torch", "transformers", "sentence_transformers", "numpy",
    "chromadb", "wikipedia", "tenacity",
}


class Blocker:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in BLOCKED:
            raise ImportError(f"blocked by verify_build: {name}")
        return None


sys.meta_path.insert(0, Blocker())

# Settings requires these at import time. Values here are never used for real
# calls -- this script only checks import wiring.
os.environ.setdefault("GROQ_API_KEY", "verify-build-placeholder")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "verify-build-placeholder")
os.environ.setdefault("ELEVENLABS_API_KEY", "verify-build-placeholder")
os.environ.setdefault("TAVILY_API_KEY", "verify-build-placeholder")
os.environ.setdefault("ENVIRONMENT", "production")
os.environ.setdefault("PORT", "8000")

failures = []


def check(label, fn):
    try:
        result = fn()
    except Exception as exc:  # noqa: BLE001 - report, do not abort
        print(f"  FAIL  {label}: {type(exc).__name__}: {exc}")
        failures.append(label)
        return None
    print(f"  ok    {label}")
    return result


def _require(collection, item):
    """Raise if item is absent, so check() reports it as a failure."""
    if item not in collection:
        raise AssertionError(f"{item!r} is not registered")
    return item


print("Verifying the backend against a Railway-like environment\n")

# --- 1. The app imports at all -------------------------------------------
print("[1] importing the application")
main = check("import app.main", lambda: __import__("app.main", fromlist=["app"]))
if main is None:
    print("\nFAILED: the app cannot even import.")
    raise SystemExit(1)
print(f"      title = {main.app.title}")

# --- 2. Every route the frontend calls is mounted ------------------------
print("\n[2] checking routes")
paths = {r.path for r in main.app.routes}
websocket_paths = {
    r.path for r in main.app.routes
    if type(r).__name__ == "APIWebSocketRoute"
}

for required in ("/health", "/api/research/query", "/api/voice/speech",
                 "/api/voice/transcribe"):
    check(f"route {required}", lambda r=required: _require(paths, r))

for required in ("/ws/translator/{room_id}",):
    check(f"websocket {required}", lambda r=required: _require(websocket_paths, r))

# --- 3. Retrieval works with no torch/numpy ------------------------------
print("\n[3] retrieval without numpy/torch")
import app.services.retrieval as retrieval  # noqa: E402


def _retrieval_check():
    if retrieval._get_embedder() is not None:
        raise AssertionError("embedder should be unavailable in this check")
    retrieval._search_tavily = lambda query, max_results=5: [
        {"title": "Cities of Pakistan", "url": "https://example.com/a",
         "content": "Karachi is the largest city of Pakistan and its economic capital."},
        {"title": "Capitals", "url": "https://example.com/b",
         "content": "Islamabad is the capital city of Pakistan, located in the north."},
        {"title": "Rome", "url": "https://example.com/c",
         "content": "The history of the Roman Empire spans centuries of Mediterranean rule."},
    ]
    retrieval._set_cached_results = lambda query, results: None

    result = retrieval.retrieve_relevant_context(
        "what is the capital of pakistan", top_k=2
    )
    assert len(result["chunks"]) == 2, "expected 2 ranked chunks"
    assert len(result["sources"]) == 2, "expected 2 sources"
    assert len(result["chunk_details"]) == 2, "expected chunk_details"
    assert "Islamabad" in result["chunks"][0], (
        "lexical ranking should surface the capital-of-Pakistan chunk first, "
        f"got: {result['chunks'][0][:60]!r}"
    )
    return result


result = check("retrieve_relevant_context", _retrieval_check)
if result:
    print(f"      top chunk = {result['chunks'][0][:60]!r}")

print()
if failures:
    print(f"FAILED ({len(failures)} problem(s)):")
    for f in failures:
        print("  -", f)
    raise SystemExit(1)

print("PASSED - the app will start on Railway with requirements.txt only.")