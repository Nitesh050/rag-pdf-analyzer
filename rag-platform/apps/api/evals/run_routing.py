"""
Routing eval: does each question take the right path through RAGChain?

    cd apps/api
    .venv/bin/python -m evals.run_routing             # dev + test
    .venv/bin/python -m evals.run_routing --split dev

Checks two things, both deterministic (no LLM, runs instantly):

  intent  the question type IntentRouter picks (qa, summary, explanation,
          comparison, chapter, metadata). It decides how much context is
          retrieved and whether summaries are used.
  pages   the page numbers parse_page_refs extracts. Questions naming pages
          bypass intent routing and fetch those pages directly.

Labels live in evals/routing.jsonl. Tune the detector against the dev
split only; the test split shows whether changes generalise.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from src.generation.intent.router import IntentRouter
from src.generation.page_refs import parse_page_refs

ROUTING_FILE = Path(__file__).resolve().parent / "routing.jsonl"


def load_items() -> list[dict]:
    return [
        json.loads(line)
        for line in ROUTING_FILE.read_text().splitlines()
        if line.strip() and not line.startswith("//")
    ]


def evaluate(items: list[dict]) -> dict:
    router = IntentRouter()
    intent_rows, page_rows = [], []

    for item in items:
        pages = parse_page_refs(item["question"])
        page_rows.append((item, pages, pages == item["pages"]))

        # Questions naming pages skip intent routing entirely, so their
        # intent isn't scored.
        if item["intent"] is not None:
            predicted = router.route(item["question"]).value
            accepted = {item["intent"], *item.get("accept", [])}
            intent_rows.append((item, predicted, predicted in accepted))

    per_intent = {}
    for intent in sorted({i["intent"] for i, _, _ in intent_rows}):
        expected = [r for r in intent_rows if r[0]["intent"] == intent]
        predicted = [r for r in intent_rows if r[1] == intent]
        per_intent[intent] = {
            "n": len(expected),
            "recall": sum(ok for _, _, ok in expected) / len(expected),
            "precision": (sum(ok for _, _, ok in predicted) / len(predicted)) if predicted else None,
        }

    return {
        "intent_accuracy": sum(ok for _, _, ok in intent_rows) / len(intent_rows),
        "page_accuracy": sum(ok for _, _, ok in page_rows) / len(page_rows),
        "trap_accuracy": _trap_accuracy(intent_rows),
        "per_intent": per_intent,
        "confusions": Counter((i["intent"], p) for i, p, ok in intent_rows if not ok),
        "intent_errors": [(i, p) for i, p, ok in intent_rows if not ok],
        "page_errors": [(i, p) for i, p, ok in page_rows if not ok],
        "n_intent": len(intent_rows),
        "n_pages": len(page_rows),
    }


def _trap_accuracy(rows) -> float | None:
    traps = [ok for item, _, ok in rows if item.get("trap")]
    return sum(traps) / len(traps) if traps else None


def report(name: str, result: dict) -> None:
    def pct(v):
        return "  -  " if v is None else f"{v:.0%}"

    print(f"\n== {name}")
    print(f"  intent accuracy  {pct(result['intent_accuracy'])} of {result['n_intent']}"
          f"   (trap questions {pct(result['trap_accuracy'])})")
    print(f"  page refs        {pct(result['page_accuracy'])} of {result['n_pages']}")
    print(f"\n  {'intent':<12}{'n':>3}{'recall':>8}{'precision':>11}")
    for intent, m in result["per_intent"].items():
        print(f"  {intent:<12}{m['n']:>3}{pct(m['recall']):>8}{pct(m['precision']):>11}")

    if result["confusions"]:
        print("\n  confusions (expected -> got):")
        for (expected, got), n in result["confusions"].most_common():
            print(f"    {expected} -> {got}: {n}")
    for item, got in result["intent_errors"]:
        trap = f"  [trap: {item['trap']}]" if item.get("trap") else ""
        print(f"    {item['id']:<10} {item['question']!r}: expected {item['intent']}, got {got}{trap}")
    for item, got in result["page_errors"]:
        print(f"    {item['id']:<10} {item['question']!r}: pages expected {item['pages']}, got {got}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", choices=["dev", "test", "all"], default="all")
    args = parser.parse_args()

    items = load_items()
    splits = ["dev", "test"] if args.split == "all" else [args.split]
    for split in splits:
        report(split, evaluate([i for i in items if i["split"] == split]))


if __name__ == "__main__":
    main()
