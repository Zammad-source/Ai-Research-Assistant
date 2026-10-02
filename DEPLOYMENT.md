# Deployment Guide

Backend on **Railway**, frontend on **Vercel**, both on free tiers.

```
frontend/frontend   Next.js 16  ->  Vercel     (public URL)
        |  HTTPS + WSS
        v
backend             FastAPI     ->  Railway    (private API)
        |
        +-- Groq        (answers, translation, query rewriting)
        +-- Tavily      (web retrieval)
        +-- ElevenLabs  (text-to-speech)
        +-- Supabase    (chat history, optional)
```

The backend must go first: Vercel needs the Railway URL, and Railway needs the
Vercel origin for CORS. It is a two-way dependency, so the two steps below
each end with a second deploy.

---

## Before you start

### 1. Push the repo to GitHub

Both platforms deploy from a Git repository, so the changes have to be pushed.

```bash
git add -A
git status          # confirm no .env or *.mp3 got staged
git commit -m "Prepare deployment for Railway and Vercel"
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

Copy `backend/.env.example` to `backend/.env` for local development. The four
values above are already present in your working `.env`.

### 3. Confirm the backend will boot before deploying

This is worth doing: it reproduces the Railway container by blocking every
heavy dependency, so it catches missing packages before a failed build does.

```bash
cd backend
python scripts/verify_build.py    # must print PASSED
python scripts/smoke_test.py      # boots uvicorn, checks /health + CORS
```

---

## Part 1 - Backend on Railway

### Create the project

1. Go to [railway.app](https://railway.app) and sign in.
2. **New Project -> Deploy from GitHub repo** -> pick this repository.
3. Railway will start building immediately. It builds the **repository root**
   by default, which is wrong here - this is a monorepo.

> New accounts start on the **Free Trial** ($5 of credit, expires in 30 days).
> After that it drops to the Free plan's $1/month, which only lasts about a week
> for a service this size. If you need it live for a demo, switch to
> **Hobby ($5/mo)** before you run out - see [Free tier limits](#free-tier-limits).

### Point Railway at the backend folder

1. Right-click the service -> **Settings**.
2. Set **Root Directory** to `backend`.

   Without this Railway looks for `requirements.txt` at the repo root, does not
   find it, and the build fails.
3. Set **Build Method** to `Nixpacks` (the default is fine - it detects
   `requirements.txt` and the `Procfile`).

Railway now picks up, from `backend/`:

| File | Purpose |
| --- | --- |
| `Procfile` | `web:` start command, binds `0.0.0.0:$PORT` |
| `railway.json` | Healthcheck at `/health`, restart policy |
| `.python-version` | Pins Python 3.11 |
| `requirements.txt` | Dependencies (deliberately no torch) |

### Add the environment variables

**Service -> Variables -> New Variable**, for each:

| Variable | Example |
| --- | --- |
| `GROQ_API_KEY` | `gsk_...` |
| `TAVILY_API_KEY` | `tvly_...` |
| `ELEVENLABS_API_KEY` | `...` |
| `SUPABASE_URL` | `https://xxxx.supabase.co` |
| `SUPABASE_KEY` | `anon or service key` |
| `ENVIRONMENT` | `production` |
| `TRANSLATION_BACKEND` | `groq` |
| `LOG_TO_FILE` | `false` |

All five keys are **required** - `pydantic-settings` refuses to start without
them, by design. The last three are optional.

**Do not set `PORT`.** Railway injects it, and the `Procfile` reads it.

### Generate a domain

**Service -> Networking -> Generate Domain** gives you something like
`omnivoise-backend.up.railway.app`. Save it - the frontend needs it.

### Verify

```bash
curl https://omnivoise-backend.up.railway.app/health
# {"status":"ok","environment":"production"}
```

That endpoint is also Railway's healthcheck target, so a passing response
means the platform considers the deploy healthy.

Optionally check CORS with the origin you will use in Part 2:

```bash
curl -i -X OPTIONS https://omnivoise-backend.up.railway.app/api/research/query \
  -H "Origin: https://omnivoice-frontend.vercel.app" \
  -H "Access-Control-Request-Method: POST"
```

Expect `access-control-allow-origin: https://omnivoice-frontend.vercel.app`.

**Leave CORS open for now.** It defaults to allowing any origin so Part 2 can
connect immediately. Lock it down at the end.

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

### Add the environment variable

**Settings -> Environment Variables -> Add**, for **Production** (and
Previews, if you want previews to work):

| Variable | Value |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | `https://omnivoise-backend.up.railway.app` |
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

Click **Deploy**. When it succeeds you get
`https://omnivoice-frontend.vercel.app`.

---

## Part 3 - Lock down CORS

Now that the Vercel URL exists, tell Railway about it.

On Railway, add:

```
CORS_ORIGINS=https://omnivoice-frontend.vercel.app
```

Then **redeploy** (adding a variable does not restart a running service).

Vercel preview deployments get random URLs. To allow those too, list several
comma-separated origins:

```
CORS_ORIGINS=https://omnivoice-frontend.vercel.app,https://omnivoice-frontend-git-main-yourname.vercel.app
```

Without `CORS_ORIGINS` the API allows any origin, which is convenient and
loose. Setting it means requests from an unlisted origin get no CORS headers
and the browser blocks them.

---

## Post-deploy checklist

