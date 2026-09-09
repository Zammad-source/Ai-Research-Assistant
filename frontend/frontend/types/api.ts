import type { ResearchSource } from "./research"

export interface ResearchQueryRequest {
  conversation_id: string | null
  query: string
}

export interface ResearchQueryResponse {
  conversation_id: string
  message_id: string
  answer: string
  sources: ResearchSource[]
  created_at: string
}

export interface ApiErrorBody {
  error: {
    code: string
    message: string
  }
}