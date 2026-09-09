import logging
import threading

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
from groq import Groq

from app.config import get_settings
from app.core.exceptions import TranslationError

logger = logging.getLogger(__name__)
settings = get_settings()

NLLB_LANG_CODES = {
    "ur": "urd_Arab",
    "sd": "snd_Arab",
    "pa": "pnb_Arab",
    "ps": "pbt_Arab",
    "en": "eng_Latn",
}

_model = None
_tokenizer = None
_model_lock = threading.Lock()

_groq_client = None


def _load_nllb_model():
    global _model, _tokenizer
    if _model is not None:
        return
    with _model_lock:
        if _model is not None:
            return
        logger.info(f"Loading NLLB model: {settings.nllb_model_name} ...")
        _tokenizer = AutoTokenizer.from_pretrained(settings.nllb_model_name)
        _model = AutoModelForSeq2SeqLM.from_pretrained(settings.nllb_model_name)
        _model.eval()
        logger.info("NLLB model loaded successfully.")


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.groq_api_key)
    return _groq_client


def _translate_with_nllb(text: str, src_code: str, tgt_code: str) -> str:
    _load_nllb_model()
    _tokenizer.src_lang = src_code
    inputs = _tokenizer(text, return_tensors="pt")
    forced_bos_token_id = _tokenizer.convert_tokens_to_ids(tgt_code)

    with torch.no_grad():
        generated_tokens = _model.generate(
            **inputs,
            forced_bos_token_id=forced_bos_token_id,
            max_length=512,
        )

    return _tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0].strip()

def _translate_with_groq(text: str, source_lang_name: str, target_lang_name: str) -> str:
    client = _get_groq_client()

    script_instruction = ""
    if target_lang_name == "Roman Urdu":
        script_instruction = (
            " IMPORTANT: Write the output using ONLY Latin/English alphabet "
            "letters (transliteration), exactly like casual Roman Urdu texting "
            "(e.g. 'yeh aik acha mulk hai'). Do NOT use Urdu/Arabic script "
            "(Nastaliq) at all, even though the language is Urdu."
        )

    prompt = (
        f"Translate the following {source_lang_name} text into {target_lang_name}."
        f"{script_instruction} "
        f"Return ONLY the translation, no explanation, no quotes.\n\n"
        f"Text: {text}"
    )
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
        temperature=0.3,
        extra_body={"reasoning_effort": "low"},
    )
    return response.choices[0].message.content.strip()



def translate_text(text: str, source_lang_code: str, target_lang_code: str) -> str:
    if not text or not text.strip():
        raise TranslationError("Cannot translate empty text.")

    if source_lang_code == target_lang_code:
        return text

    try:
        lang_names = {
            "en": "English", "ur": "Urdu", "sd": "Sindhi",
            "pa": "Punjabi", "ps": "Pashto", "ur-roman": "Roman Urdu",
        }

        if source_lang_code == "ur-roman" or target_lang_code == "ur-roman":
            source_name = lang_names.get(source_lang_code, source_lang_code)
            target_name = lang_names.get(target_lang_code, target_lang_code)
            return _translate_with_groq(text, source_name, target_name)

        src_nllb = NLLB_LANG_CODES.get(source_lang_code)
        tgt_nllb = NLLB_LANG_CODES.get(target_lang_code)

        if not src_nllb or not tgt_nllb:
            raise TranslationError(
                f"Unsupported language pair: {source_lang_code} -> {target_lang_code}"
            )

        return _translate_with_nllb(text, src_nllb, tgt_nllb)

    except TranslationError:
        raise
    except Exception as e:
        logger.exception(f"Translation failed: {e}")
        raise TranslationError("Translation failed. Please try again.")