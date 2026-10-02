# Deployment Guide

Backend on **Render**, frontend on **Vercel**, both on free tiers.

```
frontend/frontend   Next.js 16  ->  Vercel   (public URL)
        |  HTTPS + WSS
        v
backend             FastAPI     ->  Render   (private API)
        |
        +-- Groq        (answers, translation, query rewriting)
        +-- Tavily      (web retrieval)
        +-- ElevenLabs  (text-to-speech)
        +-- Supabase    (chat history, optional)
```

Render + Vercel is the pairing to use. Railway was the original target but its
Free plan gives you **$1 of credit per month**, which this service burns through
in about a week, and new accounts hit a provisioning limit that blocks creating
a second project.

There is a `render.yaml` in the repo root, so the backend is one click.

> The backend must be deployed first: Vercel needs the Render URL, and Render
> needs the Vercel origin for CORS. It is a two-way dependency, so each step ends
> with a follow-up edit.

---

## Before you start

### 1. Push the repo to GitHub

Both platforms deploy from a Git repository, so the changes have to be pushed.

```bash
git add -A
git status          # confirm no .env or *.mp3 got staged
git commit -m "Prepare deployment for Render and Vercel"
git push
```

`backend/.env` is gitignored. **Never commit it** - it holds live API keys.

### 2. API keys you need

