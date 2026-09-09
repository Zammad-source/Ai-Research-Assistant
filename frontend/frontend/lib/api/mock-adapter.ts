import { ApiError } from "./client"
import type { ResearchQueryResponse } from "@/types/api"
import type { ResearchSource } from "@/types/research"
import type { TranscriptionResponse } from "@/types/voice"

const MOCK_SOURCES: ResearchSource[] = [
  {
    id: "s1",
    title: "Understanding Retrieval-Augmented Generation",
    domain: "arxiv.org",
    url: "https://arxiv.org",
    snippet: "RAG combines a retriever with a generator to ground model outputs in retrieved documents.",
  },
  {
    id: "s2",
    title: "A Practical Guide to Citations in AI Answers",
    domain: "example.com",
    url: "https://example.com",
    snippet: "Inline citations let readers verify claims against the original source material directly.",
  },
]

function randomId() {
  return Math.random().toString(36).slice(2, 10)
}

export function sendResearchQueryMock(
  query: string,
  conversationId: string | null
): Promise<ResearchQueryResponse> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        conversation_id: conversationId ?? randomId(),
        message_id: randomId(),
        answer: `Here's a summary based on your question: "${query}". Retrieval-augmented systems fetch relevant passages before generating a response [1], and presenting citations inline helps readers trust and verify the answer [2].`,
        sources: MOCK_SOURCES,
        created_at: new Date().toISOString(),
      })
    }, 1400)
  })
}

/**
 * Stand-in for transcribeAudio (lib/api/voice.ts) — same signature and
 * response shape. Rejects on empty audio so the "no audio captured"
 * error path is demoable without a real backend.
 */
export function transcribeAudioMock(audioBlob: Blob): Promise<TranscriptionResponse> {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      if (audioBlob.size === 0) {
        reject(new ApiError(400, "No audio was captured. Please try again."))
        return
      }
      resolve({ text: "What is retrieval augmented generation?", language: "en" })
    }, 1200)
  })
}

/**
 * Stand-in for requestSpeech (lib/api/voice.ts). Always rejects — there's
 * no real audio to synthesize in mock mode, so this deliberately forces
 * useTextToSpeech's fallback path (browser SpeechSynthesis) to run,
 * which is exactly the "TTS degraded" behavior Phase 2.4 needs to prove
 * out before the backend's real TTS engine exists.
 */
export function requestSpeechMock(): Promise<Blob> {
  return Promise.reject(
    new ApiError(503, "Mock mode has no real audio — falling back to browser voice.")
  )
}