import logging
import uuid
import os
import tempfile

from elevenlabs.client import ElevenLabs

from app.config import get_settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)
settings = get_settings()

_elevenlabs_client = None

DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # "Sarah" -- default account voice
TTS_MODEL = "eleven_multilingual_v2"

OUTPUT_DIR = "tts_output"


def _output_dir() -> str:
    """
    Where generated clips are written.

    Local and container platforms give us a writable working directory, but
    Vercel mounts the function bundle read-only and only allows writes under
    /tmp. Defaulting to the temp dir there keeps TTS working instead of
    failing with a bare "read-only file system" error. TTS_OUTPUT_DIR
    overrides both.
    """
    override = os.getenv("TTS_OUTPUT_DIR")
    if override:
        return override
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return os.path.join(tempfile.gettempdir(), OUTPUT_DIR)
    return OUTPUT_DIR


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

    output_dir = _output_dir()
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        logger.exception("TTS output directory %s is not writable: %s", output_dir, e)
        raise TextToSpeechError("Could not generate speech. Please try again.")

    if output_path is None:
        output_path = os.path.join(output_dir, f"{uuid.uuid4().hex}.mp3")

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


def discard_generated_file(path: str):
    """
    Delete a previously generated clip.

    Wire this to the response's BackgroundTask. Railway's free container has a
    1 GB disk, and these clips are never cleaned up otherwise, so a long-running
    demo eventually fills the volume -- which breaks TTS and logging with a
    confusing "no space left on device".
    """
    try:
        os.remove(path)
    except OSError as e:
        # Losing the race with another cleanup, or the file is already gone,
        # is not worth failing a response the user already received.
        logger.warning(f"Could not remove generated audio {path}: {e}")