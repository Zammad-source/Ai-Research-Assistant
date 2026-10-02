import logging
import threading

from groq import Groq

from app.config import get_settings
from app.core.exceptions import TranslationError

logger = logging.getLogger(__name__)
settings = get_settings()

LANG_NAMES = {
    "en": "English",
    "ur": "Urdu",
    "sd": "Sindhi",
    "pa": "Punjabi",
    "ps": "Pashto",
    "ur-roman": "Roman Urdu",
}

# Target scripts that models get wrong unless told explicitly.
# Without these the model can emit Latin transliteration for Urdu,
# or the wrong Punjabi script.
SCRIPT_INSTRUCTIONS = {
    "ur": " Use Urdu script in its standard Urdu (Nastaliq/Arabic) alphabet.",
    "sd": " Use Sindhi in its standard Arabic-based Sindhi script.",
    "pa": " Use Punjabi in the Gurmukhi script (ਮੁਖੀ).",
    "ps": " Use Pashto in its standard Arabic-based Pashto script.",
    "ur-roman": (
        " Write the output using ONLY Latin/English alphabet letters"
        " (transliteration), exactly like casual Roman Urdu texting"
        " (e.g. 'yeh aik acha mulk hai'). Do NOT use Urdu/Arabic script"
        " (Nastaliq) at all, even though the language is Urdu."
    ),
}

NLLB_LANG_CODES = {
    "ur": "urd_Arab",
    "sd": "snd_Arab",
    "pa": "pnb_Arab",
    "ps": "pbt_Arab",
    "en": "eng_Latn",
}

# Groq has no notion of Roman Urdu, so that pair can never use local NLLB.
GROQ_ONLY_LANGS = {"ur-roman"}

_model = None
_tokenizer = None
_model_lock = threading.Lock()

_groq_client = None


def _load_nllb_model():
    """Load the local NLLB model.

    Imports torch/transformers lazily so that processes running on the Groq
    backend never pay the ~8s import cost or the 2.3 GB model residency.
    """
    global _model, _tokenizer
    if _model is not None:
        return
    with _model_lock:
        if _model is not None:
            return
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        logger.info(f"Loading NLLB model: {settings.nllb_model_name} ...")
        tokenizer = AutoTokenizer.from_pretrained(settings.nllb_model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(settings.nllb_model_name)
        model.eval()
        _tokenizer = tokenizer
        _model = model
        logger.info("NLLB model loaded successfully.")


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.groq_api_key)
    return _groq_client


def _translate_with_nllb(text: str, src_code: str, tgt_code: str) -> str:
    import torch

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


def _translate_with_groq(text: str, source_lang_name: str, target_lang_name: str, target_lang_code: str = "") -> str:
    client = _get_groq_client()

    # Keyed by language CODE. Keying by display name silently no-ops when the
    # name and code differ in spelling ("Roman Urdu" vs "ur-roman").
    script_instruction = SCRIPT_INSTRUCTIONS.get(target_lang_code, "")

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
    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise TranslationError("Translation model returned an empty response.")
    return content


def _translate_via_groq(text: str, source_lang_code: str, target_lang_code: str) -> str:
    source_name = LANG_NAMES.get(source_lang_code, source_lang_code)
    target_name = LANG_NAMES.get(target_lang_code, target_lang_code)
    return _translate_with_groq(text, source_name, target_name, target_lang_code)


def _translate_via_nllb(text: str, source_lang_code: str, target_lang_code: str) -> str:
    src_nllb = NLLB_LANG_CODES.get(source_lang_code)
    tgt_nllb = NLLB_LANG_CODES.get(target_lang_code)

    if not src_nllb or not tgt_nllb:
        raise TranslationError(
            f"Unsupported language pair for the local NLLB model: "
            f"{source_lang_code} -> {target_lang_code}"
        )

    return _translate_with_nllb(text, src_nllb, tgt_nllb)


def translate_text(text: str, source_lang_code: str, target_lang_code: str) -> str:
    if not text or not text.strip():
        raise TranslationError("Cannot translate empty text.")

    if source_lang_code == target_lang_code:
        return text

    backend = (settings.translation_backend or "groq").strip().lower()

    # Roman Urdu has no NLLB equivalent, so it is always served by Groq.
    use_groq = (
        source_lang_code in GROQ_ONLY_LANGS
        or target_lang_code in GROQ_ONLY_LANGS
        or backend == "groq"
    )

    try:
        if use_groq:
            try:
                return _translate_via_groq(text, source_lang_code, target_lang_code)
            except Exception:
                if backend != "auto":
                    raise
                logger.exception(
                    "Groq translation failed; falling back to local NLLB."
                )

        return _translate_via_nllb(text, source_lang_code, target_lang_code)

    except TranslationError:
        raise
    except Exception as e:
        logger.exception(f"Translation failed: {e}")
        raise TranslationError("Translation failed. Please try again.")