"""
Boot the backend the way Railway does and exercise the endpoints the Vercel
frontend calls. Verifies the healthcheck path, the CORS policy and routing
without spending a single API call.

    python scripts/smoke_test.py
"""

import os
import sys
import threading
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# Placeholder credentials: this test never reaches a real provider.
os.environ.setdefault("GROQ_API_KEY", "smoke-test-placeholder")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "smoke-test-placeholder")
os.environ.setdefault("ELEVENLABS_API_KEY", "smoke-test-placeholder")
os.environ.setdefault("TAVILY_API_KEY", "smoke-test-placeholder")

TEST_ORIGIN = "https://omnivoice-frontend.vercel.app"

# Mirror a real Railway service.
os.environ["ENVIRONMENT"] = "production"
os.environ["RAILWAY_ENVIRONMENT"] = "production"
os.environ["CORS_ORIGINS"] = TEST_ORIGIN

PORT = int(os.environ.get("SMOKE_TEST_PORT", "8123"))

import uvicorn  # noqa: E402

server = uvicorn.Server(uvicorn.Config(
    "app.main:app",
    host="0.0.0.0",
    port=PORT,
    log_level="warning",
))

thread = threading.Thread(target=server.run, daemon=True)
thread.start()

for _ in range(100):
    if server.started:
        break
    time.sleep(0.1)
else:
    print("FAILED: server did not start in 10s")
    raise SystemExit(1)

import httpx  # noqa: E402

base = f"http://127.0.0.1:{PORT}"
failures = []

print(f"smoke testing {base}\n")

with httpx.Client(timeout=30) as client:
    # Railway's healthcheckPath.
    r = client.get(f"{base}/health")
    if r.status_code == 200 and r.json().get("status") == "ok":
        print(f"  ok    GET /health -> 200 {r.text}")
    else:
        failures.append(f"GET /health -> {r.status_code} {r.text[:120]}")
        print(f"  FAIL  GET /health -> {r.status_code}")

    # Preflight from the real frontend origin: must be allowed.
    r = client.options(
        f"{base}/api/research/query",
        headers={"Origin": TEST_ORIGIN, "Access-Control-Request-Method": "POST"},
    )
    allow = r.headers.get("access-control-allow-origin", "<none>")
    if allow == TEST_ORIGIN:
        print(f"  ok    CORS allows {TEST_ORIGIN}")
    else:
        failures.append(f"CORS preflight returned allow-origin={allow}")
        print(f"  FAIL  CORS preflight returned allow-origin={allow}")

    # An origin that is not configured: must not be reflected.
    r = client.options(
        f"{base}/api/research/query",
        headers={
            "Origin": "https://not-our-frontend.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    allow = r.headers.get("access-control-allow-origin", "<none>")
    if allow != "https://not-our-frontend.example.com":
        print("  ok    CORS rejects unlisted origins")
    else:
        failures.append("CORS reflected an unlisted origin")
        print("  FAIL  CORS reflected an unlisted origin")

    # Language detection is local, so this exercises the real request path
    # (Pydantic validation, router, error handling) with no API cost.
    r = client.post(
        f"{base}/research/test-language-detection",
        json={"text": "Islamabad Pakistan ka capital hai"},
    )
    if r.status_code == 200:
        print(f"  ok    POST /research/test-language-detection -> 200 {r.text[:90]}")
    else:
        failures.append(f"language detection -> {r.status_code} {r.text[:160]}")
        print(f"  FAIL  POST /research/test-language-detection -> {r.status_code}")

    # Proves every router mounted.
    r = client.get(f"{base}/openapi.json")
    paths = sorted(r.json().get("paths", {}))
    if r.status_code == 200:
        print(f"  ok    GET /openapi.json -> {len(paths)} paths")
    else:
        failures.append(f"/openapi.json -> {r.status_code}")
        print(f"  FAIL  GET /openapi.json -> {r.status_code}")

server.should_exit = True
thread.join(timeout=5)

print()
if failures:
    print(f"FAILED ({len(failures)} problem(s)):")
    for f in failures:
        print("  -", f)
    raise SystemExit(1)

print("PASSED - backend serves the endpoints the frontend needs.")