"""Machine Learning core modules for SherlockML.

Imports are lazy (PEP 562): ``RAGPipeline`` pulls in chromadb +
sentence-transformers and ``NERExtractor`` pulls in spaCy, both of which are
heavy and optional.  Accessing a name only imports what that name needs, so
e.g. ``from sherlockml.ml import RLController`` (numpy + sqlite only) works
without the RAG/NER stacks installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sherlockml.ml.ner_extractor import NERExtractor
    from sherlockml.ml.rag_pipeline import RAGPipeline
    from sherlockml.ml.rl_controller import RLController

__all__ = [
    "RAGPipeline",
    "RLController",
    "NERExtractor",
]

_MODULES = {
    "RAGPipeline": "sherlockml.ml.rag_pipeline",
    "RLController": "sherlockml.ml.rl_controller",
    "NERExtractor": "sherlockml.ml.ner_extractor",
}


def __getattr__(name: str) -> Any:
    module_path = _MODULES.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(module_path), name)


def __dir__() -> list[str]:
    return sorted(__all__)
