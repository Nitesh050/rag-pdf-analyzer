"""
Generation eval: is the final answer right, grounded, cited and honest?

    cd apps/api
    .venv/bin/python -m evals.run_generation --name gen-baseline
    .venv/bin/python -m evals.run_generation --num-ctx 8192 --name gen-ctx8k
    .venv/bin/python -m evals.run_generation --from gen-baseline --judge-model qwen2.5:7b

Runs the real RAGChain (intent routing, hybrid retrieval scoped to the
question's document, prompt, LLM) over the golden set, then scores:

  Answerable questions
    correctness     judge: correct / partial / incorrect vs reference (1 / 0.5 / 0)
    grounded        judge: every claim supported by the context the model saw
                    (unvalidated: local judges don't detect this reliably yet)
    false_refusal   said "not found" although the answer was in the document
    has_citation    cites at least one "Source N"
    citation_valid  cited sources exist and their stated pages are right
    cites_gold      cites a source that is a gold page
    number_recall   numbers from the reference that appear in the answer

  Unanswerable questions
    refusal         said "not found" instead of inventing an answer

  System
    prompt_truncated  prompt hit the model's num_ctx and was silently cut

Generation and judging run as separate phases so Ollama doesn't swap
models on every question. --from re-judges a saved run without
regenerating answers.
"""

import argparse
import hashlib
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean

from src.generation.ollama_client import OllamaClient
from src.generation.prompt_templates import PromptBuilder
from src.generation.rag_chain import RAGChain

from .harness import RESULTS_DIR, build_index, chunk_corpus, load_corpus, load_golden
from .judge import Judge
from .metrics import citation_scores, is_refusal, number_recall, parse_citations, percentile

DEFAULT_NUM_CTX = 2048  # Ollama's default when num_ctx isn't set


class RecordingClient:
    """Wraps OllamaClient to keep token counts from each response."""

    def __init__(self, client: OllamaClient):
        self.client = client
        self.num_ctx = client.llm.num_ctx or DEFAULT_NUM_CTX
        self.last: dict = {}

    def generate(self, prompt: str) -> str:
        response = self.client.llm.invoke(prompt)
        meta = response.response_metadata or {}
        prompt_tokens = meta.get("prompt_eval_count") or 0
        self.last = {
            "prompt_chars": len(prompt),
            "prompt_tokens": prompt_tokens,
            "output_tokens": meta.get("eval_count"),
            # Ollama caps evaluated prompt tokens at num_ctx when it truncates.
            "prompt_truncated": prompt_tokens >= self.num_ctx * 0.98,
        }
        return response.content


def generate(golden: list[dict], args) -> list[dict]:
    chunks = chunk_corpus(load_corpus())
    manager = build_index(chunks, reranker_model=args.reranker)

    client = OllamaClient(model=args.model)
    if args.num_ctx:
        client.llm.num_ctx = args.num_ctx
    recorder = RecordingClient(client)

    chain = RAGChain(retrieval_manager=manager)
    chain.llm = recorder

    records = []
    for i, item in enumerate(golden, start=1):
        start = time.perf_counter()
        result = chain.ask(item["question"], document_id=item["doc"])
        latency = time.perf_counter() - start

        contexts = result.get("contexts", [])
        records.append({
            "id": item["id"],
            "doc": item["doc"],
            "type": item["type"],
            "question": item["question"],
            "gold_pages": item["gold_pages"],
            "reference": item["answer"],
            "intent": result.get("intent"),
            "answer": result["answer"],
            "contexts": [
                {"source": n, "page": c.metadata.get("page"), "text": c.page_content}
                for n, c in enumerate(contexts, start=1)
            ],
            "latency_s": round(latency, 2),
            **(recorder.last if contexts else {}),
        })
        print(f"  [{i}/{len(golden)}] {item['id']} {latency:.1f}s", flush=True)
        recorder.last = {}

    return records, recorder.num_ctx


def score(records: list[dict], judge: Judge | None) -> None:
    for i, record in enumerate(records, start=1):
        answer = record["answer"]
        refused = is_refusal(answer)
        checks = {"refused": refused}

        if record["type"] != "unanswerable":
            gold = {(record["doc"], p) for p in record["gold_pages"]}
            context_pages = [(record["doc"], c["page"]) for c in record["contexts"]]
            checks.update(citation_scores(parse_citations(answer), context_pages, gold))
            if not gold:
                # Summaries have no single right page to cite.
                checks["cites_gold"] = None
            # Only numeric questions hinge on exact figures; elsewhere
            # incidental numbers in the reference make this noise.
            if record["type"] == "numeric":
                checks["number_recall"] = number_recall(record["reference"], answer)

            if judge:
                context = PromptBuilder._build_context([
                    _as_document(c, record["doc"]) for c in record["contexts"]
                ])
                record["judge"] = judge.grade(record["question"], record["reference"], context, answer, refused)
                print(f"  judged [{i}/{len(records)}] {record['id']}: "
                      f"{record['judge'].get('correctness', 'ERROR')}", flush=True)

        record["checks"] = checks


