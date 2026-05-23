from langdetect import detect_langs, LangDetectException
import logging

SUPPORTED = {"hi", "ta", "bn", "mr", "te", "en"}

def detect_language(text: str) -> tuple[str, float]:
    if not text or len(text.strip()) < 3:
        return "en", 0.0
    try:
        langs = detect_langs(text)
        best = langs[0]
        lang = best.lang if best.lang in SUPPORTED else "en"
        confidence = round(best.prob, 3)
        logging.info(f"lang_detect lang={lang} confidence={confidence}")
        return lang, confidence
    except LangDetectException as e:
        logging.warning(f"lang_detect_failed error={e}")
        return "en", 0.0
