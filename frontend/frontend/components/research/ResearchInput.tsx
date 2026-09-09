"use client";

import { useState, useEffect } from "react";
import { ArrowUp, Mic, Square, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useVoiceInput } from "@/hooks/useVoiceInput";
import { getTextDirection, isRtlText } from "@/lib/rtl";
import { cn } from "@/lib/utils";

interface ResearchInputProps {
  onSend: (query: string) => void;
  isPending: boolean;
}

export function ResearchInput({ onSend, isPending }: ResearchInputProps) {
  const [input, setInput] = useState("");
  const { state, startRecording, stopRecording, cancelRecording } = useVoiceInput();

  const direction = getTextDirection(input);
  const isRtl = isRtlText(input);

  const isRecording = state === "recording";
  const isProcessingVoice = state === "processing" || state === "requesting-permission";

  // Escape cancels an in-progress recording (discards audio, no transcription).
  useEffect(() => {
    if (!isRecording) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        cancelRecording();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isRecording, cancelRecording]);

  function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    if (input.trim() && !isPending) {
      onSend(input);
      setInput("");
    }
  }

  async function handleMicClick() {
    if (isRecording) {
      const transcript = await stopRecording();
      if (transcript) {
        setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
      }
    } else {
      startRecording();
    }
  }

  function handleCancelRecording() {
    cancelRecording();
  }

  return (
    <div className="relative w-full max-w-3xl mx-auto pb-4">
      <form
        onSubmit={handleSubmit}
        className="relative flex items-center w-full p-2 bg-card/70 backdrop-blur-xl border border-border/60 rounded-[2rem] shadow-xl focus-within:ring-2 focus-within:ring-primary/20 transition-all duration-300"
      >
        {isRecording && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={handleCancelRecording}
            aria-label="Cancel recording"
            title="Cancel recording (Esc)"
            className="rounded-full shrink-0 h-10 w-10 text-muted-foreground transition-all duration-150 hover:scale-105 hover:bg-muted hover:text-foreground active:scale-95"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        )}

        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={handleMicClick}
          disabled={isPending || isProcessingVoice}
          aria-label={isRecording ? "Stop recording and use transcript" : "Start voice input"}
          className={cn(
            "rounded-full shrink-0 h-10 w-10 transition-all duration-150",
            isRecording
              ? "text-destructive bg-destructive/10 animate-recording-pulse"
              : "text-muted-foreground hover:text-primary hover:bg-primary/10 hover:scale-105 active:scale-95"
          )}
        >
          {isProcessingVoice ? (
            <Loader2 className="h-5 w-5 animate-spin text-primary" aria-hidden="true" />
          ) : isRecording ? (
            <Square className="h-5 w-5 fill-current" aria-hidden="true" />
          ) : (
            <Mic className="h-5 w-5" aria-hidden="true" />
          )}
        </Button>

        <input
          type="text"
          dir={direction}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          aria-label="Ask a research question"
          placeholder={
            isRecording
              ? "Listening... Speak now..."
              : isProcessingVoice
              ? "Processing audio..."
              : "Ask anything in Urdu, Roman Urdu, English..."
          }
          disabled={isPending || isRecording || isProcessingVoice}
          className={cn(
            "flex-1 bg-transparent border-none outline-none px-3 text-sm md:text-base placeholder:text-muted-foreground text-foreground disabled:opacity-50",
            isRtl && "text-right"
          )}
        />

        <Button
          type="submit"
          disabled={!input.trim() || isPending || isRecording}
          aria-label="Send message"
          size="icon"
          className="rounded-full shrink-0 bg-primary hover:bg-primary/90 text-white h-10 w-10 transition-transform active:scale-95"
        >
          <ArrowUp className="h-5 w-5" aria-hidden="true" />
        </Button>
      </form>

      <div className="text-center mt-3 text-xs font-medium text-muted-foreground/70" role="status" aria-live="polite">
        {isRecording
          ? "🔴 Recording audio... Click the square button to use it, X or Esc to cancel."
          : "Lisaan auto-detects Urdu, Sindhi, Punjabi, Pashto, and English."}
      </div>
    </div>
  );
}