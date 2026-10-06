"""
FastAPI Application
===================
Main app factory with lifespan management:
- On startup: ensure directories, load encoder, load KB index, restore doc indexes.
- On shutdown: nothing special needed (FAISS indexes are persisted on write).

Mount the React frontend's built dist/ at /  for production serving.
In development, the Vite dev server (port 5173) proxies API calls.
"""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle manager."""
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("MedLens starting up...")
    settings.ensure_dirs()

    # 1. Load embedding model (heavy — do once at startup)
    logger.info("Loading embedding model...")
    from backend.embeddings.encoder import get_encoder
    get_encoder()

    # 2. Load pre-built KB FAISS index (if available)
    logger.info("Loading knowledge base index...")
    from backend.knowledge_base.builder import load_kb_index
    load_kb_index()

    # 3. Restore all persisted document indexes from disk
    logger.info("Restoring document indexes...")
    from backend.storage.manager import get_storage
    from backend.embeddings.indexer import FaissIndex
    from backend.retrieval.retriever import register_doc_index

    storage = get_storage()
    for doc in storage.list_documents():
        if doc.status == "ready":
            idx_dir = doc.index_dir
            if (idx_dir / "vectors.faiss").exists():
                try:
                    idx = FaissIndex.load(idx_dir)
                    register_doc_index(doc.doc_id, idx)
                    logger.info("Restored index for %s (%s)", doc.filename, doc.doc_id)
                except Exception as exc:
                    logger.warning("Could not restore index for %s: %s", doc.doc_id, exc)

    # 4. Initialise LLM provider
    logger.info("Initialising LLM provider...")
    from backend.llm import get_llm_provider
    get_llm_provider()

    logger.info("MedLens ready.")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("MedLens shutting down.")


# ── App Factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="MedLens API",
        description="Retrieval-Augmented QA for Healthcare Documents",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API Routes ────────────────────────────────────────────────────────────
    from backend.api.routes import upload, chat, documents, evaluation, status

    app.include_router(upload.router, prefix="/api", tags=["upload"])
    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(documents.router, prefix="/api", tags=["documents"])
    app.include_router(evaluation.router, prefix="/api", tags=["evaluation"])
    app.include_router(status.router, prefix="/api", tags=["status"])

    # ── Serve React frontend (production) ─────────────────────────────────────
    dist_dir = Path(__file__).parent.parent.parent / "frontend" / "dist"
    if dist_dir.exists():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")
        logger.info("Serving frontend from %s", dist_dir)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_env == "development",
    )
