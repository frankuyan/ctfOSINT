"""RAG Pipeline for semantic search over discovered content."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


@dataclass
class RAGDocument:
    """A document indexed in the RAG system."""
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    doc_id: str | None = None
    
    def __post_init__(self) -> None:
        if self.doc_id is None:
            # Generate ID from content hash
            self.doc_id = hashlib.sha256(self.content.encode()).hexdigest()[:16]


@dataclass
class RAGResult:
    """Result from a RAG query."""
    content: str
    metadata: dict[str, Any]
    score: float
    doc_id: str


class RAGPipeline:
    """RAG pipeline for discovered content analysis.
    
    Uses ChromaDB for vector storage and sentence-transformers
    for text embeddings. Supports incremental indexing and
    semantic search with confidence thresholds.
    
    Example:
        >>> rag = RAGPipeline(persist_dir=Path("~/.sherlockml/vectorstore"))
        >>> rag.index("User bio: CTF enthusiast, pwn specialist", 
        ...           metadata={"platform": "github", "username": "target"})
        >>> results = rag.query("Find CTF related profiles", top_k=5)
    """
    
    DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    COLLECTION_NAME = "osint_data"
    
    def __init__(
        self,
        persist_dir: Path | str,
        model_name: str = DEFAULT_MODEL,
        collection_name: str = COLLECTION_NAME,
    ):
        """Initialize the RAG pipeline.
        
        Args:
            persist_dir: Directory for persistent storage
            model_name: Sentence transformer model name
            collection_name: Name of the ChromaDB collection
        """
        self.persist_dir = Path(persist_dir).expanduser()
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.model_name = model_name
        self.collection_name = collection_name
        
        # Initialize embedding model
        self._encoder: SentenceTransformer | None = None
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},  # Use cosine similarity
        )
    
    @property
    def encoder(self) -> SentenceTransformer:
        """Lazy load the encoder model."""
        if self._encoder is None:
            self._encoder = SentenceTransformer(self.model_name)
        return self._encoder
    
    def index(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        doc_id: str | None = None,
    ) -> str:
        """Add content to the vector store.
        
        Args:
            content: Text content to index
            metadata: Optional metadata dictionary
            doc_id: Optional document ID (auto-generated if not provided)
            
        Returns:
            Document ID
        """
        doc = RAGDocument(content=content, metadata=metadata or {}, doc_id=doc_id)
        
        # Add timestamp if not present
        if "indexed_at" not in doc.metadata:
            doc.metadata["indexed_at"] = datetime.utcnow().isoformat()
        
        # Generate embedding
        embedding = self.encoder.encode(content).tolist()
        
        # Upsert to ChromaDB
        self.collection.upsert(
            ids=[doc.doc_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[doc.metadata],
        )
        
        return doc.doc_id
    
    def index_batch(
        self,
        documents: list[RAGDocument],
        batch_size: int = 100,
    ) -> list[str]:
        """Index multiple documents in batches.
        
        Args:
            documents: List of documents to index
            batch_size: Number of documents per batch
            
        Returns:
            List of document IDs
        """
        doc_ids: list[str] = []
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            ids = [d.doc_id for d in batch]
            contents = [d.content for d in batch]
            metadatas = [d.metadata for d in batch]
            
            # Generate embeddings for batch
            embeddings = self.encoder.encode(contents).tolist()
            
            # Add timestamps
            for meta in metadatas:
                if "indexed_at" not in meta:
                    meta["indexed_at"] = datetime.utcnow().isoformat()
            
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=contents,
                metadatas=metadatas,
            )
            
            doc_ids.extend(ids)
        
        return doc_ids
    
    def query(
        self,
        question: str,
        top_k: int = 5,
        threshold: float = 0.0,
        where: dict[str, Any] | None = None,
    ) -> list[RAGResult]:
        """Semantic search for relevant documents.
        
        Args:
            question: Query text
            top_k: Maximum number of results
            threshold: Minimum similarity score (0.0-1.0)
            where: Optional ChromaDB filter
            
        Returns:
            List of RAGResult objects sorted by relevance
        """
        # Generate query embedding
        query_embedding = self.encoder.encode(question).tolist()
        
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        
        # Convert to RAGResult objects
        rag_results: list[RAGResult] = []
        
        if not results["ids"] or not results["ids"][0]:
            return rag_results
        
        for i, doc_id in enumerate(results["ids"][0]):
            # ChromaDB returns distances, convert to similarity scores
            # For cosine distance: similarity = 1 - distance
            distance = results["distances"][0][i] if results["distances"] else 0
            score = 1.0 - distance
            
            if score < threshold:
                continue
            
            rag_results.append(RAGResult(
                content=results["documents"][0][i] if results["documents"] else "",
                metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                score=score,
                doc_id=doc_id,
            ))
        
        return rag_results
    
    def delete(self, doc_ids: list[str]) -> None:
        """Delete documents by ID.
        
        Args:
            doc_ids: List of document IDs to delete
        """
        self.collection.delete(ids=doc_ids)
    
    def clear(self) -> None:
        """Clear all documents from the collection."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
    
    @property
    def count(self) -> int:
        """Get the number of documents in the collection."""
        return self.collection.count()
    
    def get_by_platform(self, platform: str, limit: int = 100) -> list[RAGResult]:
        """Get all documents for a specific platform.
        
        Args:
            platform: Platform name to filter by
            limit: Maximum number of results
            
        Returns:
            List of RAGResult objects
        """
        results = self.collection.get(
            where={"platform": platform},
            limit=limit,
            include=["documents", "metadatas"],
        )
        
        rag_results: list[RAGResult] = []
        
        if not results["ids"]:
            return rag_results
        
        for i, doc_id in enumerate(results["ids"]):
            rag_results.append(RAGResult(
                content=results["documents"][i] if results["documents"] else "",
                metadata=results["metadatas"][i] if results["metadatas"] else {},
                score=1.0,  # No distance for direct get
                doc_id=doc_id,
            ))
        
        return rag_results
    
    def export_to_json(self, output_path: Path) -> int:
        """Export all documents to JSON file.
        
        Args:
            output_path: Path for output file
            
        Returns:
            Number of documents exported
        """
        all_docs = self.collection.get(include=["documents", "metadatas"])
        
        export_data = []
        for i, doc_id in enumerate(all_docs["ids"]):
            export_data.append({
                "id": doc_id,
                "content": all_docs["documents"][i] if all_docs["documents"] else "",
                "metadata": all_docs["metadatas"][i] if all_docs["metadatas"] else {},
            })
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)
        
        return len(export_data)
    
    def import_from_json(self, input_path: Path) -> int:
        """Import documents from JSON file.
        
        Args:
            input_path: Path to JSON file
            
        Returns:
            Number of documents imported
        """
        with open(input_path) as f:
            data = json.load(f)
        
        documents = [
            RAGDocument(
                content=item["content"],
                metadata=item.get("metadata", {}),
                doc_id=item.get("id"),
            )
            for item in data
        ]
        
        self.index_batch(documents)
        return len(documents)
