from typing import List, Optional

from langchain_core.documents import Document

from .hybrid_search import HybridRetriever
from .reranker import Reranker
from .vector_store import VectorStore
from .filters import build_chroma_filter, merge_filters


class RetrievalManager:
	"""
	High level retrieval orchestrator.

	- Builds keyword index for BM25
	- Performs semantic, keyword or hybrid retrieval
	- Optionally reranks results using a cross-encoder
	- Accepts simple filter dicts which are converted to Chroma filters
	"""

	def __init__(
		self,
		reranker_model: Optional[str] = None,
		rerank_overfetch_multiplier: int = 3,
		min_rerank_fetch_k: int = 20,
	):

		self.vector_store = VectorStore()

		self.hybrid = HybridRetriever()

		# Reranker is optional — only instantiate if requested
		self.reranker: Optional[Reranker] = None

		if reranker_model:
			self.reranker = Reranker(model_name=reranker_model)

		# When reranking, the initial retrieval must pull a wider candidate
		# pool than top_k — otherwise the reranker only ever sees exactly
		# top_k documents and can merely reorder them instead of surfacing
		# better candidates that ranked just outside the cutoff.
		self.rerank_overfetch_multiplier = rerank_overfetch_multiplier
		self.min_rerank_fetch_k = min_rerank_fetch_k

	# ---------------------------------------------------------
	def build_indexes(self) -> None:
		"""Build any secondary indexes (e.g., BM25) used by hybrid retrieval."""

		self.hybrid.build_keyword_index()

	# ---------------------------------------------------------
	def _compute_fetch_k(self, top_k: int, will_rerank: bool) -> int:
		"""How many candidates to retrieve before any reranking step."""

		if not will_rerank:
			return top_k

		return max(top_k * self.rerank_overfetch_multiplier, self.min_rerank_fetch_k)

	# ---------------------------------------------------------
	def retrieve(
		self,
		query: str,
		top_k: int = 5,
		use_hybrid: bool = True,
		rerank: bool = True,
		filters: Optional[dict] = None,
	) -> List[Document]:
		"""
		Retrieve documents for `query`.

		- `use_hybrid`: combine semantic + BM25 via RRF
		- `rerank`: apply cross-encoder reranker if available
		- `filters`: optional metadata filters to narrow results
		"""

		chroma_filter = build_chroma_filter(filters)

		will_rerank = rerank and self.reranker is not None
		fetch_k = self._compute_fetch_k(top_k, will_rerank)

		if use_hybrid:

			# Hybrid retriever uses the VectorStore internally for semantic
			# search and BM25 for keywords. BM25 index should be built
			# beforehand via `build_indexes()` when documents change.

			results = self.hybrid.retrieve(query=query, k=fetch_k, filter=chroma_filter)

		else:

			# Semantic-only search via the vector store
			results = self.vector_store.similarity_search(
				query=query,
				k=fetch_k,
				filter=chroma_filter,
			)

		if will_rerank:

			return self.reranker.rerank(
				query=query,
				documents=results,
				top_k=top_k,
			)

		# Default: return up to top_k results
		return results[:top_k]

