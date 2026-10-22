import re

from .intent import Intent


def _patterns(*patterns: str) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in patterns))


# Whole-word patterns: plain substring checks misrouted "authorized" as
# METADATA, "TVs" as COMPARISON and "details" as EXPLANATION.
DOCUMENT = r"(?:book|paper|document|pdf|report|file|deck|slides?|article)"

METADATA = _patterns(
    r"\bwho (?:wrote|authored|published|created)\b",
    r"\bwho (?:is|are) the authors?\b",
    r"\bauthors? of\b",
    r"\bwhat(?: is|'s) the (?:title|name) of (?:this|the)\b",
    rf"\btitle of (?:this|the) {DOCUMENT}\b",
    r"\bwhat is the title\b",
    r"\bpublish(?:ed|er|ing)?\b",
    r"\bedition\b",
    r"\b(?:how many|number of) pages\b",
    r"\bpage count\b",
    r"\bwhen was (?:this|the|it)\b(?: \w+)? (?:written|published|created|released)\b",
)

COMPARISON = _patterns(
    r"\bcompar(?:e|es|ed|ing|ison)\b",
    r"\bcontrast\b",
    r"\bdifferences? between\b",
    r"\bdiffers? from\b",
    r"\bhow (?:does|do|is|are) .+ differ\b",
    r"\bvs\b\.?",
    r"\bversus\b",
    r"\b(?:better|worse|faster|slower|more \w+|less \w+) than\b",
    r"\bwhich (?:is|one is) (?:better|worse|faster|slower|preferable|more|less)\b",
    r"\bsimilarit(?:y|ies) between\b",
)

# A named part of the document. Checked before SUMMARY so "summarize
# section 2" is answered from that section, not a whole-document summary.
CHAPTER = _patterns(
    r"\bchapters?\b",
    r"\bsections?\b",
    r"\bappendix\b",
    r"\bappendices\b",
    r"\bpart (?:\d+|[ivx]+|one|two|three|four|five)\b",
)

SUMMARY = _patterns(
    r"\bsummari[sz](?:e|es|ed|ing)\b",
    r"\bsummary of\b",
    r"\b(?:a|an|brief|short|quick) summary\b",
    r"\bsummary please\b",
    r"\boverview\b",
    r"\bgist\b",
    r"\btl;? ?dr\b",
    r"\bin a nutshell\b",
    r"\bmain (?:points|ideas|topics)\b",
    r"\bkey (?:points|takeaways|ideas)\b",
    r"\btakeaways\b",
    rf"\bwhat(?: is|'s) (?:this|the) (?:\w+ )?{DOCUMENT} about\b",
)

EXPLANATION = _patterns(
    r"\bexplain\w*\b",
    r"\bteach\b",
    r"\bdescribe\b",
    r"\belaborate\b",
    r"\bwalk me through\b",
    r"\bhelp me understand\b",
    r"\bin (?:detail|depth)\b",
    r"\bstep[- ]by[- ]step\b",
    r"\bdeep dive\b",
    r"\bhow (?:does|do) .+ work\b",
)

# Most specific first: "explain the difference between X and Y" is a
# comparison, and "give an overview of part 2" is about that part.
RULES = [
    (Intent.METADATA, METADATA),
    (Intent.COMPARISON, COMPARISON),
    (Intent.CHAPTER, CHAPTER),
    (Intent.SUMMARY, SUMMARY),
    (Intent.EXPLANATION, EXPLANATION),
]


class IntentDetector:
    """
    Rule-based question-type detection, checked with evals/run_routing.py.
    Page references ("page 42") are handled separately by parse_page_refs
    and take precedence over the intent.
    """

    def detect(
        self,
        question: str,
    ) -> Intent:

        text = question.lower().replace("’", "'")

        for intent, pattern in RULES:
            if pattern.search(text):
                return intent

        return Intent.QA
