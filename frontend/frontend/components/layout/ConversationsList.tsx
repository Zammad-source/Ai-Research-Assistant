"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { MessageSquare, Trash2 } from "lucide-react"
import { useConversationsStore } from "@/store/conversations"

export function ConversationsList() {
  const router = useRouter()
  const [mounted, setMounted] = useState(false)
  const conversations = useConversationsStore((s) => s.conversations)
  const activeConversationId = useConversationsStore((s) => s.activeConversationId)
  const switchConversation = useConversationsStore((s) => s.switchConversation)
  const deleteConversation = useConversationsStore((s) => s.deleteConversation)

  // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional: delays render until client mount to avoid SSR/localStorage hydration mismatch
useEffect(() => setMounted(true), [])

  if (!mounted) return null

  if (conversations.length === 0) {
    return <p className="animate-fade-in px-3 text-sm text-muted-foreground">No conversations yet.</p>
  }

  function handleSelect(id: string) {
    switchConversation(id)
    router.push("/research")
  }

  return (
    <ul className="flex flex-col gap-0.5">
      {conversations.map((c, i) => (
        <li
          key={c.id}
          style={{ animationDelay: `${Math.min(i, 6) * 25}ms` }}
          className={`animate-sidebar-item-in group flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
            c.id === activeConversationId
              ? "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300"
              : "text-foreground hover:bg-muted"
          }`}
        >
          <button
            type="button"
            onClick={() => handleSelect(c.id)}
            aria-current={c.id === activeConversationId ? "true" : undefined}
            className="flex flex-1 items-center gap-2 truncate text-left min-h-[36px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
          >
            <MessageSquare className="h-3.5 w-3.5 shrink-0 opacity-60" aria-hidden="true" />
            <span className="truncate">{c.title}</span>
          </button>
          <button
            type="button"
            onClick={() => deleteConversation(c.id)}
            className="shrink-0 opacity-60 md:opacity-0 transition-all duration-150 hover:scale-110 hover:text-red-600 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded md:group-hover:opacity-100 h-8 w-8 flex items-center justify-center"
            aria-label={`Delete conversation: ${c.title}`}
          >
            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </li>
      ))}
    </ul>
  )
}