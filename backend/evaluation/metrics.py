"""
Retrieval Metrics
=================
Standard IR metrics for evaluating retrieval quality.

Metrics implemented:
- Precision@K: fraction of retrieved docs that are relevant
- Recall@K:    fraction of relevant docs that were retrieved
- F1@K:        harmonic mean of Precision and Recall
- Hit@K:       binary — did any retrieved result match? (averaged = Hit Rate)
- MRR:         Mean Reciprocal Rank — position of first relevant result

Each function operates on a list of (retrieved_ids, relevant_ids) pairs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass
class MetricSet:
    precision: float
    recall: float
    f1: float
    hit_rate: float
    mrr: float
    num_queries: int


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Fraction of top-k retrieved items that are relevant."""
    if k == 0:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for r in top_k if r in relevant)
    return hits / k


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Fraction of relevant items found in top-k retrieved."""
    if not relevant:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for r in top_k if r in relevant)
    return hits / len(relevant)


def f1_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Harmonic mean of Precision@K and Recall@K."""
    p = precision_at_k(retrieved, relevant, k)
    r = recall_at_k(retrieved, relevant, k)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


def hit_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """1.0 if any top-k result is relevant, else 0.0."""
    return float(any(r in relevant for r in retrieved[:k]))


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    """1 / rank of the first relevant result (0 if none found)."""
    for rank, r in enumerate(retrieved, start=1):
        if r in relevant:
            return 1.0 / rank
    return 0.0


def evaluate_retrieval(
    queries: list[tuple[list[str], set[str]]],
    k: int = 5,
) -> MetricSet:
    """
    Compute averaged metrics over a list of (retrieved_ids, relevant_ids) pairs.

    Args:
        queries: List of (retrieved_chunk_ids, relevant_chunk_ids).
        k:       Cutoff for @K metrics.

    Returns:
        MetricSet with macro-averaged scores.
    """
    if not queries:
        return MetricSet(0, 0, 0, 0, 0, 0)

    p_scores, r_scores, f1_scores, hit_scores, rr_scores = [], [], [], [], []

    for retrieved, relevant in queries:
        p_scores.append(precision_at_k(retrieved, relevant, k))
        r_scores.append(recall_at_k(retrieved, relevant, k))
        f1_scores.append(f1_at_k(retrieved, relevant, k))
        hit_scores.append(hit_at_k(retrieved, relevant, k))
        rr_scores.append(reciprocal_rank(retrieved, relevant))

    n = len(queries)
    return MetricSet(
        precision=sum(p_scores) / n,
        recall=sum(r_scores) / n,
        f1=sum(f1_scores) / n,
        hit_rate=sum(hit_scores) / n,
        mrr=sum(rr_scores) / n,
        num_queries=n,
    )
