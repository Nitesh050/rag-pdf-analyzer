# Evals

Run from `apps/api` with the venv and Ollama running.

| Eval | Command | Measures |
|---|---|---|
| Retrieval | `.venv/bin/python -m evals.run_retrieval --name <run>` | Does the right page reach the LLM (hit@k, MRR, precision) |
| Generation | `.venv/bin/python -m evals.run_generation --name <run>` | Is the answer correct, cited, and does it refuse when it should |
| Routing | `.venv/bin/python -m evals.run_routing` | Does each question get the right type (qa, summary, comparison...) and page refs; instant, no LLM |

Results go to `results/<run>.json`. The corpus PDFs live in `corpus/` (gitignored) and are pinned by sha256 in `corpus.json`.

## Routing

`routing.jsonl` labels 74 questions with the route they should take, including traps for substring matching ("authorized", "TVs", "expedition", "how many pages"). Tune the detector on the `dev` split only and check `test` afterwards. `tests/unit/test_intent_routing.py` fails if any labelled question misroutes.

| Detector | Dev | Test | Trap questions |
|---|---|---|---|
| Substring keywords (before) | 52% | 35% | 0% |
| Whole-word patterns with priority order | 100% | 100% | 100% |

The test split was written by the same person as the rules, so treat 100% as an upper bound; add real user questions that misroute to the file as they come up.

## Judge

Correctness is graded by a local LLM judge (`judge.py`, default `llama3:latest`) using a key-fact checklist; refusals, citations and numbers are checked in code.

`judge_labels.jsonl` holds human grades for the 49 answers in `results/gen-01-baseline.json`. Every generation run reports how well the judge agrees with them.

| Judge | Correctness agreement | Ungrounded answers caught |
|---|---|---|
| llama3 (8B), key-fact checklist | 92% | 0/3 |
| qwen2.5:7b, key-fact checklist | 82% | many false alarms |

Groundedness is reported as **unvalidated** until a judge catches ungrounded answers reliably.

### Swapping in a stronger judge

1. Pull it: `ollama pull qwen2.5:14b` (resumes if interrupted).
2. Re-grade the labelled answers without regenerating them:
   `.venv/bin/python -m evals.run_generation --from gen-01-baseline --judge-model qwen2.5:14b --name judge-cal-qwen14b`
3. Adopt it only if `exact agreement` is at least as good as llama3's and `ungrounded caught` improves without false alarms. Then change the default in `judge.py` (and `--judge-model` in `run_generation.py`), and drop the "unvalidated" note on groundedness.

## Noise

Answers are sampled at temperature 0.2, so two runs of the same config differ by about ±2 questions (±0.03 correctness). Treat smaller differences as noise.
