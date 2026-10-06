"""
Text Cleaner
============
Cleans and normalises raw extracted text for downstream NLP.
Pipeline: normalise unicode → expand abbreviations → remove noise →
          tokenise → lemmatise → remove stop-words (optional).

We keep both a "full" cleaned string (for chunking) and an
"NLP-ready" token list (for TF-IDF baseline retrieval).
"""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

import nltk
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize, sent_tokenize
import nltk.tag

logger = logging.getLogger(__name__)

# ── NLTK resource bootstrapping ───────────────────────────────────────────────
_NLTK_RESOURCES = [
    ("tokenizers/punkt", "punkt"),
    ("tokenizers/punkt_tab", "punkt_tab"),
    ("corpora/stopwords", "stopwords"),
    ("corpora/wordnet", "wordnet"),
    ("taggers/averaged_perceptron_tagger", "averaged_perceptron_tagger"),
    ("taggers/averaged_perceptron_tagger_eng", "averaged_perceptron_tagger_eng"),
]

def _ensure_nltk_resources() -> None:
    for resource_path, resource_name in _NLTK_RESOURCES:
        try:
            nltk.data.find(resource_path)
        except LookupError:
            logger.info("Downloading NLTK resource: %s", resource_name)
            nltk.download(resource_name, quiet=True)

_ensure_nltk_resources()

# ── Medical abbreviation normalization map ────────────────────────────────────
MEDICAL_ABBREVIATIONS: dict[str, str] = {
    r"\bpt\b": "patient",
    r"\bpts\b": "patients",
    r"\bhx\b": "history",
    r"\bdx\b": "diagnosis",
    r"\brx\b": "prescription",
    r"\btx\b": "treatment",
    r"\bsx\b": "symptoms",
    r"\bhtn\b": "hypertension",
    r"\bdm\b": "diabetes mellitus",
    r"\bcad\b": "coronary artery disease",
    r"\bmi\b": "myocardial infarction",
    r"\bchf\b": "congestive heart failure",
    r"\bcopd\b": "chronic obstructive pulmonary disease",
    r"\buti\b": "urinary tract infection",
    r"\burti\b": "upper respiratory tract infection",
    r"\bcva\b": "cerebrovascular accident",
    r"\btia\b": "transient ischemic attack",
    r"\bimo\b": "in my opinion",
    r"\bpo\b": "by mouth",
    r"\biv\b": "intravenous",
    r"\bim\b": "intramuscular",
    r"\bq\.?d\b": "daily",
    r"\bb\.?i\.?d\b": "twice daily",
    r"\bt\.?i\.?d\b": "three times daily",
    r"\bq\.?i\.?d\b": "four times daily",
    r"\bprn\b": "as needed",
    r"\bstat\b": "immediately",
    r"\bnpo\b": "nothing by mouth",
    r"\bwbc\b": "white blood cell",
    r"\brbc\b": "red blood cell",
    r"\bhgb\b": "hemoglobin",
    r"\bbp\b": "blood pressure",
    r"\bhr\b": "heart rate",
    r"\brr\b": "respiratory rate",
    r"\btemp\b": "temperature",
    r"\bspo2\b": "oxygen saturation",
    r"\bvs\b": "vital signs",
    r"\bwt\b": "weight",
    r"\bht\b": "height",
    r"\bbmi\b": "body mass index",
    r"\bfbs\b": "fasting blood sugar",
    r"\bhba1c\b": "glycated hemoglobin",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_wordnet_pos(treebank_tag: str) -> str:
    """Map Penn Treebank POS tag to WordNet POS for lemmatisation."""
    if treebank_tag.startswith("J"):
        return wordnet.ADJ
    elif treebank_tag.startswith("V"):
        return wordnet.VERB
    elif treebank_tag.startswith("N"):
        return wordnet.NOUN
    elif treebank_tag.startswith("R"):
        return wordnet.ADV
    return wordnet.NOUN


@dataclass
class CleanedText:
    original_length: int
    cleaned_text: str          # Full cleaned string for chunking
    tokens: list[str]          # Lemmatised, stop-word-removed tokens
    sentence_count: int


class TextCleaner:
    """
    Stateful cleaner so the lemmatiser and stop-word set are loaded once.
    """

    def __init__(self, language: str = "english") -> None:
        self._lemmatiser = WordNetLemmatizer()
        self._stop_words: set[str] = set(stopwords.words(language))
        # Keep medically relevant common words that NLTK would stop-remove
        _medical_keep = {
            "no", "not", "without", "with", "above", "below", "normal",
            "abnormal", "positive", "negative", "high", "low", "severe",
            "moderate", "mild", "acute", "chronic", "left", "right",
        }
        self._stop_words -= _medical_keep

    def clean(self, raw_text: str, remove_stopwords: bool = False) -> CleanedText:
        """
        Full cleaning pipeline.

        Args:
            raw_text: Raw text from extractor.
            remove_stopwords: Whether to strip stop-words from token list.
                              The cleaned_text field always keeps them.

        Returns:
            CleanedText with both a cleaned string and a token list.
        """
        original_length = len(raw_text)

        # 1. Unicode normalisation (NFKC collapses ligatures, etc.)
        text = unicodedata.normalize("NFKC", raw_text)

        # 2. Remove null bytes and control characters (keep \n, \t)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text)

        # 3. Fix hyphenated line-breaks (common in PDFs)
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

        # 4. Collapse excessive whitespace while preserving paragraph breaks
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # 5. Expand medical abbreviations (case-insensitive)
        for pattern, expansion in MEDICAL_ABBREVIATIONS.items():
            text = re.sub(pattern, expansion, text, flags=re.IGNORECASE)

        # 6. Remove special characters that carry no semantic meaning,
        #    but keep decimal numbers, hyphens in compound words, and
        #    forward-slash in dosage notation (e.g., "10 mg/day").
        text = re.sub(r"[^\w\s\-./,%()°\n]", " ", text)

        # 7. Final whitespace cleanup
        cleaned_text = text.strip()

        # 8. Tokenise
        try:
            tokens_raw = word_tokenize(cleaned_text.lower())
        except Exception:
            tokens_raw = cleaned_text.lower().split()

        # 9. POS-aware lemmatisation
        try:
            tagged = nltk.pos_tag(tokens_raw)
            tokens = [
                self._lemmatiser.lemmatize(tok, _get_wordnet_pos(pos))
                for tok, pos in tagged
                if tok.isalpha() and len(tok) > 1
            ]
        except Exception:
            tokens = [
                self._lemmatiser.lemmatize(tok)
                for tok in tokens_raw
                if tok.isalpha() and len(tok) > 1
            ]

        # 10. Optional stop-word removal (for TF-IDF baseline)
        if remove_stopwords:
            tokens = [t for t in tokens if t not in self._stop_words]

        # 11. Sentence count
        try:
            sentences = sent_tokenize(cleaned_text)
            sentence_count = len(sentences)
        except Exception:
            sentence_count = cleaned_text.count(".") + 1

        return CleanedText(
            original_length=original_length,
            cleaned_text=cleaned_text,
            tokens=tokens,
            sentence_count=sentence_count,
        )


# Module-level singleton for convenience
_default_cleaner: Optional[TextCleaner] = None


def get_cleaner() -> TextCleaner:
    global _default_cleaner
    if _default_cleaner is None:
        _default_cleaner = TextCleaner()
    return _default_cleaner


def clean_text(raw_text: str, remove_stopwords: bool = False) -> CleanedText:
    """Convenience wrapper using the module-level cleaner singleton."""
    return get_cleaner().clean(raw_text, remove_stopwords=remove_stopwords)