| # | Check | Expected |
| --- | --- | --- |
| 1 | `curl <railway-url>/health` | `{"status":"ok",...}` |
| 2 | Load the Vercel URL | Home page renders, no console errors |
| 3 | Ask a research question | Answer with clickable `[n]` citations, sources listed |
| 4 | Click a citation | Scrolls to and highlights the source card |
| 5 | Open Translator, two browsers, same room | Messages appear translated |
| 6 | Press voice/TTS playback | Audio plays |
| 7 | Check Railway logs | No `sentence-transformers unavailable` spam, no tracebacks |

Item 5 is the one that catches a misconfigured WebSocket, and item 3 is what
proves the whole chain works end to end.

### Rate limits

These are per client IP, counted in memory (so they reset whenever the service
restarts):

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

Note the limits are **in-memory, per container**. They do not aggregate across
replicas - fine on the Free plan (1 replica), but if you ever scale out, raise
the limits or move to a shared store.

---

## Free tier limits

**Railway** does *not* have a comfortable permanent free tier. Per
[docs.railway.com/pricing/plans](https://docs.railway.com/pricing/plans):

| Plan | Cost | Credit | RAM | Ephemeral disk | Replicas |
| --- | --- | --- | --- | --- | --- |
| Free Trial | $0 | **$5 once**, expires in 30 days | 1 GB | 1 GB | 2 |
| **Free** | $0/mo | **$1 / month**, no rollover | **0.5 GB** | **1 GB** | 1 |
| Hobby | $5/mo | $5 / month included | 48 GB | 100 GB | 6 |

The catch is the **$1/month Free credit**. A small idle FastAPI costs roughly
$0.15-0.20/day (RAM plus CPU, metered per second), so **$1 runs out in about a
week**. Once credit is exhausted the service stops responding.

So realistically:

- **For a graded demo or hackathon pitch, pick Hobby ($5/mo).** The $5 monthly
  credit comfortably covers this app, and you get 48 GB RAM instead of 0.5 GB.
- **If you use the Free plan**, treat the deployment as a timed preview and
  re-ups before you need it live.

The 0.5 GB RAM ceiling is also the reason `requirements.txt` excludes torch and
`sentence-transformers` - torch alone is roughly 800 MB, so including it would
fail to start rather than merely run slowly.

The 1 GB ephemeral disk is the second constraint, which is why generated TTS
clips are now deleted in a `BackgroundTask` after each response instead of
piling up in `tts_output/`.

| Heavy thing | What runs instead |
| --- | --- |
| Local NLLB translation model | Groq (`TRANSLATION_BACKEND=groq`) |
| `sentence-transformers` embeddings | Pure-Python lexical ranking in `retrieval.py` |

**Vercel** Hobby is genuinely free with no usage cap for this kind of static app.

Expect these to be your actual limits, not the platform's:

- **Groq** free tier rate-limits, so heavy concurrent use degrades first.
- **Tavily** is capped at 1000 searches/month; each research query spends one.
- **ElevenLabs** free tier has a monthly character cap on TTS.

---

## Troubleshooting

**Railway build fails on `requirements.txt` not found**
Root Directory is not set to `backend`. Service -> Settings -> Root Directory.

**Backend deploys, every request returns 500**
A required variable is missing. `Service -> Variables`. The first log line names
the offending setting. `scripts/verify_build.py` catches this locally.

**`ModuleNotFoundError: numpy` or `sentence_transformers`**
Something reintroduced a hard dependency on the heavy packages.
`scripts/verify_build.py` blocks them and fails loudly if an import slips back
in.

**Frontend loads but shows "Unable to connect to the server"**
`NEXT_PUBLIC_API_URL` is wrong, still points at localhost, or has a trailing
slash. Remember it is inlined at **build** time: after changing it, redeploy
(Vercel: Deployments -> ... -> Redeploy, or push an empty commit).

**Research requests fail with a CORS error**
`CORS_ORIGINS` on Railway does not list the exact frontend origin, including
`https://` and the subdomain. Vercel preview URLs differ per branch, so either
add them or leave `CORS_ORIGINS` unset while iterating.

**Translator connects but no messages arrive**
The socket needs `wss://`. If `NEXT_PUBLIC_WS_URL` was set by hand to `ws://`,
the browser blocks it as mixed content on an HTTPS page. Clear the variable and
let it derive from the API URL. Both `/ws/translator/{room_id}` and the legacy
`/translator/ws/{room_id}` are served, so the path is not the problem.

**First request is very slow, later ones fast**
Tavily results are cached for 5 minutes per query. Groq translation has no
cold start now that there is no local model, but the first call still pays
network latency.

**Frontend shows "Server error: 429" during a demo**
You hit a rate limit. See [Rate limits](#rate-limits). Research is capped at
5 requests per minute per IP.

**Railway service stops responding after a few days**
The Free plan only includes $1 of monthly credit, which this app burns through
in about a week. Upgrade to Hobby ($5/mo) or re-ups before a demo.

**`No space left on device` / disk fills up**
Free-tier containers have 1 GB of ephemeral storage. Generated TTS clips are
now deleted automatically after each response, so this usually means something
else is writing to disk - check whether `LOG_TO_FILE` was left on and whether
old files are still sitting in `tts_output/`.

**Local dev broke after these changes**
`backend/.env` still needs all five keys, and
`frontend/frontend/.env.local` still needs `NEXT_PUBLIC_API_URL=http://localhost:8000`.
Both files are gitignored, so they survive deploys untouched.