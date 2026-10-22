"""
Turn a follow-up question into one that stands on its own.

Retrieval only sees the question, so "And a fruit fly?" finds nothing about
neurons. Rewriting it with the conversation ("How many neurons does a fruit
fly have?") lets search and the answer prompt work as for a first question.
"""

REWRITE_PROMPT = """Rewrite the latest question so it can be understood without the conversation.

Rules:
- Replace references such as "it", "that", "they", "the second one" or "and X?" with what they refer to in the conversation.
- Keep the meaning and the language of the question. Do not answer it and do not add facts.
- If the question already makes sense on its own, return it unchanged.
- Reply with the rewritten question only, on one line.

Conversation:
{history}

Latest question: {question}

Standalone question:"""

# Recent turns to show the rewriter, and how much of each answer.
HISTORY_MESSAGES = 6
ANSWER_CHARS = 400


def format_history(history: list[tuple[str, str]]) -> str:
    lines = []
    for role, content in history[-HISTORY_MESSAGES:]:
        text = " ".join(content.split())
        if role == "assistant" and len(text) > ANSWER_CHARS:
            text = text[:ANSWER_CHARS] + "..."
        lines.append(f"{'User' if role == 'user' else 'Assistant'}: {text}")
    return "\n".join(lines)


def rewrite_followup(question: str, history: list[tuple[str, str]], llm) -> str:
    """
    The question rewritten to stand alone, given earlier (role, content)
    messages. Returns the question unchanged when there is no history or
    the model's reply isn't usable.
    """
    if not history:
        return question

    reply = llm.generate(REWRITE_PROMPT.format(history=format_history(history), question=question))
    lines = [line for line in reply.strip().splitlines() if line.strip()]
    rewritten = lines[0].strip() if lines else ""

    if rewritten.lower().startswith("standalone question:"):
        rewritten = rewritten.split(":", 1)[1]
    rewritten = rewritten.strip().strip('"').strip()

    # Guard against the model answering instead of rewriting.
    if not rewritten or len(rewritten) > 3 * len(question) + 200:
        return question

    return rewritten
