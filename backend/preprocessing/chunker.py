"""
Text Chunker
============
Splits cleaned text into overlapping passages for embedding and retrieval.

Strategy: sentence-aware sliding window.
- Split text into sentences first.
- Accumulate sentences until token budget is reached.
- Slide forward by (chunk_size - chunk_overlap) tokens.
- Each chunk carries source metadata (doc_id, chunk_index, char offsets, page_hint).

This produces more coherent chunks than naive character-splitting, and
keeps the overlap semantically meaningful (whole sentences at boundaries).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import nltk
from nltk.tokenize import sent_tokenize, word_tokenize


@dataclass
class Chunk:
    """A single text passage ready for embedding."""
    doc_id: str
    chunk_index: int
    text: str
    token_count: int
    char_start: int
    char_end: int
    page_hint: Optional[int] = None     # Best-effort page number (if available)
    source_type: str = "document"        # "document" | "knowledge_base"
    metadata: dict = field(default_factory=dict)


def _count_tokens(text: str) -> int:
    """Fast word-level token count (consistent with chunk_size semantics)."""
    return len(text.split())


def _sentence_tokenise(text: str) -> list[str]:
    """Robust sentence splitting with NLTK fallback."""
    try:
        return sent_tokenize(text)
    except Exception:
        # Simple period-based fallback
        return re.split(r"(?<=[.!?])\s+", text)


def chunk_text(
    text: str,
    doc_id: str,
    chunk_size: int = 400,
    chunk_overlap: int = 50,
    page_boundaries: Optional[list[int]] = None,  # char offsets where new pages start
    source_type: str = "document",
) -> list[Chunk]:
    """
    Split ``text`` into overlapping ``Chunk`` objects.

    Args:
        text:             The full cleaned document text.
        doc_id:           Unique document identifier.
        chunk_size:       Target token count per chunk (inclusive).
        chunk_overlap:    Number of tokens to repeat at the boundary.
        page_boundaries:  Optional list of character offsets at which a new
                          page starts. Used to attach page_hint to chunks.
        source_type:      Tag for the chunk source ("document" or "knowledge_base").

    Returns:
        List of Chunk objects in document order.
    """
    if not text.strip():
        return []

    sentences = _sentence_tokenise(text)
    if not sentences:
        return []

    # Build cumulative char offset per sentence so we can map back
    char_cursor = 0
    sentence_data: list[tuple[str, int, int]] = []  # (text, char_start, char_end)
    for sent in sentences:
        # Find the sentence in the original text starting from char_cursor
        idx = text.find(sent, char_cursor)
        if idx == -1:
            idx = char_cursor
        start = idx
        end = idx + len(sent)
        if _count_tokens(sent) <= chunk_size:
            sentence_data.append((sent, start, end))
        else:
            # NLTK may treat an entire punctuation-free document as one
            # sentence. Split oversized sentences so chunk_size remains a
            # real upper bound instead of embedding the whole document.
            words = list(re.finditer(r"\S+", sent))
            for offset in range(0, len(words), chunk_size):
                group = words[offset:offset + chunk_size]
                segment_start = start + group[0].start()
                segment_end = start + group[-1].end()
                sentence_data.append((text[segment_start:segment_end], segment_start, segment_end))
        char_cursor = end

    # Sliding window accumulation
    chunks: list[Chunk] = []
    window_start = 0          # index into sentence_data
    chunk_index = 0
    step_tokens = max(1, chunk_size - chunk_overlap)

    while window_start < len(sentence_data):
        # Accumulate sentences until token budget
        accumulated: list[str] = []
        token_total = 0
        i = window_start

        while i < len(sentence_data):
            sent_text, _, _ = sentence_data[i]
            sent_tokens = _count_tokens(sent_text)
            if token_total + sent_tokens > chunk_size and accumulated:
                break
            accumulated.append(sent_text)
            token_total += sent_tokens
            i += 1

        if not accumulated:
            # Single sentence exceeds chunk_size — include it anyway
            accumulated = [sentence_data[window_start][0]]
            token_total = _count_tokens(accumulated[0])
            i = window_start + 1

        chunk_text_str = " ".join(accumulated)
        char_start = sentence_data[window_start][1]
        char_end = sentence_data[i - 1][2]

        # Best-effort page number
        page_hint: Optional[int] = None
        if page_boundaries:
            for page_num, boundary in enumerate(page_boundaries, start=1):
                if char_start >= boundary:
                    page_hint = page_num

        chunks.append(Chunk(
            doc_id=doc_id,
            chunk_index=chunk_index,
            text=chunk_text_str,
            token_count=token_total,
            char_start=char_start,
            char_end=char_end,
            page_hint=page_hint,
            source_type=source_type,
        ))
        chunk_index += 1

        # Advance window by step_tokens worth of sentences
        tokens_stepped = 0
        while window_start < i and tokens_stepped < step_tokens:
            tokens_stepped += _count_tokens(sentence_data[window_start][0])
            window_start += 1

        # Prevent infinite loop if no progress was made
        if window_start >= i:
            window_start = i

    return chunks
