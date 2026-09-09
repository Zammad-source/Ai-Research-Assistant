import logging
import uuid
import os

from elevenlabs.client import ElevenLabs

from app.config import get_settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)
settings = get_settings()

_elevenlabs_client = None

DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # "Sarah" -- default account voice
TTS_MODEL = "eleven_multilingual_v2"

OUTPUT_DIR = "tts_output"


class TextToSpeechError(AppException):
    pass


def _get_elevenlabs_client():
    global _elevenlabs_client
    if _elevenlabs_client is None:
        _elevenlabs_client = ElevenLabs(api_key=settings.elevenlabs_api_key)
    return _elevenlabs_client


def generate_speech(text: str, output_path: str | None = None) -> str:
    if not text or not text.strip():
        raise TextToSpeechError("Cannot generate speech for empty text.")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, f"{uuid.uuid4().hex}.mp3")

    try:
        client = _get_elevenlabs_client()
        audio_generator = client.text_to_speech.convert(
            voice_id=DEFAULT_VOICE_ID,
            model_id=TTS_MODEL,
            text=text,
            output_format="mp3_44100_128",
            voice_settings={
                "stability": 0.5,
                "similarity_boost": 0.75,
                "speed": 0.9,
            },
        )

        with open(output_path, "wb") as f:
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)

        return output_path

    except Exception as e:
        logger.exception(f"TTS generation failed: {e}")
        raise TextToSpeechError("Could not generate speech. Please try again.")