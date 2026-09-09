export type MessageRole = "user" | "assistant"

export type ResearchStage = "understanding" | "searching" | "generating"

export interface ResearchSource {
  id: string
  title: string
  domain: string
  url: string
  snippet: string
}

export interface ResearchMessage {
  id: string
  role: MessageRole
  content: string
  createdAt: string
  /** Only present on assistant messages that cited sources. */
  sources?: ResearchSource[]
}