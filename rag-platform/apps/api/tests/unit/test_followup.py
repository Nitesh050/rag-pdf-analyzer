from generation.followup import format_history, rewrite_followup

HISTORY = [
    ("user", "How many neurons does a nematode worm have?"),
    ("assistant", "A nematode worm has 302 neurons (Source 1, page 42)."),
]


class FakeLLM:
    def __init__(self, reply):
        self.reply = reply
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.reply


def test_first_question_is_not_rewritten_and_costs_no_llm_call():
    llm = FakeLLM("should not be used")

    assert rewrite_followup("And a fruit fly?", [], llm) == "And a fruit fly?"
    assert llm.prompts == []


def test_follow_up_is_rewritten_with_the_conversation():
    llm = FakeLLM("How many neurons does a fruit fly have?")

    assert rewrite_followup("And a fruit fly?", HISTORY, llm) == "How many neurons does a fruit fly have?"
    assert "nematode worm has 302 neurons" in llm.prompts[0]


def test_reply_is_cleaned_up():
    llm = FakeLLM('Standalone question: "How many neurons does a fruit fly have?"\n\nExtra text')

    assert rewrite_followup("And a fruit fly?", HISTORY, llm) == "How many neurons does a fruit fly have?"


def test_falls_back_when_the_model_answers_instead():
    llm = FakeLLM("A fruit fly has about 100,000 neurons, which is " + "far more than a worm. " * 30)

    assert rewrite_followup("And a fruit fly?", HISTORY, llm) == "And a fruit fly?"


def test_falls_back_on_empty_reply():
    assert rewrite_followup("And a fruit fly?", HISTORY, FakeLLM("   ")) == "And a fruit fly?"


def test_history_is_trimmed():
    long_history = [("user", f"question {i}") for i in range(10)] + [("assistant", "x" * 1000)]

    text = format_history(long_history)

    assert "question 4" not in text and "question 9" in text
    assert len(text.splitlines()[-1]) < 450
