from typing import List, Dict, Any, Optional
import numpy as np
from rank_bm25 import BM25Okapi
import re

class HybridRetriever:
    """Combines BM25 lexical search with dense vector similarity and metadata filtering."""

    def __init__(self, embedding_model_name: Optional[str] = None):
        self.documents: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.dense_embeddings: Optional[np.ndarray] = None
        self.embedding_model_name = embedding_model_name
        self._embedder = None

    def _tokenize(self, text: str) -> List[str]:
        # Simple multilingual whitespace & punctuation tokenization
        tokens = re.findall(r"\w+", text.lower())
        return tokens

    def add_documents(self, docs: List[Dict[str, Any]]):
        self.documents.extend(docs)
        new_tokens = [self._tokenize(d.get("text", "")) for d in docs]
        self.tokenized_corpus.extend(new_tokens)
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def build_embeddings(self):
        """Build dense embeddings for documents using sentence-transformers."""
        if not self.embedding_model_name or len(self.documents) == 0:
            return

        try:
            from sentence_transformers import SentenceTransformer
            if self._embedder is None:
                self._embedder = SentenceTransformer(self.embedding_model_name)
            
            texts = [d.get("text", "") for d in self.documents]
            self.dense_embeddings = self._embedder.encode(
                texts, show_progress_bar=False, normalize_embeddings=True
            )
        except Exception as e:
            print(f"[Warning] Failed to build dense embeddings: {e}. Falling back to BM25.")
            self.dense_embeddings = None

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        source_filter: Optional[List[str]] = None,
        alpha: float = 0.5  # Weight between BM25 (1 - alpha) and Dense (alpha)
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top_k relevant documents using Reciprocal Rank Fusion or linear score combination.
        Applies source_filter if provided.
        """
        if not self.documents or not self.bm25:
            return []

        query_tokens = self._tokenize(query)
        bm25_scores = np.array(self.bm25.get_scores(query_tokens))

        # Normalize BM25 scores to [0, 1]
        if bm25_scores.max() > bm25_scores.min():
            bm25_norm = (bm25_scores - bm25_scores.min()) / (bm25_scores.max() - bm25_scores.min())
        else:
            bm25_norm = np.zeros_like(bm25_scores)

        # Dense scores if available
        if self.dense_embeddings is not None and self._embedder is not None:
            query_emb = self._embedder.encode([query], normalize_embeddings=True)[0]
            dense_scores = np.dot(self.dense_embeddings, query_emb)
            # Cosine similarity is in [-1, 1], map to [0, 1]
            dense_norm = np.clip((dense_scores + 1.0) / 2.0, 0, 1)
            combined_scores = (1 - alpha) * bm25_norm + alpha * dense_norm
        else:
            combined_scores = bm25_norm

        # Filter and rank
        results = []
        ranked_indices = np.argsort(combined_scores)[::-1]

        for idx in ranked_indices:
            doc = self.documents[idx]
            
            # Apply source filter if specified
            if source_filter:
                doc_source = doc.get("source_id", "")
                doc_file = doc.get("filename", "")
                if not any(sf in doc_source or sf in doc_file for sf in source_filter):
                    continue

            results.append({
                "score": float(combined_scores[idx]),
                "bm25_score": float(bm25_norm[idx]),
                "document": doc,
            })

            if len(results) >= top_k:
                break

        return results
