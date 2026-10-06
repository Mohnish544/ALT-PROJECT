"""
Unit Tests — Retrieval
======================
Tests for the FAISS indexer, retrieval logic, and TF-IDF baseline.
"""
from __future__ import annotations

import numpy as np
import pytest

from backend.embeddings.indexer import FaissIndex, SearchResult
from backend.preprocessing.chunker import Chunk
from backend.retrieval.baseline import TFIDFRetriever
from backend.evaluation.metrics import (
    precision_at_k, recall_at_k, f1_at_k, hit_at_k,
    reciprocal_rank, evaluate_retrieval,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

def make_chunk(doc_id: str, idx: int, text: str) -> Chunk:
    return Chunk(
        doc_id=doc_id, chunk_index=idx, text=text,
        token_count=len(text.split()), char_start=0, char_end=len(text),
    )


def make_random_vectors(n: int, dim: int = 128) -> np.ndarray:
    """Random L2-normalised vectors."""
    vecs = np.random.randn(n, dim).astype(np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / norms


# ── FAISS Index Tests ─────────────────────────────────────────────────────────

class TestFaissIndex:

    def test_add_and_search(self):
        dim = 64
        index = FaissIndex(dim=dim)
        chunks = [make_chunk("doc1", i, f"medical text {i}") for i in range(10)]
        vecs = make_random_vectors(10, dim)
        index.add(vecs, chunks)

        assert index.total_vectors == 10

        query = make_random_vectors(1, dim)
        results = index.search(query, top_k=3)
        assert len(results) == 3
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(0.0 <= r.score <= 1.1 for r in results)

    def test_results_sorted_descending(self):
        dim = 32
        index = FaissIndex(dim=dim)
        chunks = [make_chunk("doc", i, f"text {i}") for i in range(20)]
        vecs = make_random_vectors(20, dim)
        index.add(vecs, chunks)

        query = make_random_vectors(1, dim)
        results = index.search(query, top_k=10)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_empty_index_returns_empty(self):
        index = FaissIndex(dim=64)
        results = index.search(make_random_vectors(1, 64), top_k=5)
        assert results == []

    def test_save_and_load(self, tmp_path):
        dim = 32
        index = FaissIndex(dim=dim, index_dir=tmp_path)
        chunks = [make_chunk("doc", i, f"test chunk {i}") for i in range(5)]
        vecs = make_random_vectors(5, dim)
        index.add(vecs, chunks)
        index.save()

        loaded = FaissIndex.load(tmp_path)
        assert loaded.total_vectors == 5
        assert len(loaded.chunks) == 5
        assert loaded.chunks[0].doc_id == "doc"

    def test_top_k_capped_at_ntotal(self):
        dim = 16
        index = FaissIndex(dim=dim)
        chunks = [make_chunk("doc", i, f"t{i}") for i in range(3)]
        index.add(make_random_vectors(3, dim), chunks)
        results = index.search(make_random_vectors(1, dim), top_k=100)
        assert len(results) <= 3

    def test_min_score_filter(self):
        dim = 32
        index = FaissIndex(dim=dim)
        chunks = [make_chunk("doc", i, f"txt {i}") for i in range(10)]
        vecs = make_random_vectors(10, dim)
        index.add(vecs, chunks)
        results = index.search(make_random_vectors(1, dim), top_k=10, min_score=1.0)
        # Almost no result will have cosine sim ≥ 1.0 (only identical vectors would)
        assert len(results) <= 1

    def test_remove_by_doc_id(self):
        dim = 32
        index = FaissIndex(dim=dim)
        chunks_a = [make_chunk("docA", i, f"A {i}") for i in range(3)]
        chunks_b = [make_chunk("docB", i, f"B {i}") for i in range(3)]
        vecs = make_random_vectors(6, dim)
        index.add(vecs[:3], chunks_a)
        index.add(vecs[3:], chunks_b)
        removed = index.remove_by_doc_id("docA")
        assert removed == 3
        remaining = [c for c in index.chunks if c.doc_id == "docA"]
        assert remaining == []


# ── TF-IDF Baseline Tests ─────────────────────────────────────────────────────

class TestTFIDFRetriever:

    def test_fit_and_search(self):
        chunks = [
            make_chunk("doc", 0, "patient has hypertension and elevated blood pressure"),
            make_chunk("doc", 1, "diabetes mellitus type 2 with insulin resistance"),
            make_chunk("doc", 2, "coronary artery disease risk factor assessment"),
            make_chunk("doc", 3, "antibiotic treatment for urinary tract infection"),
        ]
        retriever = TFIDFRetriever()
        retriever.fit(chunks)
        results = retriever.search("what medications for blood pressure hypertension", top_k=2)
        assert len(results) > 0
        # The hypertension chunk should rank first
        top_chunk, top_score = results[0]
        assert "hypertension" in top_chunk.text or "blood pressure" in top_chunk.text

    def test_empty_corpus(self):
        retriever = TFIDFRetriever()
        retriever.fit([])
        results = retriever.search("test query")
        assert results == []

    def test_scores_are_positive(self):
        chunks = [make_chunk("d", i, f"medical condition {i} treatment") for i in range(5)]
        retriever = TFIDFRetriever()
        retriever.fit(chunks)
        results = retriever.search("medical treatment", top_k=3)
        for _, score in results:
            assert score >= 0.0


# ── Metric Tests ─────────────────────────────────────────────────────────────

class TestMetrics:

    def test_precision_at_k_perfect(self):
        retrieved = ["a", "b", "c"]
        relevant = {"a", "b", "c"}
        assert precision_at_k(retrieved, relevant, 3) == 1.0

    def test_precision_at_k_zero(self):
        retrieved = ["x", "y", "z"]
        relevant = {"a", "b"}
        assert precision_at_k(retrieved, relevant, 3) == 0.0

    def test_recall_at_k(self):
        retrieved = ["a", "b", "c", "d"]
        relevant = {"a", "b", "e"}  # only 2 of 3 found
        assert abs(recall_at_k(retrieved, relevant, 4) - 2 / 3) < 1e-9

    def test_f1_at_k(self):
        retrieved = ["a", "b", "c"]
        relevant = {"a", "b"}
        p = precision_at_k(retrieved, relevant, 3)
        r = recall_at_k(retrieved, relevant, 3)
        f1 = f1_at_k(retrieved, relevant, 3)
        expected = 2 * p * r / (p + r)
        assert abs(f1 - expected) < 1e-9

    def test_hit_at_k_hit(self):
        assert hit_at_k(["x", "a"], {"a", "b"}, 2) == 1.0

    def test_hit_at_k_miss(self):
        assert hit_at_k(["x", "y"], {"a", "b"}, 2) == 0.0

    def test_reciprocal_rank(self):
        retrieved = ["x", "y", "a", "b"]
        relevant = {"a"}
        assert abs(reciprocal_rank(retrieved, relevant) - 1 / 3) < 1e-9

    def test_evaluate_retrieval_aggregation(self):
        queries = [
            (["a", "b", "c"], {"a"}),
            (["x", "y", "z"], {"a"}),
        ]
        ms = evaluate_retrieval(queries, k=3)
        assert ms.num_queries == 2
        assert 0.0 <= ms.precision <= 1.0
        assert 0.0 <= ms.recall <= 1.0
        assert 0.0 <= ms.hit_rate <= 1.0
        assert 0.0 <= ms.mrr <= 1.0
