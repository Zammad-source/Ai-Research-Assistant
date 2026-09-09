"use client"

import { useState } from "react"
import { ArrowUp, Mic, Square, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useVoiceInput } from "@/hooks/useVoiceInput"
import { cn } from "@/lib/utils"

interface TranslatorInputProps {
  onSend: (text: string) => void
  disabled?: boolean
}

const LANGUAGE_OPTIONS = [
  { value: "urdu", label: "Urdu" },
  { value: "punjabi", label: "Punjabi" },
  { value: "sindhi", label: "Sindhi" },
  { value: "pashto", label: "Pashto" },
  { value: "english", label: "English" },
]

export function TranslatorInput({ onSend, disabled }: TranslatorInputProps) {
  const [input, setInput] = useState("")
  const [myLanguage, setMyLanguage] = useState("urdu")
  const [partnerLanguage, setPartnerLanguage] = useState("english")
  const { state, startRecording, stopRecording, cancelRecording } = useVoiceInput()

  const isRecording = state === "recording"
  const isProcessing = state === "processing" || state === "requesting-permission"

  function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault()
    if (input.trim() && !disabled) {
      onSend(input.trim())
      setInput("")
    }
  }

  async function handleMicClick() {
    if (isRecording) {
      const transcript = await stopRecording()
      if (transcript) {
        setInput((prev) => (prev ? `${prev} ${transcript}` : transcript))
      }
    } else {
      startRecording()
    }
  }

  return (
    <div className="border-t border-border bg-background/80 backdrop-blur-md p-4">
      <div className="flex gap-2 mb-3">
        <select
          value={myLanguage}
          onChange={(e) => setMyLanguage(e.target.value)}
          aria-label="Your language"
          className="px-3 py-1.5 bg-card border border-border rounded-lg text-sm"
        >
          {LANGUAGE_OPTIONS.map((lang) => (
            <option key={lang.value} value={lang.value}>
              {lang.label}
            </option>
          ))}
        </select>

        <span className="text-muted-foreground self-center">→</span>

        <select
          value={partnerLanguage}
          onChange={(e) => setPartnerLanguage(e.target.value)}
          aria-label="Partner's language"
          className="px-3 py-1.5 bg-card border border-border rounded-lg text-sm"
        >
          {LANGUAGE_OPTIONS.map((lang) => (
            <option key={lang.value} value={lang.value}>
              {lang.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-2">
        {isRecording && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={cancelRecording}
            aria-label="Cancel recording"
            className="rounded-full shrink-0 h-10 w-10"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        )}

        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={handleMicClick}
          disabled={disabled || isProcessing}
          aria-label={isRecording ? "Stop recording" : "Start voice input"}
          className={cn(
            "rounded-full shrink-0 h-10 w-10",
            isRecording ? "text-destructive bg-destructive/10" : "text-muted-foreground hover:text-primary"
          )}
        >
          {isRecording ? <Square className="h-4 w-4 fill-current" aria-hidden="true" /> : <Mic className="h-4 w-4" aria-hidden="true" />}
        </Button>

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          placeholder={isRecording ? "Listening…" : "Type a message…"}
          disabled={disabled || isRecording || isProcessing}
          aria-label="Message to translate"
          className="flex-1 px-4 py-2.5 bg-card border border-border rounded-full text-sm outline-none focus:ring-2 focus:ring-primary/20"
        />

        <Button
          type="button"
          size="icon"
          onClick={handleSubmit}
          disabled={!input.trim() || disabled || isRecording}
          aria-label="Send message"
          className="rounded-full shrink-0 h-10 w-10 bg-primary hover:bg-primary/90 text-white"
        >
          <ArrowUp className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  )
}