"""
Retrieval metrics at page granularity.

Ground truth is a set of (doc, page) pairs rather than chunk ids, so the
golden set stays valid when chunking changes. A retrieved chunk counts as
relevant when its (document_id, page) is in the gold set.
"""

import re
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


# ---------------------------------------------------------------------------
# Generation checks. Deterministic, so they don't depend on the LLM judge.
# ---------------------------------------------------------------------------

REFUSAL_MARKERS = (
    "couldn't find the answer",
    "could not find the answer",
    "couldn't find any relevant information",
    "not found in the provided document",
    "does not contain information",
    "doesn't contain information",
    "no information about",
)

CITATION = re.compile(r"source\s*(\d+)(?:[^)\]\n]{0,40}?pages?\s*(\d+))?", re.IGNORECASE)
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def is_refusal(answer: str) -> bool:
    text = answer.lower().replace("’", "'")
    return any(marker in text for marker in REFUSAL_MARKERS)


def parse_citations(answer: str) -> list[tuple[int, int | None]]:
    """(source number, page or None) for each "Source N[, page P]" mention."""
    return [
        (int(source), int(page) if page else None)
        for source, page in CITATION.findall(answer)
    ]


def citation_scores(
    citations: list[tuple[int, int | None]],
    context_pages: list[Page],
    gold: set[Page],
) -> dict:
    """
    has_citation: the answer cites at least one source.
    citation_valid: share of citations that name a real source and, when a
        page is given, the page that source is actually from.
    cites_gold: at least one cited source is a gold page.
    """
    if not citations:
        return {"has_citation": 0.0, "citation_valid": 0.0, "cites_gold": 0.0}

    valid = 0
    cited_pages = set()
    for source, page in citations:
        if 1 <= source <= len(context_pages):
            actual = context_pages[source - 1]
            if page is None or page == actual[1]:
                valid += 1
            cited_pages.add(actual)

    return {
        "has_citation": 1.0,
        "citation_valid": valid / len(citations),
        "cites_gold": float(bool(cited_pages & gold)),
    }


def number_recall(reference: str, answer: str) -> float | None:
    """
    Share of the numbers in the reference answer that also appear in the
    answer (commas ignored). None when the reference has no numbers.
    """
    def numbers(text: str) -> set[str]:
        return {n.replace(",", "").rstrip(".") for n in NUMBER.findall(text)}

    expected = numbers(reference)
    if not expected:
        return None
    return len(expected & numbers(answer)) / len(expected)
