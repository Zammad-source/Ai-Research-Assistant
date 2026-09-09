"use client"

import { AlertCircle, RotateCcw } from "lucide-react"

interface ResearchErrorProps {
  message: string
  onRetry: () => void
}

export function ResearchError({ message, onRetry }: ResearchErrorProps) {
  return (
    <div className="animate-fade-in flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="flex-1">
        <p>{message}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 inline-flex items-center gap-1 rounded-md border border-red-300 px-2 py-1 text-xs font-medium transition-all duration-150 hover:scale-105 hover:bg-red-100 active:scale-95 dark:border-red-800 dark:hover:bg-red-900/40"
        >
          <RotateCcw className="h-3 w-3" />
          Retry
        </button>
      </div>
    </div>
  )
}