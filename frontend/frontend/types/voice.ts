export type RecordingState =
  | "idle"
  | "requesting-permission"
  | "recording"
  | "processing"
  | "error"

export type VoiceErrorCode =
  | "permission_denied"
  | "no_microphone"
  | "recording_failed"
  | "transcription_failed"
  | "empty_audio"
  | "playback_failed"
  | "network_error"
  | "timeout"

export interface VoiceError {
  code: VoiceErrorCode
  message: string
}

export interface TranscriptionResponse {
  text: string
  language?: string
}
