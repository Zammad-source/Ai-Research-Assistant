import re
import logging
from langdetect import detect, DetectorFactory, LangDetectException

from app.core.exceptions import LanguageDetectionError

# Make langdetect deterministic (it's non-deterministic by default)
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)

# Unicode ranges for script-based detection
ARABIC_SCRIPT_RANGE = re.compile(r'[\u0600-\u06FF\u0750-\u077F]')
GURMUKHI_SCRIPT_RANGE = re.compile(r'[\u0A00-\u0A7F]')  # Punjabi (Gurmukhi)

# Common Roman Urdu words/patterns to help distinguish from plain English
ROMAN_URDU_MARKERS = {
    "hai", "hain", "ho", "kya", "kyun", "kaise", "mein", "main", "ka", "ki",
    "ke", "se", "ko", "aur", "nahi", "nahin", "tha", "thi", "the", "aap",
    "tum", "hum", "mujhe", "tumhe", "usko", "kar", "karo", "karna", "raha",
    "rahi", "rahe", "wala", "wali", "bhi", "abhi", "yai", "yeh", "woh",
}

SUPPORTED_LANGUAGES = {
    "ur": "Urdu",
    "sd": "Sindhi",
    "pa": "Punjabi",
    "ps": "Pashto",
    "ur-roman": "Roman Urdu",
    "en": "English",
    "unknown": "Unknown",
}


def _is_roman_urdu(text: str) -> bool:
    """Heuristic check: does this Latin-script text look like Roman Urdu?"""
    words = re.findall(r'[a-zA-Z]+', text.lower())
    if not words:
        return False
    marker_hits = sum(1 for w in words if w in ROMAN_URDU_MARKERS)
    # If a meaningful fraction of words are known Roman Urdu markers, call it Roman Urdu
    return (marker_hits / len(words)) >= 0.15


def _detect_by_script(text: str) -> str | None:
    """First pass: check Unicode character ranges for non-Latin scripts."""
    arabic_count = len(ARABIC_SCRIPT_RANGE.findall(text))
    gurmukhi_count = len(GURMUKHI_SCRIPT_RANGE.findall(text))

    total_chars = max(len(text.replace(" ", "")), 1)

    if gurmukhi_count / total_chars > 0.3:
        return "pa"  # Punjabi in Gurmukhi script

    if arabic_count / total_chars > 0.3:
        # Arabic script is shared by Urdu, Sindhi, Pashto, Saraiki.
        # We can't fully distinguish these by script alone — langdetect
        # helps narrow it further below, with Urdu as the safe default
        # for this project's audience.
        return "arabic_script"

    return None


def detect_language(text: str) -> dict:
    """
    Detects the language of the input text.

    Returns:
        dict with keys: 'language_code', 'language_name', 'confidence_method'

    Raises:
        LanguageDetectionError if text is empty or detection fails entirely.
    """
    if not text or not text.strip():
        raise LanguageDetectionError("Cannot detect language of empty text.")

    cleaned = text.strip()

    # Step 1: Script-based detection (most reliable for Arabic-script languages)
    script_result = _detect_by_script(cleaned)

    if script_result == "pa":
        return {
            "language_code": "pa",
            "language_name": "Punjabi",
            "confidence_method": "script",
        }

    if script_result == "arabic_script":
        # Narrow down within Arabic-script languages using langdetect
        try:
            lang_code = detect(cleaned)
            if lang_code in ("ur", "ps", "sd"):
                return {
                    "language_code": lang_code,
                    "language_name": SUPPORTED_LANGUAGES.get(lang_code, lang_code),
                    "confidence_method": "script+langdetect",
                }
        except LangDetectException:
            pass
        # Default fallback within Arabic script: Urdu (most common for this audience)
        return {
            "language_code": "ur",
            "language_name": "Urdu",
            "confidence_method": "script_fallback",
        }

    # Step 2: Latin script — check Roman Urdu first
    if _is_roman_urdu(cleaned):
        return {
            "language_code": "ur-roman",
            "language_name": "Roman Urdu",
            "confidence_method": "heuristic_markers",
        }

    # Step 3: Fallback to langdetect for plain English or anything else
    try:
        lang_code = detect(cleaned)
        if lang_code == "en":
            return {
                "language_code": "en",
                "language_name": "English",
                "confidence_method": "langdetect",
            }
        # Unrecognized/unsupported language — still return it, let caller decide
        return {
            "language_code": lang_code,
            "language_name": SUPPORTED_LANGUAGES.get(lang_code, lang_code),
            "confidence_method": "langdetect",
        }
    except LangDetectException as e:
        logger.error(f"langdetect failed for text: {cleaned[:50]}... | {e}")
        raise LanguageDetectionError(
            "Could not detect language. Please try rephrasing your input."
        )