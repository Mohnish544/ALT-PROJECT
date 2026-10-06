#!/usr/bin/env python3
"""
Build General Medical Knowledge Base FAISS Index
==================================================
Encodes MedQuAD chunks and builds the persistent FAISS index at
data/kb_index/.

Run this ONCE after downloading MedQuAD:
    python scripts/build_kb_index.py

Or for a quick demo (2000 entries):
    python scripts/build_kb_index.py --max-entries 2000

This script:
1. Loads MedQuAD JSONL (run download_medquad.py first).
2. Chunks Q&A pairs using the configured chunk_size.
3. Encodes with the configured embedding model.
4. Saves FAISS index + metadata to data/kb_index/.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(description="Build MedQuAD KB FAISS index")
    parser.add_argument(
        "--max-entries", type=int, default=None,
        help="Limit MedQuAD entries for faster build (default: all)"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Rebuild even if index already exists"
    )
    args = parser.parse_args()

    from backend.config import settings

    kb_dir = settings.kb_index_path.parent
    faiss_path = kb_dir / "vectors.faiss"

    if faiss_path.exists() and not args.force:
        logger.info(
            "KB index already exists at %s. Use --force to rebuild.", kb_dir
        )
        return

    medquad_path = Path("data/medquad/medquad.jsonl")
    if not medquad_path.exists():
        logger.error(
            "MedQuAD JSONL not found at %s.\n"
            "Run: python scripts/download_medquad.py", medquad_path
        )
        sys.exit(1)

    logger.info("Starting KB index build (max_entries=%s)...", args.max_entries or "all")

    from backend.knowledge_base.builder import build_kb_index
    index = build_kb_index(max_entries=args.max_entries)

    logger.info(
        "KB index complete: %d vectors saved to %s",
        index.total_vectors, kb_dir
    )
    logger.info("You can now start the API: python -m backend.api.main")


if __name__ == "__main__":
    main()
