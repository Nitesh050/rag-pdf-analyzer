from evals.run_routing import evaluate, load_items


def test_every_labelled_question_routes_correctly():
    """
    Guards the rule-based intent detector and page parser against
    regressions: every question in evals/routing.jsonl must route as
    labelled. Run `python -m evals.run_routing` to see which ones fail.
    """
    result = evaluate(load_items())

    assert result["intent_errors"] == []
    assert result["page_errors"] == []
