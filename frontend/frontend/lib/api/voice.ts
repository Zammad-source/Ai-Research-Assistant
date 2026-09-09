import { ApiError } from "./client"
import type { TranscriptionResponse } from "@/types/voice"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export function transcribeAudio(audioBlob: Blob, signal?: AbortSignal): Promise<TranscriptionResponse> {
  const formData = new FormData()
  formData.append("audio", audioBlob, "recording.webm")
  return uploadAudio(formData, signal)
}

async function uploadAudio(formData: FormData, signal?: AbortSignal): Promise<TranscriptionResponse> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 30000)
  signal?.addEventListener("abort", () => controller.abort())

  try {
    const res = await fetch(`${API_BASE_URL}/api/voice/transcribe`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    })

    if (!res.ok) {
      throw new ApiError(
        res.status,
        "Couldn't transcribe the audio. Please try again."
      )
    }
    return (await res.json()) as TranscriptionResponse
  } catch (err) {
    if (err instanceof ApiError) throw err
    if ((err as Error).name === "AbortError") {
      throw new ApiError(408, "Transcription timed out. Please try again.")
    }
    throw new ApiError(503, "Couldn't reach the server. Check your connection.")
  } finally {
    clearTimeout(timeout)
  }
}

export async function requestSpeech(text: string, signal?: AbortSignal): Promise<Blob> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 20000)
  signal?.addEventListener("abort", () => controller.abort())

  try {
    const res = await fetch(`${API_BASE_URL}/api/voice/speech`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
      signal: controller.signal,
    })

    if (!res.ok) {
      throw new ApiError(res.status, "Couldn't generate speech for this response.")
    }
    return await res.blob()
  } catch (err) {
    if (err instanceof ApiError) throw err
    if ((err as Error).name === "AbortError") {
      throw new ApiError(408, "Speech generation timed out.")
    }
    throw new ApiError(503, "Couldn't reach the server. Check your connection.")
  } finally {
    clearTimeout(timeout)
  }
}