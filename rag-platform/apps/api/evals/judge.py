"""
LLM-as-judge for answer correctness and groundedness.

Small local judges are poor at holistic "rate this answer" verdicts: an
8B model graded refusals as correct and never used "partial" (see
evals/judge_labels.jsonl for the human labels it was checked against).
So the judge only answers narrow yes/no questions and code derives the
grade:

  1. Refusals are graded in code as incorrect, without the judge.
  2. The judge splits the reference answer into key facts and marks each
     one present or missing in the system answer.
     all present -> correct, some -> partial, none -> incorrect
  3. The judge lists claims in the answer that the context doesn't support.

Runs locally through Ollama; swap the model with --judge-model.
"""

import json

from langchain_ollama import ChatOllama

JUDGE_PROMPT = """You are checking an answer produced by a document question-answering system.

QUESTION:
{question}

REFERENCE ANSWER (written by a human who read the document):
{reference}

CONTEXT (the document excerpts the system was given):
{context}

SYSTEM ANSWER:
{answer}

Do two checks.

1. Split the REFERENCE ANSWER into its key facts (usually 1 to 4 short facts).
   For each fact, decide if the SYSTEM ANSWER states it (same meaning is enough,
   wording can differ). A fact the SYSTEM ANSWER gets wrong or leaves out is not present.

2. List every factual claim in the SYSTEM ANSWER that is NOT supported by the CONTEXT.
   Use only the CONTEXT, not your own knowledge. Ignore citation formatting.
   Use an empty list if every claim is supported.

Respond with JSON only, in this shape:
{{"facts": [{{"fact": "<key fact from the reference>", "present": true}}], "unsupported_claims": []}}"""

CORRECTNESS_SCORE = {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}


def grade_from_facts(facts: list[dict]) -> str:
    present = sum(bool(f.get("present")) for f in facts)
    if facts and present == len(facts):
        return "correct"
    if present:
        return "partial"
    return "incorrect"


def verdict(label: str, reason: str, grounded: bool, **extra) -> dict:
    return {
        "correctness": label,
        "correctness_score": CORRECTNESS_SCORE[label],
        "correctness_reason": reason,
        "grounded": grounded,
        **extra,
    }


class Judge:

    def __init__(self, model: str = "llama3:latest", num_ctx: int = 8192):
        # num_ctx must cover the whole judge prompt: Ollama silently
        # truncates anything beyond it (its default is only 2048 tokens).
        self.model = model
        self.llm = ChatOllama(model=model, temperature=0, format="json", num_ctx=num_ctx)

    def grade(self, question: str, reference: str, context: str, answer: str, refused: bool) -> dict:
        if refused:
            # The question is answerable, so "not found" is a wrong answer.
            # It makes no unsupported claims, so it counts as grounded.
            return verdict("incorrect", "refused an answerable question", True, facts=[], unsupported_claims=[])

        prompt = JUDGE_PROMPT.format(
            question=question,
            reference=reference,
            context=context,
            answer=answer,
        )

        for _ in range(2):
            try:
                raw = json.loads(self.llm.invoke(prompt).content)
                facts = [f for f in raw.get("facts", []) if isinstance(f, dict)]
                unsupported = [c for c in raw.get("unsupported_claims", []) if c]
                if facts:
                    label = grade_from_facts(facts)
                    missing = [f.get("fact") for f in facts if not f.get("present")]
                    reason = f"missing: {missing}" if missing else "all key facts present"
                    return verdict(label, reason, not unsupported, facts=facts, unsupported_claims=unsupported)
            except (json.JSONDecodeError, AttributeError, TypeError):
                pass

        return {"judge_error": True}
