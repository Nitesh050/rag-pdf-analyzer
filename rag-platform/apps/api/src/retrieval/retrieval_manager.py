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

	def __init__(self, reranker_model: Optional[str] = None):

		self.vector_store = VectorStore()

		self.hybrid = HybridRetriever()

		# Reranker is optional — only instantiate if requested
		self.reranker: Optional[Reranker] = None

		if reranker_model:
			self.reranker = Reranker(model_name=reranker_model)

	# ---------------------------------------------------------
	def build_indexes(self) -> None:
		"""Build any secondary indexes (e.g., BM25) used by hybrid retrieval."""

		self.hybrid.build_keyword_index()

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

		if use_hybrid:

			# Hybrid retriever uses the VectorStore internally for semantic
			# search and BM25 for keywords. BM25 index should be built
			# beforehand via `build_indexes()` when documents change.

			results = self.hybrid.retrieve(query=query, k=top_k)

		else:

			# Semantic-only search via the vector store
			results = self.vector_store.similarity_search(
				query=query,
				k=top_k,
				filter=chroma_filter,
			)

		if rerank and self.reranker:

			# Increase candidate pool before reranking to improve recall
			candidates = results if len(results) >= top_k else results

			return self.reranker.rerank(
				query=query,
				documents=candidates,
				top_k=top_k,
			)

		# Default: return up to top_k results
		return results[:top_k]

