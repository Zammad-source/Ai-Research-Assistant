import logging

from groq import Groq

from app.config import get_settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)
settings = get_settings()

_groq_client = None

STT_LANGUAGE_CODES = {
    "ur": "ur",
    "sd": "sd",
    "pa": "pa",
    "ps": "ps",
    "en": "en",
}


class SpeechToTextError(AppException):
    pass


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.groq_api_key)
    return _groq_client


def transcribe_audio(audio_file_path: str, language_code: str | None = None) -> str:
    try:
        client = _get_groq_client()
        whisper_lang = STT_LANGUAGE_CODES.get(language_code) if language_code else None

        with open(audio_file_path, "rb") as audio_file:
            kwargs = {"file": audio_file, "model": "whisper-large-v3"}
            if whisper_lang:
                kwargs["language"] = whisper_lang
            transcript = client.audio.transcriptions.create(**kwargs)

        text = transcript.text.strip()
        if not text:
            raise SpeechToTextError("No speech could be detected in the audio.")
        return text

    except SpeechToTextError:
        raise
    except FileNotFoundError:
        raise SpeechToTextError("Audio file not found.")
    except Exception as e:
        logger.exception(f"STT transcription failed: {e}")
        raise SpeechToTextError("Could not transcribe audio. Please try again.")


def transcribe_audio_with_language(audio_file_path: str) -> dict:
    """
    Transcribes without a language hint and asks Whisper to also report
    the detected language. Used by the frontend-facing
    /api/voice/transcribe endpoint (frontend doesn't send a language hint).
    """
    try:
        client = _get_groq_client()
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3",
                response_format="verbose_json",
            )

        text = (transcript.text or "").strip()
        if not text:
            raise SpeechToTextError("No speech could be detected in the audio.")

        language = getattr(transcript, "language", None)
        return {"text": text, "language": language}

    except SpeechToTextError:
        raise
    except FileNotFoundError:
        raise SpeechToTextError("Audio file not found.")
    except Exception as e:
        logger.exception(f"STT transcription failed: {e}")
        raise SpeechToTextError("Could not transcribe audio. Please try again.")