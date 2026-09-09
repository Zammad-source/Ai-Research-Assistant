"use client"

import type { TranslatorMessage as TranslatorMessageType } from "@/types/translator"
import { cn } from "@/lib/utils"

interface TranslatorMessageProps {
  message: TranslatorMessageType
}

export function TranslatorMessage({ message }: TranslatorMessageProps) {
  const isSelf = message.role === "self"

  return (
    <div className={cn("flex mb-6", isSelf ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] md:max-w-[70%] px-4 py-3 rounded-2xl",
          isSelf
            ? "bg-primary text-white rounded-br-md"
            : "bg-card border border-border rounded-bl-md"
        )}
      >
        <p className={cn("text-sm md:text-base", message.isPending && "opacity-60")}>
          {message.originalText}
        </p>

        {message.translatedText && (
          <div
            className={cn(
              "mt-2 pt-2 border-t text-sm",
              isSelf ? "border-white/20 text-white/85" : "border-border text-muted-foreground"
            )}
          >
            <p className="text-xs opacity-70 mb-1">
              {message.originalLanguage} → {message.translatedLanguage}
            </p>
            {message.translatedText}
          </div>
        )}

        {message.isPending && (
          <p className="text-xs opacity-60 mt-2">Translating…</p>
        )}
      </div>
    </div>
  )
}