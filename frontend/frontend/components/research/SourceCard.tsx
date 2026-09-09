"use client"

import { forwardRef } from "react"
import { ExternalLink } from "lucide-react"
import type { ResearchSource } from "@/types/research"

interface SourceCardProps {
  source: ResearchSource
  index: number
}

export const SourceCard = forwardRef<HTMLDivElement, SourceCardProps>(function SourceCard(
  { source, index },
  ref
) {
  return (
    <div
      ref={ref}
      id={`source-${source.id}`}
      className="rounded-lg border border-border bg-card p-3 transition-all duration-150 hover:-translate-y-0.5 hover:shadow-md focus-within:ring-2 focus-within:ring-ring"
    >
      <div className="flex items-start gap-2">
        <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted text-[11px] font-medium text-muted-foreground" aria-hidden="true">
          {index}
        </span>
        <div className="min-w-0 flex-1">
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={source.title + " - opens in a new tab, source " + index}
            className="flex items-center gap-1 text-sm font-medium text-foreground hover:text-blue-600 focus-visible:outline-none rounded"
          >
            <span className="truncate">{source.title}</span>
            <ExternalLink className="h-3 w-3 shrink-0" aria-hidden="true" />
          </a>
          <p className="mt-0.5 text-xs text-muted-foreground">{source.domain}</p>
          <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{source.snippet}</p>
        </div>
      </div>
    </div>
  )
})