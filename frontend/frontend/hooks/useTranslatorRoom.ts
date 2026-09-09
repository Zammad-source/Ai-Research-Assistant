"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { TranslatorSocket } from "@/lib/websocket/translatorSocket"
import { MockTranslatorSocket } from "@/lib/websocket/mockTranslatorSocket"
import type { ConnectionStatus, TranslatorMessage, TranslatorWebSocketEvent } from "@/types/translator"

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK_API === "true"

function createId() {
  return Math.random().toString(36).slice(2, 10)
}

export function useTranslatorRoom() {
  const socketRef = useRef<TranslatorSocket | MockTranslatorSocket | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected")
  const [messages, setMessages] = useState<TranslatorMessage[]>([])
  const [roomCode, setRoomCode] = useState<string | null>(null)
  const [isHost, setIsHost] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    return () => {
      socketRef.current?.disconnect()
    }
  }, [])

  const createRoom = useCallback(() => {
    const code = Math.floor(100000 + Math.random() * 900000).toString()
    const socket = USE_MOCK ? new MockTranslatorSocket() : new TranslatorSocket()
    socketRef.current = socket

    socket.onStatusChange((status) => {
      switch (status) {
        case "open":
          setConnectionStatus("connected")
          break
        case "connecting":
          setConnectionStatus("connecting")
          break
        case "reconnecting":
          setConnectionStatus("reconnecting")
          break
        case "error":
        case "closed":
          setConnectionStatus("error")
          break
        default:
          setConnectionStatus("disconnected")
      }
    })

    socket.onMessage((event: TranslatorWebSocketEvent) => {
      if (event.type === "message") {
        const msg: TranslatorMessage = {
          id: event.message_id,
          role: "partner",
          originalText: event.original_text,
          translatedText: event.translated_text,
          originalLanguage: event.original_language,
          translatedLanguage: event.translated_language,
          createdAt: event.created_at,
        }
        setMessages((prev) => [...prev, msg])
      }
    })

    setRoomCode(code)
    setIsHost(true)
    setMessages([])
    setError(null)
    socket.connect(code, true)
    return code
  }, [])

  const joinRoom = useCallback((code: string) => {
    const socket = USE_MOCK ? new MockTranslatorSocket() : new TranslatorSocket()
    socketRef.current = socket

    socket.onStatusChange((status) => {
      switch (status) {
        case "open":
          setConnectionStatus("connected")
          break
        case "connecting":
          setConnectionStatus("connecting")
          break
        case "reconnecting":
          setConnectionStatus("reconnecting")
          break
        case "error":
        case "closed":
          setConnectionStatus("error")
          break
        default:
          setConnectionStatus("disconnected")
      }
    })

    socket.onMessage((event: TranslatorWebSocketEvent) => {
      if (event.type === "message") {
        const msg: TranslatorMessage = {
          id: event.message_id,
          role: "partner",
          originalText: event.original_text,
          translatedText: event.translated_text,
          originalLanguage: event.original_language,
          translatedLanguage: event.translated_language,
          createdAt: event.created_at,
        }
        setMessages((prev) => [...prev, msg])
      }
    })

    setRoomCode(code)
    setIsHost(false)
    setMessages([])
    setError(null)
    socket.connect(code, false)
  }, [])

  const sendMessage = useCallback(
    (text: string, originalLanguage: string, translatedLanguage: string) => {
      const socket = socketRef.current
      if (!socket) return

      const msg: TranslatorMessage = {
        id: createId(),
        role: "self",
        originalText: text,
        translatedText: "",
        originalLanguage: originalLanguage as TranslatorMessage["originalLanguage"],
        translatedLanguage: translatedLanguage as TranslatorMessage["translatedLanguage"],
        createdAt: new Date().toISOString(),
        isPending: true,
      }
      setMessages((prev) => [...prev, msg])
      socket.sendText(text, originalLanguage, translatedLanguage)
    },
    []
  )

  const disconnect = useCallback(() => {
    socketRef.current?.disconnect()
    setConnectionStatus("disconnected")
    setRoomCode(null)
    setMessages([])
    setIsHost(false)
  }, [])

  return {
    connectionStatus,
    messages,
    roomCode,
    isHost,
    error,
    createRoom,
    joinRoom,
    sendMessage,
    disconnect,
  }
}