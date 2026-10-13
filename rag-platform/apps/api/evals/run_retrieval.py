"""
Retrieval eval: how often does the right page reach the LLM?

    cd apps/api
    .venv/bin/python -m evals.run_retrieval --name baseline
    .venv/bin/python -m evals.run_retrieval --modes hybrid hybrid_rerank --scope doc

Modes:
    semantic       Chroma similarity only
    bm25           keyword only
    hybrid         semantic + BM25 fused with RRF (what /chat uses today)
    hybrid_rerank  hybrid, then cross-encoder rerank (RERANKER_MODEL)

Scopes:
    global  search every document (what /chat does today, no document_id)
    doc     filter to the question's document (/chat with document_id)

Writes evals/results/<name>.json with aggregate and per-question results.
"""

import argparse
import json
import time
from collections import defaultdict
from datetime import datetime, timezone

from .harness import RESULTS_DIR, build_index, chunk_corpus, load_corpus, load_golden
from .metrics import aggregate, percentile, score_question

KS = [1, 3, 5, 10]
MODES = ["semantic", "bm25", "hybrid", "hybrid_rerank"]
DEFAULT_RERANKER = "BAAI/bge-reranker-base"


def retrieve(manager, mode: str, question: str, filters: dict | None):
    if mode == "semantic":
        return manager.retrieve(question, top_k=max(KS), use_hybrid=False, rerank=False, filters=filters)
    if mode == "bm25":
        return manager.hybrid.keyword_search(question, k=max(KS), filter=filters)
    if mode == "hybrid":
        return manager.retrieve(question, top_k=max(KS), use_hybrid=True, rerank=False, filters=filters)
    if mode == "hybrid_rerank":
        return manager.retrieve(question, top_k=max(KS), use_hybrid=True, rerank=True, filters=filters)
    raise ValueError(f"Unknown mode: {mode}")


def evaluate(manager, golden: list[dict], mode: str, scope: str) -> dict:
    per_question = []
    latencies = []

    for item in golden:
        gold = {(item["doc"], page) for page in item["gold_pages"]}
        filters = {"document_id": item["doc"]} if scope == "doc" else None

        start = time.perf_counter()
        docs = retrieve(manager, mode, item["question"], filters)
        latencies.append((time.perf_counter() - start) * 1000)

        retrieved = [(d.metadata.get("document_id"), d.metadata.get("page")) for d in docs]
        scores = score_question(retrieved, gold, KS)

        per_question.append({
            "id": item["id"],
            "doc": item["doc"],
            "type": item["type"],
            "question": item["question"],
            "gold_pages": item["gold_pages"],
            "retrieved": [f"{doc}:p{page}" for doc, page in retrieved],
            "scores": scores,
        })

    def breakdown(field: str) -> dict:
        groups = defaultdict(list)
        for q in per_question:
            groups[q[field]].append(q["scores"])
        return {name: {"n": len(s), **aggregate(s)} for name, s in sorted(groups.items())}

    return {
        "overall": aggregate([q["scores"] for q in per_question]),
        "latency_ms": {
            "p50": round(percentile(latencies, 50), 1),
            "p95": round(percentile(latencies, 95), 1),
        },
        "by_type": breakdown("type"),
        "by_doc": breakdown("doc"),
        "questions": per_question,
    }


def print_table(results: dict) -> None:
    columns = ["hit@1", "hit@3", "hit@5", "hit@10", "recall@5", "mrr@10", "precision@5"]
    header = f"{'run':<28}" + "".join(f"{c:>12}" for c in columns) + f"{'p50 ms':>10}"
    print("\n" + header)
    print("-" * len(header))
    for run_name, run in results.items():
        row = f"{run_name:<28}" + "".join(f"{run['overall'][c]:>12.3f}" for c in columns)
        print(row + f"{run['latency_ms']['p50']:>10.0f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--modes", nargs="+", choices=MODES, default=MODES)
    parser.add_argument("--scope", nargs="+", choices=["global", "doc"], default=["global", "doc"])
    parser.add_argument("--reranker", default=DEFAULT_RERANKER)
    parser.add_argument("--keyword-weight", type=float, help="override BM25 weight in hybrid fusion")
    parser.add_argument("--name", default=datetime.now().strftime("%Y%m%d-%H%M%S"))
    parser.add_argument("--only", help="comma-separated question ids to run")
    args = parser.parse_args()

    corpus = load_corpus()
    golden = [q for q in load_golden() if q["gold_pages"]]  # unanswerables are for generation evals
    if args.only:
        wanted = set(args.only.split(","))
        golden = [q for q in golden if q["id"] in wanted]

    chunks = chunk_corpus(corpus)
    chunk_counts = defaultdict(int)
    for chunk in chunks:
        chunk_counts[chunk.metadata["document_id"]] += 1
    print(f"{len(golden)} questions, {len(chunks)} chunks {dict(chunk_counts)}")

    reranker = args.reranker if "hybrid_rerank" in args.modes else None
    manager = build_index(chunks, reranker_model=reranker)
    if args.keyword_weight is not None:
        manager.hybrid.keyword_weight = args.keyword_weight

    results = {}
    for scope in args.scope:
        for mode in args.modes:
            results[f"{mode}/{scope}"] = evaluate(manager, golden, mode, scope)

    print_table(results)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"{args.name}.json"
    out.write_text(json.dumps({
        "name": args.name,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": {
            "reranker": reranker,
            "keyword_weight": manager.hybrid.keyword_weight,
            "chunks": len(chunks),
            "chunks_per_doc": dict(chunk_counts),
            "questions": len(golden),
        },
        "runs": results,
    }, indent=2))
    print(f"\nSaved {out.relative_to(RESULTS_DIR.parent.parent)}")


if __name__ == "__main__":
    main()
