"use client";

import { useRef, useEffect } from "react";
import { useResearchConversation } from "@/hooks/useResearchConversation";
import { MessageBubble } from "./MessageBubble";
import { ResearchInput } from "./ResearchInput";
import { ResearchPending } from "./ResearchPending";
import { ResearchError } from "./ResearchError";

export function ResearchChat() {
  const { messages, isPending, error, sendQuery, retry } = useResearchConversation();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isPending]);

  return (
    <section className="flex flex-col h-[calc(100dvh-4rem)] relative" aria-label="Research Assistant chat">
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 py-6 md:px-8"
        role="log"
        aria-live="polite"
        aria-label="Conversation messages"
      >
        <div className="max-w-3xl mx-auto flex flex-col">

          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center min-h-[50dvh] text-center px-4">
              <h1 className="text-2xl font-heading font-semibold mb-2">
                What would you like to research today?
              </h1>
              <p className="text-muted-foreground text-sm max-w-md">
                Ask questions in Urdu, Roman Urdu, Sindhi, Punjabi, Pashto, or English.
              </p>
            </div>
          )}

          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}

          {isPending && (
            <div className="flex justify-start mb-8">
              <div className="max-w-[80%]">
                <ResearchPending />
              </div>
            </div>
          )}

          {error && (
            <div className="flex justify-start mb-8" role="alert">
              <div className="max-w-[80%]">
                <ResearchError message={error} onRetry={retry} />
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="sticky bottom-0 bg-background/80 backdrop-blur-md px-4 pt-2 pb-4 border-t border-border/40">
        <ResearchInput onSend={sendQuery} isPending={isPending} />
      </div>
    </section>
  );
}
