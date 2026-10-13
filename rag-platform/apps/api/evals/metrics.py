"""
Retrieval metrics at page granularity.

Ground truth is a set of (doc, page) pairs rather than chunk ids, so the
golden set stays valid when chunking changes. A retrieved chunk counts as
relevant when its (document_id, page) is in the gold set.
"""

from statistics import mean

Page = tuple[str, int]


def hit_at_k(retrieved: list[Page], gold: set[Page], k: int) -> float:
    """1.0 if any of the top-k chunks lands on a gold page."""
    return float(any(page in gold for page in retrieved[:k]))


def recall_at_k(retrieved: list[Page], gold: set[Page], k: int) -> float:
    """Fraction of gold pages covered by the top-k chunks."""
    if not gold:
        return 0.0
    return len(gold & set(retrieved[:k])) / len(gold)


def precision_at_k(retrieved: list[Page], gold: set[Page], k: int) -> float:
    """
    Fraction of the top-k chunks that are on a gold page. Low precision
    means the LLM gets more irrelevant context it has to ignore.
    """
    top = retrieved[:k]
    if not top:
        return 0.0
    return sum(page in gold for page in top) / len(top)


def reciprocal_rank(retrieved: list[Page], gold: set[Page], k: int) -> float:
    """1/rank of the first relevant chunk within the top-k, else 0."""
    for rank, page in enumerate(retrieved[:k], start=1):
        if page in gold:
            return 1.0 / rank
    return 0.0


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1)))
    return ordered[index]


def score_question(retrieved: list[Page], gold: set[Page], ks: list[int]) -> dict:
    scores = {"mrr@10": reciprocal_rank(retrieved, gold, 10)}
    for k in ks:
        scores[f"hit@{k}"] = hit_at_k(retrieved, gold, k)
        scores[f"recall@{k}"] = recall_at_k(retrieved, gold, k)
    scores["precision@5"] = precision_at_k(retrieved, gold, 5)
    return scores


def aggregate(per_question: list[dict]) -> dict:
    """Mean of every metric across questions."""
    if not per_question:
        return {}
    keys = per_question[0].keys()
    return {key: round(mean(q[key] for q in per_question), 4) for key in keys}
