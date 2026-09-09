"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { sendResearchQuery } from "@/lib/api/research"
import { sendResearchQueryMock } from "@/lib/api/mock-adapter"
import { ApiError } from "@/lib/api/client"
import { useConversationsStore } from "@/store/conversations"
import type { ResearchMessage } from "@/types/research"

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK_API === "true"

function createId() {
  return Math.random().toString(36).slice(2, 10)
}

/**
 * Same responsibility as the Phase 2.3 version (mutation, retry, error
 * handling) but now backed by the shared conversations store instead of
 * local component state — so the Sidebar's list and this chat view are
 * always looking at the same data. The public shape callers use
 * (messages, isPending, error, sendQuery, regenerate, retry) is unchanged.
 */
export function useResearchConversation() {
  const queryClient = useQueryClient()

  const activeConversationId = useConversationsStore((s) => s.activeConversationId)
  const conversations = useConversationsStore((s) => s.conversations)
  const createConversation = useConversationsStore((s) => s.createConversation)
  const addMessage = useConversationsStore((s) => s.addMessage)
  const removeMessage = useConversationsStore((s) => s.removeMessage)
  const setBackendConversationId = useConversationsStore((s) => s.setBackendConversationId)

  const activeConversation = conversations.find((c) => c.id === activeConversationId) ?? null
  const messages = activeConversation?.messages ?? []
  const backendConversationId = activeConversation?.backendConversationId ?? null

  const mutation = useMutation({
    mutationFn: (query: string) =>
      USE_MOCK
        ? sendResearchQueryMock(query, backendConversationId)
        : sendResearchQuery(query, backendConversationId),
    retry: 2,
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 8000),
    onSuccess: (data) => {
      if (!activeConversationId) return
      setBackendConversationId(activeConversationId, data.conversation_id)
      addMessage(activeConversationId, {
        id: data.message_id,
        role: "assistant",
        content: data.answer,
        createdAt: data.created_at,
        sources: data.sources,
      })
      queryClient.invalidateQueries({ queryKey: ["research-conversation", data.conversation_id] })
    },
  })

  function sendQuery(query: string) {
    // First message on a fresh page load may have no active conversation
    // yet — create one lazily instead of forcing the user to click
    // "New Conversation" first.
    const conversationId = activeConversationId ?? createConversation()

    const userMessage: ResearchMessage = {
      id: createId(),
      role: "user",
      content: query,
      createdAt: new Date().toISOString(),
    }
    addMessage(conversationId, userMessage)
    mutation.mutate(query)
  }

  function regenerate(assistantMessageId: string) {
    if (!activeConversationId) return
    const idx = messages.findIndex((m) => m.id === assistantMessageId)
    if (idx === -1) return
    const priorUser = [...messages.slice(0, idx)].reverse().find((m) => m.role === "user")
    removeMessage(activeConversationId, assistantMessageId)
    if (priorUser) mutation.mutate(priorUser.content)
  }

  const errorMessage =
    mutation.error instanceof ApiError
      ? mutation.error.message
      : mutation.isError
        ? "Something went wrong. Please try again."
        : null

  return {
    messages,
    isPending: mutation.isPending,
    error: errorMessage,
    sendQuery,
    regenerate,
    retry: () => {
      if (typeof mutation.variables === "string") mutation.mutate(mutation.variables)
    },
  }
}