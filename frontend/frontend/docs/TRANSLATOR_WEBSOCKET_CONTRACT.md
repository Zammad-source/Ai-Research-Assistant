# Translator WebSocket Contract

## Endpoint

`ws://localhost:8000/ws/translator/{room_code}?is_host={true|false}`

## Events Sent by Client

### 1. Send Message

```json
{
  "type": "message",
  "original_text": "Hello",
  "original_language": "urdu",
  "translated_language": "english"
}