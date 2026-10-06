"""
Evaluation Route
================
GET /api/evaluate — run evaluation on held-out QA pairs and return metrics.
Compares TF-IDF baseline vs. semantic embedding retrieval.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from backend.api.models import EvaluationResponse, MetricResult

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/evaluate", response_model=EvaluationResponse)
def run_evaluation() -> EvaluationResponse:
    """
    Run the evaluation pipeline on the held-out QA pairs.
    Compares semantic retrieval vs. TF-IDF baseline.
    """
    try:
        from backend.evaluation.evaluator import run_evaluation as _eval
        results = _eval()
        return results
    except Exception as exc:
        logger.error("Evaluation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Evaluation error: {exc}")
