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


from evals.metrics import citation_scores, is_refusal, number_recall, parse_citations


def test_is_refusal_matches_prompt_phrase_and_curly_apostrophe():
    assert is_refusal("I couldn’t find the answer in the provided document(s).")
    assert not is_refusal("The answer is 0.6 (Source 1, page 15).")


def test_parse_citations_with_and_without_page():
    answer = "It is 302 (Source 2, page 42). See also Source 3."
    assert parse_citations(answer) == [(2, 42), (3, None)]


def test_citation_scores_checks_page_against_cited_source():
    context = [("book", 41), ("book", 42)]
    gold = {("book", 42)}

    good = citation_scores([(2, 42)], context, gold)
    assert good == {"has_citation": 1.0, "citation_valid": 1.0, "cites_gold": 1.0}

    # Source 1 is page 41, so claiming page 42 for it is an invalid citation.
    wrong_page = citation_scores([(1, 42)], context, gold)
    assert wrong_page["citation_valid"] == 0.0
    assert wrong_page["cites_gold"] == 0.0

    assert citation_scores([], context, gold)["has_citation"] == 0.0


def test_number_recall_ignores_commas():
    assert number_recall("60,000 training and 10,000 test", "60000 and 10,000") == 1.0
    assert number_recall("0.9473 accuracy", "about 95%") == 0.0
    assert number_recall("no numbers here", "anything") is None


from evals.judge import grade_from_facts


def test_grade_from_facts():
    assert grade_from_facts([{"present": True}, {"present": True}]) == "correct"
    assert grade_from_facts([{"present": True}, {"present": False}]) == "partial"
    assert grade_from_facts([{"present": False}]) == "incorrect"
    assert grade_from_facts([]) == "incorrect"


def test_partial_answer_ending_with_gap_is_not_a_refusal():
    answer = ("The first guess was 0.5 (Source 1, page 14). " * 4
              + "The document does not contain information about later guesses.")
    assert not is_refusal(answer)
