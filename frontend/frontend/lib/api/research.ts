import { apiClient } from "./client"
import type { ResearchQueryRequest, ResearchQueryResponse } from "@/types/api"

/**
 * Sends a research question to the backend.
 * Pass `conversationId: null` to start a new conversation - store the
 * response's `conversation_id` and reuse it on the next call in the
 * same thread.
 */
export function sendResearchQuery(
  query: string,
  conversationId: string | null,
  signal?: AbortSignal
): Promise<ResearchQueryResponse> {
  const payload: ResearchQueryRequest = { query, conversation_id: conversationId }
  return apiClient<ResearchQueryResponse>("/api/research/query", {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  })
}
