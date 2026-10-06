"""Retrieval package."""
from .retriever import (
    retrieve, RetrievalResult,
    register_doc_index, load_doc_index, unload_doc_index,
    get_doc_index, list_loaded_doc_ids,
)
from .baseline import TFIDFRetriever, get_baseline

__all__ = [
    "retrieve", "RetrievalResult",
    "register_doc_index", "load_doc_index", "unload_doc_index",
    "get_doc_index", "list_loaded_doc_ids",
    "TFIDFRetriever", "get_baseline",
]
