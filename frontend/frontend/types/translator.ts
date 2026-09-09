export type TranslatorRole = "self" | "partner"

export type TranslatorLanguage = "urdu" | "punjabi" | "sindhi" | "pashto" | "english"

export type ConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "error"

export interface TranslatorMessage {
  id: string
  role: TranslatorRole
  originalText: string
  translatedText: string
  originalLanguage: TranslatorLanguage
  translatedLanguage: TranslatorLanguage
  createdAt: string
  isPending?: boolean
}

export interface TranslatorRoom {
  code: string
  createdAt: string
  isHost: boolean
  partnerConnected: boolean
}

export interface WebSocketMessageEvent {
  type: "message"
  message_id: string
  original_text: string
  translated_text: string
  original_language: TranslatorLanguage
  translated_language: TranslatorLanguage
  created_at: string
}

export interface WebSocketTranslationEvent {
  type: "translation_status"
  status: "translating" | "translated"
  message_id: string
}

export interface WebSocketAudioEvent {
  type: "audio"
  message_id: string
  audio_base64?: string
  audio_url?: string
}

export interface WebSocketConnectionEvent {
  type: "connection"
  status: "connected" | "disconnected"
  participant: TranslatorRole
}

export interface WebSocketErrorEvent {
  type: "error"
  code: string
  message: string
}

export type TranslatorWebSocketEvent =
  | WebSocketMessageEvent
  | WebSocketTranslationEvent
  | WebSocketAudioEvent
  | WebSocketConnectionEvent
  | WebSocketErrorEvent