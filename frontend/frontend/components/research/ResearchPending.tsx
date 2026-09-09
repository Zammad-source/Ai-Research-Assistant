"use client"

import { Loader2 } from "lucide-react"

export function ResearchPending() {
  return (
    <div className="animate-spinner-fade-in flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-3 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      Researching your question...
    </div>
  )
}