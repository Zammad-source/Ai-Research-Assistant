"use client"

import { BrainCircuit, Check, PenLine, Search } from "lucide-react"
import type { ResearchStage } from "@/types/research"

const STAGES: { key: ResearchStage; label: string; icon: typeof Search }[] = [
  { key: "understanding", label: "Understanding your question", icon: BrainCircuit },
  { key: "searching", label: "Searching sources", icon: Search },
  { key: "generating", label: "Generating answer", icon: PenLine },
]

interface ResearchStatusProps {
  stage: ResearchStage
}

export function ResearchStatus({ stage }: ResearchStatusProps) {
  const activeIndex = STAGES.findIndex((s) => s.key === stage)
  const activeLabel = STAGES[activeIndex]?.label ?? ""

  return (
    <div
      className="flex flex-col gap-2 rounded-lg border border-border bg-card px-4 py-3"
      role="status"
      aria-live="polite"
      aria-label={`Research status: ${activeLabel}`}
    >
      {STAGES.map((s, i) => {
        const isDone = i < activeIndex
        const isActive = i === activeIndex
        const Icon = s.icon
        return (
          <div
            key={s.key}
            className={`flex items-center gap-2 text-sm transition-opacity ${
              isDone || isActive ? "opacity-100" : "opacity-40"
            }`}
          >
            <span
              aria-hidden="true"
              className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${
                isDone
                  ? "bg-blue-600 text-white"
                  : isActive
                    ? "bg-blue-100 text-blue-600 dark:bg-blue-950"
                    : "bg-muted text-muted-foreground"
              }`}
            >
              {isDone ? (
                <Check className="h-3 w-3" />
              ) : (
                <Icon className={`h-3 w-3 ${isActive ? "animate-pulse" : ""}`} />
              )}
            </span>
            <span className={isActive ? "font-medium text-foreground" : "text-muted-foreground"}>
              {s.label}
              {isActive && <span className="ml-0.5 animate-pulse" aria-hidden="true">...</span>}
            </span>
          </div>
        )
      })}
    </div>
  )
}