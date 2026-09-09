"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { ResearchMessage } from "@/types/research"

export interface Conversation {
  id: string
  /** The backend's conversation_id — null until the first response comes back. */
  backendConversationId: string | null
  title: string
  messages: ResearchMessage[]
  createdAt: string
  updatedAt: string
}

interface ConversationsState {
  conversations: Conversation[]
  activeConversationId: string | null

  createConversation: () => string
  switchConversation: (id: string) => void
  deleteConversation: (id: string) => void
  addMessage: (conversationId: string, message: ResearchMessage) => void
  removeMessage: (conversationId: string, messageId: string) => void
  setBackendConversationId: (localId: string, backendId: string) => void
}

function createId() {
  return Math.random().toString(36).slice(2, 10)
}

function deriveTitle(firstUserMessage: ResearchMessage): string {
  const text = firstUserMessage.content.trim()
  return text.length > 48 ? `${text.slice(0, 48)}…` : text
}

/**
 * Single source of truth for conversations — the Sidebar's "Recent
 * Conversations" list and the ResearchChat view both read from this,
 * so switching or creating a conversation in one place is instantly
 * reflected in the other. Persisted to localStorage, so refreshing the
 * page doesn't lose history.
 */
export const useConversationsStore = create<ConversationsState>()(
  persist(
    (set) => ({
      conversations: [],
      activeConversationId: null,

      createConversation: () => {
        const id = createId()
        const now = new Date().toISOString()
        const conversation: Conversation = {
          id,
          backendConversationId: null,
          title: "New conversation",
          messages: [],
          createdAt: now,
          updatedAt: now,
        }
        set((state) => ({
          conversations: [conversation, ...state.conversations],
          activeConversationId: id,
        }))
        return id
      },

      switchConversation: (id) => set({ activeConversationId: id }),

      deleteConversation: (id) =>
        set((state) => {
          const remaining = state.conversations.filter((c) => c.id !== id)
          const wasActive = state.activeConversationId === id
          return {
            conversations: remaining,
            activeConversationId: wasActive ? (remaining[0]?.id ?? null) : state.activeConversationId,
          }
        }),

      addMessage: (conversationId, message) =>
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === conversationId
              ? {
                  ...c,
                  messages: [...c.messages, message],
                  updatedAt: new Date().toISOString(),
                  title: c.messages.length === 0 && message.role === "user" ? deriveTitle(message) : c.title,
                }
              : c
          ),
        })),

      removeMessage: (conversationId, messageId) =>
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === conversationId ? { ...c, messages: c.messages.filter((m) => m.id !== messageId) } : c
          ),
        })),

      setBackendConversationId: (localId, backendId) =>
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === localId ? { ...c, backendConversationId: backendId } : c
          ),
        })),
    }),
    {
      name: "lisaan-research-conversations",
    }
  )
)