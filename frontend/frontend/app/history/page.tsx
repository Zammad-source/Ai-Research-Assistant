"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { MessageSquare } from "lucide-react"
import { useConversationsStore } from "@/store/conversations"

export default function HistoryPage() {
  const router = useRouter()
  const [mounted, setMounted] = useState(false)
  const conversations = useConversationsStore((s) => s.conversations)
  const switchConversation = useConversationsStore((s) => s.switchConversation)

  // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional: delays render until client mount to avoid SSR/localStorage hydration mismatch
useEffect(() => setMounted(true), [])

  function openConversation(id: string) {
    switchConversation(id)
    router.push("/research")
  }

  if (!mounted) return null

  if (conversations.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center text-muted-foreground">
        <MessageSquare className="h-8 w-8 opacity-40" />
        <p className="text-lg font-medium text-foreground">No conversations yet</p>
        <p className="max-w-sm text-sm">Start a research question and it&apos;ll show up here.</p>
      </div>
    )
  }

  const sorted = [...conversations].sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1))

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 sm:px-8">
      <h1 className="mb-6 text-xl font-semibold text-foreground">History</h1>
      <div className="flex flex-col gap-2">
        {sorted.map((c) => {
          const lastMessage = c.messages[c.messages.length - 1]
          return (
            <button
              key={c.id}
              type="button"
              onClick={() => openConversation(c.id)}
              className="flex flex-col gap-1 rounded-lg border border-border bg-card p-4 text-left transition-colors hover:bg-muted"
            >
              <p className="truncate text-sm font-medium text-foreground">{c.title}</p>
              {lastMessage && (
                <p className="line-clamp-1 text-xs text-muted-foreground">{lastMessage.content}</p>
              )}
              <p className="text-[11px] text-muted-foreground">{new Date(c.updatedAt).toLocaleString()}</p>
            </button>
          )
        })}
      </div>
    </div>
  )
}