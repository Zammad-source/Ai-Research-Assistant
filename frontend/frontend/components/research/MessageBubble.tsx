"use client";

import { useState } from "react";
import { User, Sparkles, Copy, Check, Volume2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import type { ResearchMessage } from "@/types/research";
import { SourceCard } from "./SourceCard";
import { useTextToSpeech } from "@/hooks/useTextToSpeech";
import { getTextDirection, isRtlText } from "@/lib/rtl";

export function MessageBubble({ message }: { message: ResearchMessage }) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);
  const { play, stop, activeMessageId, state } = useTextToSpeech();

  const isPlaying = activeMessageId === message.id && state === "playing";
  const direction = getTextDirection(message.content);
  const isRtl = isRtlText(message.content);

  function handleCopy() {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleAudioToggle() {
    if (isPlaying) {
      stop();
    } else {
      play(message.content, message.id);
    }
  }

  return (
    <div className={cn("flex w-full mb-8 group animate-message-in", isUser ? "justify-end" : "justify-start")}>
      <div className={cn("flex gap-4 max-w-[92%] md:max-w-[85%]", isUser ? "flex-row-reverse" : "flex-row")}>

        <div
          aria-hidden="true"
          className={cn(
            "flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-full shadow-sm",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-card border border-border/60 text-primary"
          )}
        >
          {isUser ? <User className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
        </div>

        <div className="flex flex-col gap-3 min-w-0 flex-1">
          <div
            dir={direction}
            className={cn(
              "relative px-5 py-3.5 text-sm md:text-base leading-relaxed rounded-3xl shadow-sm break-words transition-shadow",
              isRtl ? "font-urdu text-right" : "text-left",
              isUser
                ? "bg-primary text-primary-foreground rounded-tr-sm"
                : "bg-card border border-border/60 text-foreground rounded-tl-sm shadow-black/[0.02]"
            )}
          >
            <span className="sr-only">{isUser ? "You said: " : "Lisaan said: "}</span>
            {message.content}
          </div>

          {!isUser && message.sources && message.sources.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
              {message.sources.map((source, idx) => (
                <SourceCard key={idx} source={source} index={idx + 1} />
              ))}
            </div>
          )}

          {!isUser && (
            <div className="flex items-center gap-1 text-muted-foreground mt-1 opacity-80 group-hover:opacity-100 transition-opacity">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopy}
                aria-label={copied ? "Copied" : "Copy response"}
                className="h-8 px-2.5 text-xs gap-1.5 hover:text-foreground hover:bg-muted rounded-lg transition-all duration-150 hover:scale-105 active:scale-95"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-green-500 animate-fade-in" aria-hidden="true" /> : <Copy className="h-3.5 w-3.5" aria-hidden="true" />}
                <span>{copied ? "Copied" : "Copy"}</span>
              </Button>

              <Button
                variant="ghost"
                size="sm"
                onClick={handleAudioToggle}
                aria-label={isPlaying ? "Pause response" : "Listen to response"}
                className={cn(
                  "h-8 px-2.5 text-xs gap-1.5 rounded-lg hover:bg-muted transition-all duration-150 hover:scale-105 active:scale-95",
                  isPlaying ? "text-primary font-medium" : "hover:text-foreground"
                )}
              >
                <Volume2 className={cn("h-3.5 w-3.5", isPlaying && "animate-pulse text-primary")} aria-hidden="true" />
                <span>{isPlaying ? "Pause" : "Listen"}</span>
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}