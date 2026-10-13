from evals.metrics import (
    aggregate,
    hit_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)

GOLD = {("book", 10), ("book", 11)}
RETRIEVED = [("book", 3), ("book", 10), ("book", 10), ("slides", 11), ("book", 11)]


def test_hit_at_k_only_counts_top_k():
    assert hit_at_k(RETRIEVED, GOLD, 1) == 0.0
    assert hit_at_k(RETRIEVED, GOLD, 2) == 1.0


def test_recall_counts_distinct_gold_pages():
    # Two chunks from page 10 still cover only one of the two gold pages.
    assert recall_at_k(RETRIEVED, GOLD, 3) == 0.5
    assert recall_at_k(RETRIEVED, GOLD, 5) == 1.0


def test_page_must_match_document():
    # Page 11 of a different document is not relevant.
    assert recall_at_k(RETRIEVED, GOLD, 4) == 0.5


def test_precision_and_reciprocal_rank():
    assert precision_at_k(RETRIEVED, GOLD, 5) == 3 / 5
    assert reciprocal_rank(RETRIEVED, GOLD, 10) == 0.5
    assert reciprocal_rank([("book", 1)], GOLD, 10) == 0.0


def test_aggregate_means_each_metric():
    assert aggregate([{"hit@1": 1.0}, {"hit@1": 0.0}]) == {"hit@1": 0.5}
