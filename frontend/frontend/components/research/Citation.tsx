"use client"

interface CitationProps {
  index: number
  onClick: () => void
}

/**
 * Small inline [n] marker rendered inside message text. Clicking it scrolls
 * the matching SourceCard into view (see MessageBubble's scrollToSource).
 */
export function Citation({ index, onClick }: CitationProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mx-0.5 inline-flex h-4 min-w-4 -translate-y-0.5 items-center justify-center rounded-full bg-blue-100 px-1 align-super text-[10px] font-medium text-blue-700 transition-colors hover:bg-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:hover:bg-blue-900"
      aria-label={`View source ${index}`}
    >
      {index}
    </button>
  )
}
