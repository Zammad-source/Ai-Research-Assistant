import os
import logging
import tempfile

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.speech_to_text import transcribe_audio
from app.services.text_to_speech import generate_speech

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/test-stt")
async def test_stt(audio: UploadFile = File(...), language_code: str = Form(None)):
    """
    Upload an audio file (wav/mp3/m4a) and get back the transcribed text.
    Test with Postman: form-data, key 'audio' (type File), optional key 'language_code'.
    """
    suffix = os.path.splitext(audio.filename)[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        text = transcribe_audio(tmp_path, language_code)
        return {"success": True, "transcribed_text": text}
    finally:
        os.remove(tmp_path)


class TTSTestRequest(BaseModel):
    text: str


@router.post("/test-tts")
async def test_tts(payload: TTSTestRequest):
    """
    Send text, get back a playable/downloadable mp3 file.
    """
    output_path = generate_speech(payload.text)
    return FileResponse(output_path, media_type="audio/mpeg", filename="speech.mp3")