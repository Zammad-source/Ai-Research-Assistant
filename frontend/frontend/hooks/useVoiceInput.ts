"use client"

import { useCallback, useRef, useState } from "react"
import { transcribeAudio } from "@/lib/api/voice"
import { transcribeAudioMock } from "@/lib/api/mock-adapter"
import { ApiError } from "@/lib/api/client"
import type { RecordingState, VoiceError } from "@/types/voice"

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK_API === "true"

// MediaRecorder needs a mimeType the backend's Whisper endpoint can read.
// Browser support varies, so we probe in priority order and let the
// browser pick its default only as a last resort.
const PREFERRED_MIME_TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"]

function pickSupportedMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined
  return PREFERRED_MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type))
}

/**
 * Owns the mic recording lifecycle + upload-to-transcript step, mirroring
 * the mutation-owns-state pattern useResearchConversation.ts uses for
 * text queries. ResearchInput/VoiceRecorder consume this instead of
 * touching MediaRecorder or fetch directly.
 */
export function useVoiceInput() {
  const [state, setState] = useState<RecordingState>("idle")
  const [elapsedMs, setElapsedMs] = useState(0)
  const [error, setError] = useState<VoiceError | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const startedAtRef = useRef(0)

  const stopTimer = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = null
  }, [])

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }, [])

  const startRecording = useCallback(async () => {
    setError(null)
    setState("requesting-permission")

    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setError({ code: "no_microphone", message: "This browser doesn't support microphone access." })
      setState("error")
      return
    }

    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (err) {
      const name = (err as DOMException).name
      if (name === "NotAllowedError" || name === "SecurityError") {
        setError({
          code: "permission_denied",
          message: "Microphone access was denied. Allow it in your browser settings to use voice input.",
        })
      } else if (name === "NotFoundError") {
        setError({ code: "no_microphone", message: "No microphone was found on this device." })
      } else {
        setError({ code: "recording_failed", message: "Couldn't access the microphone. Please try again." })
      }
      setState("error")
      return
    }

    streamRef.current = stream
    chunksRef.current = []

    const mimeType = pickSupportedMimeType()
    let recorder: MediaRecorder
    try {
      recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)
    } catch {
      setError({ code: "recording_failed", message: "Recording isn't supported in this browser." })
      setState("error")
      stopStream()
      return
    }

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data)
    }
    recorder.onerror = () => {
      setError({ code: "recording_failed", message: "Recording failed unexpectedly. Please try again." })
      setState("error")
      stopStream()
      stopTimer()
    }

    mediaRecorderRef.current = recorder
    recorder.start()
    setState("recording")
    setElapsedMs(0)
    startedAtRef.current = Date.now()
    timerRef.current = setInterval(() => setElapsedMs(Date.now() - startedAtRef.current), 200)
  }, [stopStream, stopTimer])

  /** Stops recording, uploads the clip, and resolves with the transcript (or null on any failure). */
  const stopRecording = useCallback((): Promise<string | null> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current
      if (!recorder || state !== "recording") {
        resolve(null)
        return
      }

      stopTimer()

      recorder.onstop = async () => {
        stopStream()
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" })
        chunksRef.current = []

        if (blob.size === 0) {
          setError({ code: "empty_audio", message: "No audio was captured. Please try again." })
          setState("error")
          resolve(null)
          return
        }

        setState("processing")
        try {
          const result = USE_MOCK ? await transcribeAudioMock(blob) : await transcribeAudio(blob)
          setState("idle")
          resolve(result.text)
        } catch (err) {
          const message =
            err instanceof ApiError ? err.message : "Couldn't transcribe the audio. Please try again."
          setError({ code: "transcription_failed", message })
          setState("error")
          resolve(null)
        }
      }

      recorder.stop()
    })
  }, [state, stopStream, stopTimer])

  const cancelRecording = useCallback(() => {
    stopTimer()
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.onstop = null
      mediaRecorderRef.current.stop()
    }
    stopStream()
    chunksRef.current = []
    setState("idle")
    setElapsedMs(0)
  }, [stopStream, stopTimer])

  const reset = useCallback(() => {
    setError(null)
    setState("idle")
  }, [])

  return { state, elapsedMs, error, startRecording, stopRecording, cancelRecording, reset }
}
