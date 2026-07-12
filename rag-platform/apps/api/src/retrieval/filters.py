from typing import Any, Dict, Optional


def build_chroma_filter(
	filters: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
	"""
	Convert a simple filter dict into a Chroma-compatible filter.

	Expected incoming `filters` examples:
	  {"filename": "foo.pdf"}
	  {"source": "web", "page": 4}
	  {"document_id": "abc", "tags": ["term1","term2"]}

	This function performs light validation and normalisation and
	returns None when no filters are provided.
	"""

	if not filters:
		return None

	chroma_filter: Dict[str, Any] = {}

	for key, value in filters.items():

		# Chroma expects exact matches or lists for OR behaviour.
		# Pass values through, but coerce tuples/sets to lists.
		if isinstance(value, (tuple, set)):
			chroma_filter[key] = list(value)
		else:
			chroma_filter[key] = value

	return chroma_filter


def merge_filters(*filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
	"""Merge multiple filter dicts into one. Later filters override earlier ones."""

	merged: Dict[str, Any] = {}

	for f in filters:
		if not f:
			continue
		for k, v in f.items():
			merged[k] = v

	return merged or None

