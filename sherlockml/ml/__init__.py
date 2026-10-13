"""Machine Learning core modules for SherlockML.

Imports are lazy: the RAG pipeline pulls in chromadb and
sentence-transformers and the NER extractor pulls in spaCy, so importing
one component (e.g. the SQLite-backed RLController) must not require the
heavy dependencies of the others.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sherlockml.ml.ner_extractor import NERExtractor
    from sherlockml.ml.rag_pipeline import RAGPipeline
    from sherlockml.ml.rl_controller import RLController

_LAZY = {
    "RAGPipeline": "sherlockml.ml.rag_pipeline",
    "RLController": "sherlockml.ml.rl_controller",
    "NERExtractor": "sherlockml.ml.ner_extractor",
}

__all__ = [
    "RAGPipeline",
    "RLController",
    "NERExtractor",
]


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        return getattr(importlib.import_module(_LAZY[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
