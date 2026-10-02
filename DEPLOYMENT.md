# Deployment Guide

Both halves run on **Vercel**, on the Hobby plan, at no cost.

| | Project | URL |
| --- | --- | --- |
| Backend | `ai-research-assistant-api` | https://ai-research-assistant-api.vercel.app |
| Frontend | `omnivoice-frontend` | https://omnivoice-frontend.vercel.app |

They are two separate Vercel projects on purpose. Only the backend gets API
keys; the frontend's `NEXT_PUBLIC_*` values are inlined into the JavaScript that
every visitor downloads, so a key stored there would be public.

```
frontend/frontend   Next.js 16  ->  Vercel   (public URL)
        |  HTTPS
        v
backend             FastAPI     ->  Vercel   (private API, server-only keys)
        |
        +-- Groq        (answers, translation, query rewriting)
        +-- Tavily      (web retrieval)
        +-- ElevenLabs  (text-to-speech)
        +-- Supabase    (chat history, optional)
```

---

## What works, and what does not

| Feature | Status | Why |
| --- | --- | --- |
| Research with citations | Live | Plain HTTP + outbound calls |
| Voice input / transcription | Live | Plain HTTP |
| Text-to-speech playback | Live | Writes to `/tmp`, which is writable |
| Translator rooms | **Mocked in the browser** | Vercel Functions cannot hold WebSockets |

Vercel Functions time out and never upgrade to `wss://`, so the translator's
long-lived socket cannot run there. The frontend detects this and falls back to
its in-browser mock socket, which keeps the rooms demoable. Research and voice
still hit the real backend.