| Service | What it powers | Free tier |
| --- | --- | --- |
| [Groq](https://console.groq.com/keys) | Answers, translation, query rewriting | Yes |
| [Tavily](https://app.tavily.com) | Web search for research answers | 1000 credits/mo |
| [ElevenLabs](https://elevenlabs.io) | Text-to-speech | Yes, limited |
| [Supabase](https://supabase.com) | Chat history (optional) | Yes |

Copy `backend/.env.example` to `backend/.env` for local development. The five
values above are already present in your working `.env`, and you will paste the
same five into Render in Part 1.

### 3. Confirm the backend will boot before deploying

This reproduces the Render container by blocking every heavy dependency, so it
catches missing packages before a failed build does.

```bash
cd backend
python scripts/verify_build.py    # must print PASSED
python scripts/smoke_test.py      # boots uvicorn, checks /health + CORS
```

---

## Part 1 - Backend on Render

### Create the service

1. Go to [dashboard.render.com](https://dashboard.render.com) and sign in.
2. **New -> Blueprint**, then pick this repository.

   Render reads `render.yaml` from the repo root and shows a preview of what it
   will create. Confirm the service is called `ai-research-assistant-api`.

The blueprint already sets the parts that are easy to get wrong:

| Setting | Value | Why it matters |
| --- | --- | --- |
| Root Directory | `backend` | Monorepo - `requirements.txt` is not at the repo root |
| Runtime | Python 3.11 | Matches `.python-version` |
| Plan | `free` | 0.1 CPU, 512 MB RAM |
| Build Command | `pip install -r requirements.txt` | |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT ...` | `$PORT` is injected by Render |
| Health Check Path | `/health` | Gates the rollout |
| Auto-Deploy | on every commit to `main` | |

Prefer creating it by hand instead of via the blueprint? Same fields, plus
**Create Web Service -> Connect repo -> Environment: Python -> Root Directory:
`backend`**.

### Enter the environment variables

Render prompts for every variable marked `sync: false` in the blueprint:

| Variable | Where to get it |
| --- | --- |
| `GROQ_API_KEY` | `backend/.env` |
| `TAVILY_API_KEY` | `backend/.env` |
| `ELEVENLABS_API_KEY` | `backend/.env` |
| `SUPABASE_URL` | `backend/.env` |
| `SUPABASE_KEY` | `backend/.env` |
| `CORS_ORIGINS` | Leave blank for now, see Part 3 |

All five keys are **required** - `pydantic-settings` refuses to start without
them, by design.

The blueprint hardcodes the optional ones: `ENVIRONMENT=production`,
`TRANSLATION_BACKEND=groq`, `LOG_TO_FILE=false`, `RATE_LIMIT_PER_MINUTE=20`.

> `LOG_TO_FILE=false` matters on Render. The service filesystem is ephemeral, so
> rotating log files there just burn disk that never gets read. Render captures
> stdout anyway, and `logging_config.py` always writes there.

**Do not set `PORT`.** Render injects it.

Click **Apply**. The first build takes a few minutes because Python and every
dependency are installed from scratch.

### Get the URL and verify

Render assigns a subdomain like
`https://ai-research-assistant-api.onrender.com`. It appears at the top of the
service page.

```bash
curl https://ai-research-assistant-api.onrender.com/health
# {"status":"ok","environment":"production"}
```

**If the first curl hangs for a minute and then returns, that is normal.**
Free services sleep after 15 minutes without traffic and take roughly a minute
to wake. The wake is not a failure.

Optionally check CORS with the origin you will use in Part 2:

```bash
curl -i -X OPTIONS https://ai-research-assistant-api.onrender.com/api/research/query \
  -H "Origin: https://your-app.vercel.app" \
  -H "Access-Control-Request-Method: POST"
```

Expect `access-control-allow-origin: https://your-app.vercel.app`.

---

## Part 2 - Frontend on Vercel

### Create the project

1. Go to [vercel.com](https://vercel.com) and sign in.
2. **Add New -> Project** -> import this same repository.
3. Set **Root Directory** to **`frontend/frontend`**

   This nesting is easy to miss. It is where `package.json` lives.

   It should then detect:

   | Setting | Value |
   | --- | --- |
   | Framework Preset | Next.js |
   | Install Command | `npm ci` |
   | Build Command | `npm run build` |
   | Output Directory | `.next` |

### Add the environment variables

**Settings -> Environment Variables -> Add**, for **Production** (and
Previews, if you want previews to work):

| Variable | Value |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | `https://ai-research-assistant-api.onrender.com` |
| `NEXT_PUBLIC_USE_MOCK_API` | `false` |

No trailing slash on the URL - endpoints are appended as
`${API_URL}/api/research/query`.

Two things to know:

- **`NEXT_PUBLIC_WS_URL` is optional.** If you leave it unset the WebSocket URL
  is derived from `NEXT_PUBLIC_API_URL` (`https` -> `wss`). Set it explicitly
  only if the socket lives on a different host.
- **Only the backend needs API keys.** Never put `GROQ_API_KEY` or any other
  secret in Vercel. Anything named `NEXT_PUBLIC_*` is inlined into the
  JavaScript served to every visitor.

### Deploy

Click **Deploy**. When it succeeds you get `https://your-app.vercel.app`.

---

## Part 3 - Lock down CORS

Now that the Vercel URL exists, tell Render about it.

**Service -> Environment**, set:

```
CORS_ORIGINS=https://your-app.vercel.app
```

Then **Save Changes** and trigger a deploy (**Manual Deploy -> Deploy latest
commit**) - adding a variable does not restart a running service.

Vercel preview deployments get random URLs. To allow those too, list several
comma-separated origins:

```
CORS_ORIGINS=https://your-app.vercel.app,https://your-app-git-main-yourname.vercel.app
```

Without `CORS_ORIGINS` the API allows any origin, which is convenient and
loose. Setting it means requests from an unlisted origin get no CORS headers
and the browser blocks them.

---

## Post-deploy checklist

| # | Check | Expected |
| --- | --- | --- |
| 1 | `curl <render-url>/health` | `{"status":"ok",...}` |
| 2 | Load the Vercel URL | Home page renders, no console errors |
| 3 | Ask a research question | Answer with clickable `[n]` citations, sources listed |
| 4 | Click a citation | Scrolls to and highlights the source card |
| 5 | Open Translator, two browsers, same room | Messages appear translated |
| 6 | Press voice/TTS playback | Audio plays |
| 7 | Check Render logs | No `sentence-transformers unavailable` spam, no tracebacks |

Item 5 is the one that catches a misconfigured WebSocket, and item 3 is what
proves the whole chain works end to end.

### Rate limits

These are per client IP, counted in memory (so they reset whenever the service
restarts or wakes from sleep):

| Endpoint | Limit | Why |
| --- | --- | --- |
| `/api/research/query` | 5 / min | 4+ LLM calls plus a web search each |
| `/api/voice/speech` | 15 / min | ElevenLabs character quota |
| `/api/voice/transcribe` | 15 / min | Groq Whisper |
| `/research` (legacy) | 15 / min | |

These exist because the endpoints are public and every call spends paid API
credit. In practice research is generous enough for a demo - a single query
takes several seconds, so you cannot approach 5/min by clicking quickly.

If a demo ever gets blocked, raise the limit in
`backend/app/routes/frontend_api.py` or drop slowapi's default HTML error page
in favour of a JSON body the frontend already knows how to read.

The limits are **in-memory, per instance**. They do not aggregate across
replicas - fine on the Free plan (1 instance), but if you ever scale out, raise
the limits or move to a shared store.

---

## Free tier limits

**Render** Free, per [docs.render.com/pricing](https://docs.render.com/pricing):

| Plan | Cost | CPU | RAM | Sleeps? | Instance hours |
| --- | --- | --- | --- | --- | --- |
| **Free** | $0 | 0.1 | 512 MB | Yes, after 15 min idle | 750 / month |

No credit balance to run out, which is the main reason this is better than
Railway Free for anything long-lived. The tradeoffs are a cold start and a
hard RAM ceiling:

- **Cold start.** After 15 minutes idle the instance stops and the next request
  gets Render's loading page for roughly a minute. During a demo, hit
  `/health` a minute early to pre-warm it.
- **512 MB RAM.** This is why `requirements.txt` excludes torch and
  `sentence-transformers` - torch alone is roughly 800 MB, so including it would
  fail to start rather than merely run slowly.

| Heavy thing | What runs instead |
| --- | --- |
| Local NLLB translation model | Groq (`TRANSLATION_BACKEND=groq`) |
| `sentence-transformers` embeddings | Pure-Python lexical ranking in `retrieval.py` |

WebSockets work on the Free plan, so the Translator room feature is fine. Note
that an idle WebSocket with no incoming messages does not keep the service
awake.

**Vercel** Hobby is genuinely free with no usage cap for this kind of static app.

Expect these to be your actual limits, not the platform's:

- **Groq** free tier rate-limits, so heavy concurrent use degrades first.
- **Tavily** is capped at 1000 searches/month; each research query spends one.
- **ElevenLabs** free tier has a monthly character cap on TTS.

---

## Troubleshooting

**Build fails with `requirements.txt not found`**
Root Directory is not set to `backend`. Blueprints get this from
`rootDir: backend`; if you built the service by hand, set it in
**Settings -> Root Directory**.

**Deploy succeeds, every request returns 500**
A required variable is missing. **Service -> Environment**. The first log line
names the offending setting. `scripts/verify_build.py` catches this locally.

**Service stays in "Deploying" forever**
`/health` is not responding, so Render rolls back. Usually a missing key again,
or the health check firing while Groq is unreachable at import time.

**`ModuleNotFoundError: numpy` or `sentence_transformers`**
Something reintroduced a hard dependency on the heavy packages.
`scripts/verify_build.py` blocks them and fails loudly if an import slips back
in.

**Frontend loads but shows "Unable to connect to the server"**
`NEXT_PUBLIC_API_URL` is wrong, still points at localhost, or has a trailing
slash. Remember it is inlined at **build** time: after changing it, redeploy
(Vercel: Deployments -> ... -> Redeploy, or push an empty commit).

**Research requests fail with a CORS error**
`CORS_ORIGINS` on Render does not list the exact frontend origin, including
`https://` and the subdomain. Vercel preview URLs differ per branch, so either
add them or leave `CORS_ORIGINS` unset while iterating.

**Translator connects but no messages arrive**
The socket needs `wss://`. If `NEXT_PUBLIC_WS_URL` was set by hand to `ws://`,
the browser blocks it as mixed content on an HTTPS page. Clear the variable and
let it derive from the API URL. Both `/ws/translator/{room_id}` and the legacy
`/translator/ws/{room_id}` are served, so the path is not the problem.

**First request is very slow, later ones fast**
Either a cold start (see [Free tier limits](#free-tier-limits)) or an uncached
Tavily result - results are cached for 5 minutes per query. Groq translation
has no warm-up cost now that there is no local model, but the first call still
pays network latency.

**Frontend shows "Server error: 429" during a demo**
You hit a rate limit. See [Rate limits](#rate-limits). Research is capped at
5 requests per minute per IP.

**Render service stops responding between demo sessions**
Expected. Free instances sleep after 15 minutes idle. Send one request to
`/health` about a minute before you need it.

**Local dev broke after these changes**
`backend/.env` still needs all five keys, and
`frontend/frontend/.env.local` still needs `NEXT_PUBLIC_API_URL=http://localhost:8000`.
Both files are gitignored, so they survive deploys untouched.