def _as_document(context: dict, doc: str):
    from langchain_core.documents import Document
    return Document(page_content=context["text"], metadata={"source": doc, "page": context["page"]})


def summarize(records: list[dict]) -> dict:
    answerable = [r for r in records if r["type"] != "unanswerable"]
    unanswerable = [r for r in records if r["type"] == "unanswerable"]
    judged = [r for r in answerable if "correctness_score" in r.get("judge", {})]

    def avg(values):
        values = [v for v in values if v is not None]
        return round(mean(values), 4) if values else None

    def answer_metrics(rows):
        rows_judged = [r for r in rows if "correctness_score" in r.get("judge", {})]
        cited = [r for r in rows if r["checks"].get("has_citation")]
        return {
            "n": len(rows),
            "correctness": avg(r["judge"]["correctness_score"] for r in rows_judged),
            "fully_correct": avg(float(r["judge"]["correctness_score"] == 1.0) for r in rows_judged),
            "grounded": avg(float(r["judge"]["grounded"]) for r in rows_judged),
            "false_refusal": avg(float(r["checks"]["refused"]) for r in rows),
            "has_citation": avg(r["checks"]["has_citation"] for r in rows),
            "citation_valid": avg(r["checks"]["citation_valid"] for r in cited),
            "cites_gold": avg(r["checks"].get("cites_gold") for r in rows),
            "number_recall": avg(r["checks"].get("number_recall") for r in rows),
        }

    by_type = defaultdict(list)
    for r in answerable:
        by_type[r["type"]].append(r)

    with_tokens = [r for r in records if r.get("prompt_tokens")]
    latencies = [r["latency_s"] for r in records]

    return {
        "judge_agreement": judge_agreement(judged),
        "answerable": answer_metrics(answerable),
        "unanswerable": {
            "n": len(unanswerable),
            "refusal": avg(float(r["checks"]["refused"]) for r in unanswerable),
        },
        "system": {
            "latency_s_p50": round(percentile(latencies, 50), 2),
            "latency_s_p95": round(percentile(latencies, 95), 2),
            "max_prompt_tokens": max((r["prompt_tokens"] for r in with_tokens), default=0),
            "prompts_truncated": sum(bool(r.get("prompt_truncated")) for r in records),
            "judge_errors": len(answerable) - len(judged) if judged else None,
        },
        "by_type": {t: answer_metrics(rows) for t, rows in sorted(by_type.items())},
        "by_intent": {
            intent: {
                "n": len(rows),
                "prompts_truncated": sum(bool(r.get("prompt_truncated")) for r in rows),
                "correctness": avg(r["judge"]["correctness_score"] for r in rows if "correctness_score" in r.get("judge", {})),
            }
            for intent, rows in sorted(_group(records, "intent").items())
        },
    }


def judge_agreement(judged: list[dict]) -> dict | None:
    """
    How often the judge's correctness label matches the human label in
    evals/judge_labels.jsonl. Only answers identical to the labelled ones
    count, since a regenerated answer may deserve a different grade.
    """
    path = RESULTS_DIR.parent / "judge_labels.jsonl"
    if not path.exists():
        return None

    human = {}
    for line in path.read_text().splitlines():
        if line.strip():
            label = json.loads(line)
            human[(label["id"], label["answer_sha"])] = label

    pairs, grounding = [], []
    for r in judged:
        key = (r["id"], hashlib.sha256(r["answer"].encode()).hexdigest()[:16])
        if key in human:
            pairs.append((human[key]["label"], r["judge"]["correctness"], r["id"]))
            grounding.append((human[key].get("grounded"), r["judge"]["grounded"], r["id"]))

    if not pairs:
        return None

    return {
        "n": len(pairs),
        "exact": round(sum(h == j for h, j, _ in pairs) / len(pairs), 4),
        "human_score": round(mean({"correct": 1, "partial": .5, "incorrect": 0}[h] for h, _, _ in pairs), 4),
        "judge_score": round(mean({"correct": 1, "partial": .5, "incorrect": 0}[j] for _, j, _ in pairs), 4),
        "disagreements": [f"{i}: human={h} judge={j}" for h, j, i in pairs if h != j],
        # Detecting ungrounded answers: how many of the human-flagged ones
        # the judge caught, and which judge flags were false alarms.
        "ungrounded_caught": f"{sum(h is False and j is False for h, j, _ in grounding)}"
                             f"/{sum(h is False for h, _, _ in grounding)}",
        "ungrounded_false_alarms": [i for h, j, i in grounding if h is True and j is False],
    }