If the translator must connect browsers on different machines for real, the
backend needs a platform that holds WebSockets. Render, Railway or Fly all do
that, but each one needs a card or has a credit allowance that runs out - see
[Going fully live](#going-fully-live).

---

## Redeploying

Both projects are deployed from this repo, but they were originally created from
the CLI rather than connected to Git. To publish a change, deploy from the
matching directory:

```bash
cd backend
vercel deploy --prod --yes          # -> ai-research-assistant-api

cd ../frontend/frontend
vercel deploy --prod --yes          # -> omnivoice-frontend
```

To get push-to-deploy instead, run `vercel git connect` once per directory.

### Rules that bite

- **`NEXT_PUBLIC_*` values are baked in at build time.** Changing one requires a
  redeploy, not a restart. This is why a wrong `NEXT_PUBLIC_API_URL` survives a
  "successful" deploy and shows up as "unable to connect to the server".
- **Each project has its own environment variables.** Setting
  `NEXT_PUBLIC_API_URL` on the backend does nothing for the frontend.
- **`.vercelignore` matters.** `backend/venv/` is 1.69 GB. Without the ignore
  file the upload stalls or fails. The same file keeps `.env` files out of the
  bundle.

---

## Environment variables

### `ai-research-assistant-api` (all secret)

| Variable | Notes |
| --- | --- |
| `GROQ_API_KEY` | Answers, translation, query rewriting |
| `TAVILY_API_KEY` | Web search |
| `ELEVENLABS_API_KEY` | Text-to-speech |
| `SUPABASE_URL` | Chat history |
| `SUPABASE_KEY` | Chat history |
| `CORS_ORIGINS` | `https://omnivoice-frontend.vercel.app` |
| `ENVIRONMENT` | `production` |
| `TRANSLATION_BACKEND` | `groq` |
| `LOG_TO_FILE` | `false` - Vercel's bundle is read-only, so logs go to stdout only |

All five keys are **required**. `pydantic-settings` refuses to start without
them, by design, so a missing one shows up as a boot failure rather than a
runtime error deep in a request.

### `omnivoice-frontend` (all public - safe to read, never put a key here)

| Variable | Value |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | `https://ai-research-assistant-api.vercel.app` |
| `NEXT_PUBLIC_USE_MOCK_API` | `false` |
| `NEXT_PUBLIC_TRANSLATOR_MOCK` | `true` - see [above](#what-works-and-what-does-not) |

`NEXT_PUBLIC_WS_URL` is deliberately unset. Setting it by hand is how the
translator ends up on `ws://` and gets blocked as mixed content on an HTTPS
page.

---

## Vercel specifics this codebase has to accommodate

Deploying FastAPI to Vercel is not the same as deploying it to a container, and
three things in this backend had to change for it:

1. **The bundle is read-only.** `logging_config.py` used to call
   `os.makedirs("logs")` at import time, which raises `Errno 30` on Vercel and
   prevents the app from booting at all. It is now guarded, and file logging
   turns itself off when `VERCEL` is set.
2. **Only `/tmp` is writable.** Generated TTS clips go to
   `tempfile.gettempdir()` on serverless and to `./tts_output` everywhere else,
   overridable with `TTS_OUTPUT_DIR`.
3. **Python 3.11 does not exist here.** Vercel's runtime supports 3.12, 3.13 and
   3.14 only, so `.python-version` is pinned to 3.12.

Also worth knowing, because it looks like a bug when it happens:

- **Do not add a `functions` block to `vercel.json`.** Keying it to
  `app/main.py` is what Vercel's own docs show, but the build then fails with
  *"The pattern `app/main.py` defined in `functions` doesn't match any
  Serverless Functions inside the `api` directory"* because that validation runs
  before the framework entrypoint is resolved. Leave `vercel.json` out and the
  default duration is fine.
- **Framework preset matters.** A project created through the CLI/API can be
  pinned to `Other`, which skips FastAPI detection entirely and produces an
  instant, empty build that 404s. Set the preset to **FastAPI**.
- **Deployment Protection is on by default** for new projects, which puts Vercel
  Auth in front of production and breaks every browser request. Turn it off:
  `vercel project protection disable <project> --sso`.

---

## Local development

Nothing above changes how you work locally.

```bash
cd backend
python scripts/verify_build.py    # must print PASSED
python scripts/smoke_test.py      # boots uvicorn, checks /health + CORS

cd ../frontend/frontend
npm run dev
```

`backend/.env` still needs all five keys, and
`frontend/frontend/.env.local` still needs
`NEXT_PUBLIC_API_URL=http://localhost:8000`. Leave
`NEXT_PUBLIC_TRANSLATOR_MOCK` unset locally so the translator connects to your
real local backend.

---

## Rate limits

Per client IP, counted in memory, so they reset whenever the instance restarts:

| Endpoint | Limit | Why |
| --- | --- | --- |
| `/api/research/query` | 5 / min | 4+ LLM calls plus a web search each |
| `/api/voice/speech` | 15 / min | ElevenLabs character quota |
| `/api/voice/transcribe` | 15 / min | Groq Whisper |
| `/research` (legacy) | 15 / min | |

These are public endpoints that spend paid API credit on every call. Research is
generous enough for a demo - one query takes several seconds, so 5/min cannot be
reached by clicking quickly. Raise them in
`backend/app/routes/frontend_api.py` if a demo ever needs more.

---

## Post-deploy checklist

| # | Check | Expected |
| --- | --- | --- |
| 1 | `curl https://ai-research-assistant-api.vercel.app/health` | `{"status":"ok",...}` |
| 2 | Load https://omnivoice-frontend.vercel.app | Home page renders, no console errors |
| 3 | Ask a research question | Answer with clickable `[n]` citations, sources listed |
| 4 | Click a citation | Scrolls to and highlights the source card |
| 5 | Open Translator, two tabs, same room | Messages appear (mock socket) |
| 6 | Press voice/TTS playback | Audio plays |
| 7 | Vercel logs for the backend | No tracebacks, no `No space left on device` |

---

## Troubleshooting

**Frontend shows "Unable to connect to the server"**
`NEXT_PUBLIC_API_URL` is wrong, unset, or has a trailing slash. It is inlined at
build time, so redeploy after changing it.

**`401` or a Vercel login page on the deployed URL**
Deployment Protection is on. `vercel project protection disable <project> --sso`.

**Backend 404s on every route**
The framework preset is not `FastAPI`, so there is no Python function. Check
`vercel project inspect ai-research-assistant-api` and look for
`Framework Preset: FastAPI`.

**Backend 500s, first line of the log names a setting**
A required env var is missing on the `ai-research-assistant-api` project.

**`ModuleNotFoundError: numpy` or `sentence_transformers`**
Something reintroduced a hard dependency on the heavy packages.
`scripts/verify_build.py` fails loudly if an import slips back in.

**Build succeeds instantly and serves nothing**
Framework detection never ran (see the `vercel.json` note above), or the upload
was empty because `.vercelignore` excluded the source.

**Research requests fail with a CORS error**
`CORS_ORIGINS` on the backend does not list the exact frontend origin. Vercel
preview URLs differ per branch, so add them or clear `CORS_ORIGINS` while
iterating.

**Translator connects but nothing happens**
`NEXT_PUBLIC_TRANSLATOR_MOCK` is unset or false while the backend is on Vercel.
It must be `true` here.

**Frontend shows "Server error: 429"**
Rate limit hit. See [Rate limits](#rate-limits).

---

## Going fully live

A real cross-machine translator needs a host that keeps WebSockets open. Options,
all of which need a card on file or a credit allowance:

| Platform | WebSockets | Cost | Catch |
| --- | --- | --- | --- |
| **Render** | Yes | $0, 750 instance hrs/mo | Requires a payment method on the workspace, even for Free |
| **Railway** | Yes | $1/mo credit | Free credit lasts about a week at this app's idle cost |
| **Fly.io** | Yes | $0 allowance | Requires a card |

`render.yaml` in the repo root is a ready-made Render Blueprint: point it at this
repository, paste the five keys, and set `NEXT_PUBLIC_TRANSLATOR_MOCK` back to
`false` on the frontend. Only `CORS_ORIGINS` needs the new hostname.