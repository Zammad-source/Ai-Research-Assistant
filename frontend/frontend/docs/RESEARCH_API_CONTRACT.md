# Research API Contract

The frontend (Next.js) expects exactly this contract from the FastAPI backend.
Anything that matches this shape will work with zero frontend changes.

## Endpoint

```
POST {API_BASE_URL}/api/research/query
Content-Type: application/json
```

`API_BASE_URL` is whatever we agree on for dev/prod (e.g. `http://localhost:8000`).

## Request body

```json
{
  "conversation_id": "string or null",
  "query": "string"
}
```

- `conversation_id` is `null` on the **first** message of a new conversation.
  The backend should generate one and return it — the frontend stores it and
  sends it back on every following message in that thread.

## Success response — `200 OK`

```json
{
  "conversation_id": "conv_abc123",
  "message_id": "msg_def456",
  "answer": "RAG combines retrieval and generation [1]. Citing sources inline builds trust [2].",
  "sources": [
    {
      "id": "s1",
      "title": "Understanding Retrieval-Augmented Generation",
      "url": "https://arxiv.org/some-paper",
      "domain": "arxiv.org",
      "snippet": "A one or two sentence excerpt from the source."
    },
    {
      "id": "s2",
      "title": "A Practical Guide to Citations in AI Answers",
      "url": "https://example.com/article",
      "domain": "example.com",
      "snippet": "Another short excerpt."
    }
  ],
  "created_at": "2026-08-27T10:15:00Z"
}
```

**Important:** the citation markers in `answer` (`[1]`, `[2]`, ...) are matched
**by position** to the `sources` array — `[1]` → `sources[0]`, `[2]` →
`sources[1]`, and so on. Keep them in the same order.

## Error response — any `4xx` / `5xx`

```json
{
  "error": {
    "code": "rate_limited",
    "message": "Too many requests, please wait a moment."
  }
}
```

`code` is a short machine-readable string (e.g. `invalid_query`, `timeout`,
`internal_error`); `message` is what gets shown to the user, so keep it
human-readable.

## Other notes for integration

- **CORS**: dev frontend runs at `http://localhost:3000` — needs to be
  allowed on the backend.
- **Timeout**: frontend aborts and shows an error after 20s. If research
  queries can genuinely take longer than that, let us know so we can raise
  the timeout or move to a streaming/async pattern.
- **Retries**: the frontend automatically retries failed requests twice
  (with backoff) before showing an error, so make sure repeated identical
  requests are safe to run (idempotent) or return a stable result.
- **Streaming**: not required for this phase — one request, one JSON
  response. If we want live token-by-token output later, that's a separate
  SSE/WebSocket endpoint we can design on top of this one without breaking
  it.
- **Auth**: none implemented yet on the frontend. Tell us the scheme
  (API key header, bearer token, etc.) once it's decided and we'll wire it
  into `lib/api/client.ts`.
