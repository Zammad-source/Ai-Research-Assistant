import type { TranslatorWebSocketEvent } from "@/types/translator"

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000"

export type TranslatorSocketStatus = "idle" | "connecting" | "open" | "closing" | "closed" | "reconnecting" | "error"

type MessageHandler = (event: TranslatorWebSocketEvent) => void
type StatusHandler = (status: TranslatorSocketStatus) => void

interface PendingMessage {
  type: string
  payload: unknown
}

export class TranslatorSocket {
  private ws: WebSocket | null = null
  private pendingMessages: PendingMessage[] = []
  private messageHandlers = new Set<MessageHandler>()
  private statusHandlers = new Set<StatusHandler>()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private shouldReconnect = true
  private currentRoomCode: string | null = null

  get status(): TranslatorSocketStatus {
    if (this.ws) {
      switch (this.ws.readyState) {
        case WebSocket.CONNECTING:
          return this.reconnectAttempts > 0 ? "reconnecting" : "connecting"
        case WebSocket.OPEN:
          return "open"
        case WebSocket.CLOSING:
          return "closing"
        case WebSocket.CLOSED:
          return "closed"
      }
    }
    return "idle"
  }

  connect(roomCode: string, isHost: boolean): void {
    this.currentRoomCode = roomCode
    this.shouldReconnect = true
    this.reconnectAttempts = 0
    this.pendingMessages = []
    this.openSocket(roomCode, isHost)
  }

  private openSocket(roomCode: string, isHost: boolean): void {
    const url = `${WS_BASE}/ws/translator/${roomCode}?is_host=${isHost}`
    this.setStatus(this.reconnectAttempts > 0 ? "reconnecting" : "connecting")

    try {
      this.ws = new WebSocket(url)
    } catch {
      this.handleError(new Error("WebSocket connection failed"))
      return
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0
      this.setStatus("open")
      this.flushPendingMessages()
    }

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const parsed = JSON.parse(event.data) as TranslatorWebSocketEvent
        this.messageHandlers.forEach((handler) => handler(parsed))
      } catch {
        // Ignore malformed messages
      }
    }

    this.ws.onclose = () => {
      if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.scheduleReconnect(roomCode, isHost)
      } else {
        this.setStatus("closed")
      }
    }

    this.ws.onerror = () => {
      this.setStatus("error")
    }
  }

  private scheduleReconnect(roomCode: string, isHost: boolean): void {
    this.reconnectAttempts++
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000)
    this.setStatus("reconnecting")

    this.reconnectTimer = setTimeout(() => {
      this.openSocket(roomCode, isHost)
    }, delay)
  }

  private flushPendingMessages(): void {
    const toSend = [...this.pendingMessages]
    this.pendingMessages = []

    for (const msg of toSend) {
      this.send(msg.type, msg.payload)
    }
  }

  send(type: string, payload: unknown): void {
    if (this.status === "open" && this.ws) {
      this.ws.send(JSON.stringify({ type, ...(payload as object) }))
    } else {
      this.pendingMessages.push({ type, payload })
    }
  }

  sendText(text: string, originalLanguage: string, translatedLanguage: string): void {
    this.send("message", {
      original_text: text,
      original_language: originalLanguage,
      translated_language: translatedLanguage,
    })
  }

  disconnect(): void {
    this.shouldReconnect = false
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.ws?.close()
    this.pendingMessages = []
    this.currentRoomCode = null
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler)
    return () => this.messageHandlers.delete(handler)
  }

  onStatusChange(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler)
    return () => this.statusHandlers.delete(handler)
  }

  private setStatus(status: TranslatorSocketStatus): void {
    this.statusHandlers.forEach((handler) => handler(status))
  }

  private handleError(error: Error): void {
    console.error("Translator socket error:", error)
    this.setStatus("error")
  }
}