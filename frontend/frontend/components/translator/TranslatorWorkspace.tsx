"use client"

import { useRef, useEffect } from "react"
import { useTranslatorRoom } from "@/hooks/useTranslatorRoom"
import { RoomSetup } from "./RoomSetup"
import { TranslatorMessage } from "./TranslatorMessage"
import { ConnectionStatusIndicator } from "./ConnectionStatusIndicator"
import { TranslatorInput } from "./TranslatorInput"
import { Button } from "@/components/ui/button"
import { PhoneOff } from "lucide-react"

export function TranslatorWorkspace() {
  const {
    connectionStatus,
    messages,
    roomCode,
    isHost,
    createRoom,
    joinRoom,
    sendMessage,
    disconnect,
  } = useTranslatorRoom()

  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const isInRoom = connectionStatus === "connected" || connectionStatus === "connecting" || connectionStatus === "reconnecting"

  if (!isInRoom) {
    return (
      <div className="h-[calc(100dvh-4rem)] flex items-center justify-center">
        <RoomSetup onCreateRoom={createRoom} onJoinRoom={joinRoom} />
      </div>
    )
  }

  return (
    <section className="flex flex-col h-[calc(100dvh-4rem)] relative" aria-label="Translator chat">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between bg-background/80 backdrop-blur-md">
        <div>
          <h2 className="font-heading font-semibold text-sm">Translator Room</h2>
          {roomCode && <p className="text-xs text-muted-foreground font-mono">{roomCode}</p>}
        </div>
        <div className="flex items-center gap-3">
          <ConnectionStatusIndicator status={connectionStatus} />
          <Button variant="ghost" size="icon" onClick={disconnect} aria-label="Leave room">
            <PhoneOff className="h-4 w-4 text-destructive" aria-hidden="true" />
          </Button>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6" role="log" aria-live="polite">
        <div className="max-w-3xl mx-auto">
          {messages.length === 0 && (
            <div className="text-center text-muted-foreground text-sm py-12">
              {isHost ? "Waiting for your partner to join…" : "Say hello to start the conversation!"}
            </div>
          )}

          {messages.map((msg) => (
            <TranslatorMessage key={msg.id} message={msg} />
          ))}
        </div>
      </div>

      <TranslatorInput
        onSend={(text) => sendMessage(text, "urdu", "english")}
        disabled={connectionStatus !== "connected"}
      />
    </section>
  )
}