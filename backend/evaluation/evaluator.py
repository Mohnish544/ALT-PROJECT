"""
Evaluator
=========
Runs evaluation on the held-out QA pairs, comparing:
1. Semantic retrieval (sentence-transformer embeddings + FAISS)
2. TF-IDF baseline (bag-of-words, BM25-style)

Evaluation data: backend/evaluation/eval_data/qa_pairs.json
Each entry: {"question": "...", "relevant_chunk_ids": [...], "answer": "..."}

Because eval_data references chunk IDs from sample docs, we need to:
1. Load sample documents and build in-memory indexes.
2. Retrieve for each question.
3. Compute metrics.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.api.models import EvaluationResponse, MetricResult
from backend.evaluation.metrics import evaluate_retrieval, MetricSet

logger = logging.getLogger(__name__)

EVAL_DATA_PATH = Path(__file__).parent / "eval_data" / "qa_pairs.json"
SAMPLE_DOCS_DIR = Path("data/sample_docs")


def _load_qa_pairs() -> list[dict]:
    if not EVAL_DATA_PATH.exists():
        logger.error("Eval data not found at %s", EVAL_DATA_PATH)
        return []
    with open(EVAL_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_eval_index(doc_texts: dict[str, str]) -> tuple:
    """
    Build in-memory FAISS and TF-IDF indexes from document texts.
    Returns (faiss_index, tfidf_retriever, all_chunks).
    """
    from backend.preprocessing.cleaner import clean_text
    from backend.preprocessing.chunker import chunk_text, Chunk
    from backend.embeddings.encoder import get_encoder
    from backend.embeddings.indexer import FaissIndex
    from backend.retrieval.baseline import TFIDFRetriever

    all_chunks: list[Chunk] = []
    for doc_id, text in doc_texts.items():
        cleaned = clean_text(text)
        chunks = chunk_text(
            text=cleaned.cleaned_text,
            doc_id=doc_id,
            source_type="document",
        )
        for chunk in chunks:
            chunk.metadata["display_source"] = doc_id
        all_chunks.extend(chunks)

    if not all_chunks:
        return None, None, []

    # Semantic index
    encoder = get_encoder()
    texts = [c.text for c in all_chunks]
    vectors = encoder.encode(texts)
    faiss_index = FaissIndex(dim=encoder.dim)
    faiss_index.add(vectors, all_chunks)

    # TF-IDF baseline
    tfidf = TFIDFRetriever()
    tfidf.fit(all_chunks)

    return faiss_index, tfidf, all_chunks


def run_evaluation(top_k: int = 5) -> EvaluationResponse:
    """
    Run the full evaluation pipeline and return metrics.
    """
    qa_pairs = _load_qa_pairs()
    if not qa_pairs:
        return EvaluationResponse(
            metrics=[],
            total_questions=0,
            evaluation_timestamp=datetime.now(timezone.utc).isoformat(),
            notes="No evaluation data found. Ensure eval_data/qa_pairs.json exists.",
        )

    # Load sample documents for evaluation
    doc_texts: dict[str, str] = {}
    for txt_file in SAMPLE_DOCS_DIR.glob("*.txt"):
        try:
            doc_texts[txt_file.stem] = txt_file.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("Could not read %s: %s", txt_file, exc)

    if not doc_texts:
        return EvaluationResponse(
            metrics=[],
            total_questions=0,
            evaluation_timestamp=datetime.now(timezone.utc).isoformat(),
            notes="No sample documents found in data/sample_docs/. Cannot evaluate.",
        )

    logger.info("Building eval indexes from %d document(s)...", len(doc_texts))
    faiss_index, tfidf, all_chunks = _build_eval_index(doc_texts)

    if faiss_index is None:
        return EvaluationResponse(
            metrics=[],
            total_questions=0,
            evaluation_timestamp=datetime.now(timezone.utc).isoformat(),
            notes="Could not build evaluation indexes.",
        )

    from backend.embeddings.encoder import get_encoder
    encoder = get_encoder()

    # Collect retrieval results for both methods
    semantic_pairs: list[tuple[list[str], set[str]]] = []
    baseline_pairs: list[tuple[list[str], set[str]]] = []

    for entry in qa_pairs:
        question = entry.get("question", "")
        # relevant_chunk_ids may reference doc_id:chunk_index pairs or keywords
        relevant_keywords: set[str] = set(entry.get("relevant_keywords", []))

        if not question:
            continue

        # Semantic retrieval
        query_vec = encoder.encode_query(question)
        sem_results = faiss_index.search(query_vec, top_k=top_k)
        sem_ids = [r.chunk.text[:50].lower() for r in sem_results]

        # TF-IDF retrieval
        tfidf_results = tfidf.search(question, top_k=top_k)
        tfidf_ids = [c.text[:50].lower() for c, _ in tfidf_results]

        # Map relevant keywords to any chunk containing the keywords
        def _relevant_ids(result_ids: list[str]) -> set[str]:
            """Which retrieved chunks contain at least one relevant keyword."""
            relevant = set()
            all_chunk_texts = [c.text.lower() for c in all_chunks]
            for kw in relevant_keywords:
                kw_lower = kw.lower()
                for chunk in all_chunks:
                    if kw_lower in chunk.text.lower():
                        relevant.add(chunk.text[:50].lower())
            return relevant

        relevant_set = _relevant_ids(sem_ids)

        semantic_pairs.append((sem_ids, relevant_set))
        baseline_pairs.append((tfidf_ids, relevant_set))

    # Compute metrics
    sem_metrics = evaluate_retrieval(semantic_pairs, k=top_k)
    base_metrics = evaluate_retrieval(baseline_pairs, k=top_k)

    def _improvement(sem: float, base: float) -> float:
        if base == 0:
            return 0.0
        return round((sem - base) / base * 100, 1)

    metric_results = [
        MetricResult(
            metric=f"Precision@{top_k}",
            semantic_value=round(sem_metrics.precision, 4),
            baseline_value=round(base_metrics.precision, 4),
            improvement_pct=_improvement(sem_metrics.precision, base_metrics.precision),
        ),
        MetricResult(
            metric=f"Recall@{top_k}",
            semantic_value=round(sem_metrics.recall, 4),
            baseline_value=round(base_metrics.recall, 4),
            improvement_pct=_improvement(sem_metrics.recall, base_metrics.recall),
        ),
        MetricResult(
            metric=f"F1@{top_k}",
            semantic_value=round(sem_metrics.f1, 4),
            baseline_value=round(base_metrics.f1, 4),
            improvement_pct=_improvement(sem_metrics.f1, base_metrics.f1),
        ),
        MetricResult(
            metric=f"Hit Rate@{top_k}",
            semantic_value=round(sem_metrics.hit_rate, 4),
            baseline_value=round(base_metrics.hit_rate, 4),
            improvement_pct=_improvement(sem_metrics.hit_rate, base_metrics.hit_rate),
        ),
        MetricResult(
            metric="MRR",
            semantic_value=round(sem_metrics.mrr, 4),
            baseline_value=round(base_metrics.mrr, 4),
            improvement_pct=_improvement(sem_metrics.mrr, base_metrics.mrr),
        ),
    ]

    return EvaluationResponse(
        metrics=metric_results,
        total_questions=sem_metrics.num_queries,
        evaluation_timestamp=datetime.now(timezone.utc).isoformat(),
        notes=(
            f"Evaluated on {sem_metrics.num_queries} questions from {len(doc_texts)} sample document(s). "
            f"Semantic retrieval uses {encoder.model_name}; baseline uses TF-IDF with bigrams."
        ),
    )
