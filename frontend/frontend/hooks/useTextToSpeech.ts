"use client"

import { useCallback, useRef, useState } from "react"
import { requestSpeech } from "@/lib/api/voice"
import { requestSpeechMock } from "@/lib/api/mock-adapter"

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK_API === "true"

export type PlaybackState = "idle" | "loading" | "playing" | "paused" | "error"

/**
 * Plays a message's text as speech. Tries the backend TTS endpoint first;
 * if that fails or is unavailable — e.g. a regional voice (Saraiki) isn't
 * ready yet — falls back to the browser's built-in SpeechSynthesis so the
 * "Listen" control degrades gracefully instead of just breaking.
 * One instance is shared across all messages (in ResearchChat) so only
 * one audio stream ever plays at a time.
 */
export function useTextToSpeech() {
  const [state, setState] = useState<PlaybackState>("idle")
  const [activeMessageId, setActiveMessageId] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const objectUrlRef = useRef<string | null>(null)

  const revokeUrl = useCallback(() => {
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current)
      objectUrlRef.current = null
    }
  }, [])

  const stop = useCallback(() => {
    audioRef.current?.pause()
    audioRef.current = null
    revokeUrl()
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel()
    }
    setState("idle")
    setActiveMessageId(null)
  }, [revokeUrl])

  const playWithBrowserVoice = useCallback((text: string, messageId: string) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      setState("error")
      return
    }
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.onstart = () => setState("playing")
    utterance.onend = () => {
      setState("idle")
      setActiveMessageId(null)
    }
    utterance.onerror = () => {
      setState("error")
      setActiveMessageId(null)
    }
    window.speechSynthesis.speak(utterance)
    setActiveMessageId(messageId)
  }, [])

  const play = useCallback(
    async (text: string, messageId: string) => {
      // Same message already active — toggle pause/resume instead of restarting.
      if (activeMessageId === messageId && state === "playing") {
        if (audioRef.current) {
          audioRef.current.pause()
          setState("paused")
        } else if (typeof window !== "undefined" && "speechSynthesis" in window) {
          window.speechSynthesis.pause()
          setState("paused")
        }
        return
      }
      if (activeMessageId === messageId && state === "paused") {
        if (audioRef.current) {
          audioRef.current.play()
          setState("playing")
        } else if (typeof window !== "undefined" && "speechSynthesis" in window) {
          window.speechSynthesis.resume()
          setState("playing")
        }
        return
      }

      stop()
      setState("loading")
      setActiveMessageId(messageId)

      try {
        const audioBlob = USE_MOCK ? await requestSpeechMock() : await requestSpeech(text)

        const url = URL.createObjectURL(audioBlob)
        objectUrlRef.current = url
        const audio = new Audio(url)
        audioRef.current = audio
        audio.onended = () => {
          setState("idle")
          setActiveMessageId(null)
          revokeUrl()
        }
        audio.onerror = () => {
          setState("error")
          revokeUrl()
        }
        await audio.play()
        setState("playing")
      } catch {
        // Backend TTS unavailable/degraded — fall back to the browser's
        // own voice rather than failing the "Listen" action outright.
        playWithBrowserVoice(text, messageId)
      }
    },
    [activeMessageId, state, stop, playWithBrowserVoice, revokeUrl]
  )

  return { state, activeMessageId, play, stop }
}