def _group(records, field):
    groups = defaultdict(list)
    for r in records:
        groups[r.get(field)].append(r)
    return groups


def print_summary(summary: dict) -> None:
    a, u, s = summary["answerable"], summary["unanswerable"], summary["system"]

    def fmt(v):
        return "  -  " if v is None else f"{v:.3f}"

    print(f"\nAnswerable ({a['n']})")
    for key in ["correctness", "fully_correct", "grounded", "false_refusal",
                "has_citation", "citation_valid", "cites_gold", "number_recall"]:
        # Neither local judge (llama3, qwen2.5) flagged unsupported claims
        # reliably against human review, so this one is not trusted yet.
        note = "  (unvalidated)" if key == "grounded" else ""
        print(f"  {key:<16}{fmt(a[key])}{note}")
    print(f"Unanswerable ({u['n']})\n  {'refusal':<16}{fmt(u['refusal'])}")
    print(f"System\n  latency p50/p95  {s['latency_s_p50']}s / {s['latency_s_p95']}s"
          f"\n  max prompt tok   {s['max_prompt_tokens']}"
          f"\n  truncated        {s['prompts_truncated']} prompts")

    agreement = summary.get("judge_agreement")
    if agreement:
        print(f"Judge vs human labels ({agreement['n']})"
              f"\n  exact agreement  {agreement['exact']:.3f}"
              f"\n  score human/judge {agreement['human_score']:.3f} / {agreement['judge_score']:.3f}")
        for line in agreement["disagreements"]:
            print(f"    {line}")
        print(f"  ungrounded caught   {agreement['ungrounded_caught']}"
              f"\n  false alarms        {agreement['ungrounded_false_alarms']}")

    print(f"\n{'type':<12}{'n':>3}{'correct':>9}{'grounded':>10}{'cited':>8}")
    for name, m in summary["by_type"].items():
        print(f"{name:<12}{m['n']:>3}{fmt(m['correctness']):>9}{fmt(m['grounded']):>10}{fmt(m['has_citation']):>8}")
    print(f"\n{'intent':<12}{'n':>3}{'trunc':>7}{'correct':>9}")
    for name, m in summary["by_intent"].items():
        print(f"{str(name):<12}{m['n']:>3}{m['prompts_truncated']:>7}{fmt(m['correctness']):>9}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", default=datetime.now().strftime("gen-%Y%m%d-%H%M%S"))
    parser.add_argument("--model", default="qwen2.5:7b", help="answer model")
    parser.add_argument("--num-ctx", type=int, help="override the answer model's context window")
    parser.add_argument("--reranker", help="cross-encoder model, off by default like production")
    parser.add_argument("--judge-model", default="llama3:latest")
    parser.add_argument("--no-judge", action="store_true", help="deterministic checks only")
    parser.add_argument("--from", dest="from_run", help="re-score a saved run instead of generating")
    parser.add_argument("--only", help="comma-separated question ids")
    args = parser.parse_args()

    if args.from_run:
        saved = json.loads((RESULTS_DIR / f"{args.from_run}.json").read_text())
        records, config = saved["questions"], saved["config"]
        for r in records:
            r.pop("judge", None)
    else:
        golden = load_golden()
        if args.only:
            wanted = set(args.only.split(","))
            golden = [q for q in golden if q["id"] in wanted]
        print(f"Generating {len(golden)} answers with {args.model}")
        records, num_ctx = generate(golden, args)
        config = {
            "model": args.model,
            "num_ctx": num_ctx,
            "reranker": args.reranker,
        }

    judge = None if args.no_judge else Judge(model=args.judge_model)
    if judge:
        print(f"Judging with {judge.model}")
    score(records, judge)
    config["judge"] = judge.model if judge else None

    summary = summarize(records)
    print_summary(summary)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"{args.name}.json"
    out.write_text(json.dumps({
        "name": args.name,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": config,
        "summary": summary,
        "questions": records,
    }, indent=2))
    print(f"\nSaved {out.relative_to(RESULTS_DIR.parent.parent)}")


if __name__ == "__main__":
    main()
