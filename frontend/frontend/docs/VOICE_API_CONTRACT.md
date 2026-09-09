# Voice API Contract

For whoever builds the STT/TTS endpoints in FastAPI. The frontend already
calls these — flip `NEXT_PUBLIC_USE_MOCK_API=false` once they exist and no
frontend code changes.

## POST /api/voice/transcribe

Speech-to-text. Multipart upload, not JSON.

**Request:** `multipart/form-data`
- `audio` (file) — browser-recorded clip. Typically `audio/webm;codecs=opus`
  (Chrome/Edge/Firefox default) or `audio/ogg;codecs=opus` as a fallback.
  Convert/accept both, or transcode server-side before feeding Whisper.

**Response 200:**
```json
{
  "text": "What is retrieval augmented generation?",
  "language": "en"
}
```

**Response (error, any non-2xx):**
```json
{
  "error": {
    "code": "transcription_failed",
    "message": "Human-readable message shown directly to the user"
  }
}
```

Frontend timeout: 30s.

---

## POST /api/voice/speech

Text-to-speech. Returns raw audio bytes, not JSON.

**Request:**
```json
{ "text": "The answer to synthesize as speech." }
```

**Response 200:** binary audio body (`audio/mpeg` or `audio/wav`), no JSON
wrapper. The frontend does `res.blob()` directly and plays it.

**Response (error, any non-2xx):** same `{ "error": { code, message } }`
shape as above. When this happens (including if a regional voice like
Saraiki isn't ready), the frontend automatically falls back to the
browser's own text-to-speech — no user-facing crash, but real audio from
your endpoint is obviously better when available.

Frontend timeout: 20s.
