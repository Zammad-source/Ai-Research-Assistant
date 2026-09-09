import type { TranslatorWebSocketEvent } from "@/types/translator"

type MessageHandler = (event: TranslatorWebSocketEvent) => void
type StatusHandler = (status: string) => void

export class MockTranslatorSocket {
  private messageHandlers = new Set<MessageHandler>()
  private statusHandlers = new Set<StatusHandler>()
  private currentStatus = "idle"

  connect(roomCode: string, isHost: boolean): void {
    this.setStatus("connecting")
    setTimeout(() => {
      this.setStatus("open")
      this.emit({
        type: "connection",
        status: "connected",
        participant: "partner",
      })
    }, 1000)
  }

  send(type: string, payload: unknown): void {
    if (type === "message") {
      const msg = payload as { original_text: string }
      // Simulate partner reply after 1.5s
      setTimeout(() => {
        this.emit({
          type: "message",
          message_id: Math.random().toString(36).slice(2, 10),
          original_text: "This is a simulated partner reply.",
          translated_text: msg.original_text,
          original_language: "english",
          translated_language: "urdu",
          created_at: new Date().toISOString(),
        })
      }, 1500)
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
    this.setStatus("closed")
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler)
    return () => this.messageHandlers.delete(handler)
  }

  onStatusChange(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler)
    return () => this.statusHandlers.delete(handler)
  }

  private emit(event: TranslatorWebSocketEvent): void {
    this.messageHandlers.forEach((handler) => handler(event))
  }

  private setStatus(status: string): void {
    this.currentStatus = status
    this.statusHandlers.forEach((handler) => handler(status))
  }
}