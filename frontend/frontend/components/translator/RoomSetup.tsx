"use client"

import { useState } from "react"
import { Copy, Phone, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface RoomSetupProps {
  onCreateRoom: () => void
  onJoinRoom: (code: string) => void
  roomCode?: string | null
  isHost?: boolean
}

export function RoomSetup({ onCreateRoom, onJoinRoom, roomCode, isHost }: RoomSetupProps) {
  const [joinCode, setJoinCode] = useState("")
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    if (!roomCode) return
    navigator.clipboard.writeText(roomCode)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="max-w-md mx-auto flex flex-col gap-6 p-6">
      <div className="text-center">
        <h2 className="text-2xl font-heading font-semibold mb-2">Translator Mode</h2>
        <p className="text-muted-foreground text-sm">
          Communicate with someone in a different language in real time.
        </p>
      </div>

      <div className="flex flex-col gap-4">
        <Button
          onClick={onCreateRoom}
          className="w-full py-6 text-base font-medium"
          aria-label="Create a new translation room"
        >
          <Plus className="h-5 w-5 mr-2" aria-hidden="true" />
          Create a New Room
        </Button>

        {roomCode && isHost && (
          <div className="p-4 bg-card border border-border rounded-xl text-center animate-fade-in">
            <p className="text-sm text-muted-foreground mb-2">Share this code with your partner:</p>
            <div className="flex items-center justify-center gap-3">
              <span className="text-3xl font-mono font-bold tracking-widest">{roomCode}</span>
              <Button variant="ghost" size="icon" onClick={handleCopy} aria-label="Copy room code">
                <Copy className={cn("h-4 w-4", copied && "text-primary")} aria-hidden="true" />
              </Button>
            </div>
            {copied && <p className="text-xs text-primary mt-2">Copied!</p>}
          </div>
        )}

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-border" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-background px-2 text-muted-foreground">or</span>
          </div>
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value.replace(/\D/g, ""))}
            placeholder="Enter 6-digit code"
            aria-label="Room code"
            className="flex-1 px-4 py-3 bg-card border border-border rounded-xl text-center text-lg font-mono tracking-widest outline-none focus:ring-2 focus:ring-primary/20"
          />
          <Button
            onClick={() => joinCode.length === 6 && onJoinRoom(joinCode)}
            disabled={joinCode.length !== 6}
            aria-label="Join room"
            className="px-4"
          >
            <Phone className="h-4 w-4 mr-2" aria-hidden="true" />
            Join
          </Button>
        </div>
      </div>
    </div>
  )
}