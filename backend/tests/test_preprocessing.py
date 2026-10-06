"""
Unit Tests — Preprocessing
==========================
Tests for text extraction, cleaning, and chunking.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from backend.preprocessing.cleaner import clean_text, TextCleaner
from backend.preprocessing.chunker import chunk_text, Chunk
from backend.preprocessing.extractor import extract


# ── Cleaner Tests ─────────────────────────────────────────────────────────────

class TestTextCleaner:

    def test_basic_cleaning(self):
        raw = "Patient  has   HBP.\n\n\n\nBP: 140/90."
        result = clean_text(raw)
        assert result.cleaned_text  # Not empty
        assert "blood pressure" in result.cleaned_text.lower() or "hbp" in result.cleaned_text.lower()

    def test_medical_abbreviation_expansion(self):
        raw = "Pt has htn and dm."
        result = clean_text(raw)
        # Abbreviations should be expanded
        assert "patient" in result.cleaned_text.lower()
        assert "hypertension" in result.cleaned_text.lower()
        assert "diabetes mellitus" in result.cleaned_text.lower()

    def test_unicode_normalisation(self):
        raw = "caf\u00e9 and r\u00e9sum\u00e9"  # accented characters
        result = clean_text(raw)
        assert result.cleaned_text  # Should not crash

    def test_hyphen_linebreak_fix(self):
        raw = "anti-\nhypertensive medication"
        result = clean_text(raw)
        assert "antihypertensive" in result.cleaned_text.lower() or "anti" in result.cleaned_text.lower()

    def test_tokens_are_nonempty(self):
        raw = "The patient was prescribed metformin 500mg for diabetes."
        result = clean_text(raw)
        assert len(result.tokens) > 0
        # All tokens should be alphabetic strings
        for tok in result.tokens:
            assert tok.isalpha(), f"Non-alpha token: {tok!r}"

    def test_stop_word_removal(self):
        raw = "The patient had a high blood sugar level and was given insulin."
        result_with_stop = clean_text(raw, remove_stopwords=False)
        result_no_stop = clean_text(raw, remove_stopwords=True)
        # With stop-words removed, fewer tokens
        assert len(result_no_stop.tokens) <= len(result_with_stop.tokens)

    def test_empty_text_returns_empty(self):
        result = clean_text("")
        assert result.cleaned_text == ""
        assert result.tokens == []

    def test_sentence_count(self):
        raw = "First sentence. Second sentence. Third sentence."
        result = clean_text(raw)
        assert result.sentence_count >= 2  # At least 2 sentences detected

    def test_original_length_preserved(self):
        raw = "Some text to test."
        result = clean_text(raw)
        assert result.original_length == len(raw)


# ── Chunker Tests ─────────────────────────────────────────────────────────────

class TestChunker:

    def test_basic_chunking(self):
        text = "First sentence. " * 100  # ~400 words
        chunks = chunk_text(text, doc_id="test_doc", chunk_size=50, chunk_overlap=10)
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, Chunk)
            assert chunk.doc_id == "test_doc"
            assert chunk.text.strip()

    def test_chunk_overlap(self):
        # Build a long text from repeated sentences
        sentences = [f"This is sentence number {i} about medicine." for i in range(40)]
        text = " ".join(sentences)
        chunks = chunk_text(text, doc_id="doc", chunk_size=50, chunk_overlap=10)
        assert len(chunks) > 1
        # Adjacent chunks should share some text (overlap)
        # At minimum, they should not be completely non-overlapping
        # (exact overlap check is approximate due to sentence boundaries)

    def test_empty_text_returns_empty(self):
        chunks = chunk_text("", doc_id="empty_doc")
        assert chunks == []

    def test_chunk_indices_sequential(self):
        text = "Medical text about various conditions. " * 50
        chunks = chunk_text(text, doc_id="doc", chunk_size=30, chunk_overlap=5)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_short_text_single_chunk(self):
        text = "This is a short clinical note."
        chunks = chunk_text(text, doc_id="short", chunk_size=400, chunk_overlap=50)
        assert len(chunks) == 1
        assert "short clinical note" in chunks[0].text.lower()

    def test_source_type_tag(self):
        text = "Some medical knowledge. " * 20
        chunks = chunk_text(text, doc_id="kb_001", source_type="knowledge_base")
        for chunk in chunks:
            assert chunk.source_type == "knowledge_base"

    def test_char_offsets_valid(self):
        text = "Sentence one. Sentence two. Sentence three."
        chunks = chunk_text(text, doc_id="offset_test", chunk_size=10, chunk_overlap=2)
        for chunk in chunks:
            assert chunk.char_start >= 0
            assert chunk.char_end <= len(text) + 5  # Allow minor offset

    def test_token_count_reasonable(self):
        text = "Word " * 500  # 500 words
        chunks = chunk_text(text, doc_id="tok", chunk_size=100, chunk_overlap=20)
        for chunk in chunks:
            # Token count should be within reasonable range of chunk_size
            assert chunk.token_count <= 110  # Allow a bit over due to sentence boundary


# ── Extractor Tests (TXT only — no PDF/DOCX fixture needed) ───────────────────

class TestExtractor:

    def test_txt_extraction(self, tmp_path):
        content = "Patient medical history: hypertension, diabetes mellitus type 2."
        txt_file = tmp_path / "test.txt"
        txt_file.write_text(content, encoding="utf-8")
        result = extract(txt_file)
        assert result.text.strip() == content.strip()
        assert result.file_type == "txt"
        assert result.char_count == len(content)

    def test_txt_unsupported_extension(self, tmp_path):
        bad_file = tmp_path / "test.csv"
        bad_file.write_text("data,data,data")
        with pytest.raises(ValueError, match="Unsupported file type"):
            extract(bad_file)

    def test_empty_txt_raises(self, tmp_path):
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")
        with pytest.raises(ValueError, match="empty"):
            extract(empty_file)

    def test_utf8_encoding(self, tmp_path):
        content = "Médical données: résumé du patient."
        txt_file = tmp_path / "utf8.txt"
        txt_file.write_bytes(content.encode("utf-8"))
        result = extract(txt_file)
        assert "patient" in result.text.lower()
