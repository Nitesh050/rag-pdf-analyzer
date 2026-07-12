from .intent import Intent


class IntentDetector:

    def detect(
        self,
        question: str,
    ) -> Intent:

        question = question.lower()

        summary_keywords = [
            "summary",
            "summarize",
            "summarise",
            "overview",
            "gist",
        ]

        explanation_keywords = [
            "explain",
            "teach",
            "describe",
            "detail",
            "in detail",
            "deeply",
        ]

        comparison_keywords = [
            "compare",
            "difference",
            "vs",
            "versus",
        ]

        chapter_keywords = [
            "chapter",
            "page",
            "section",
        ]

        metadata_keywords = [
            "author",
            "title",
            "publisher",
            "edition",
        ]

        if any(word in question for word in summary_keywords):
            return Intent.SUMMARY

        if any(word in question for word in explanation_keywords):
            return Intent.EXPLANATION

        if any(word in question for word in comparison_keywords):
            return Intent.COMPARISON

        if any(word in question for word in chapter_keywords):
            return Intent.CHAPTER

        if any(word in question for word in metadata_keywords):
            return Intent.METADATA

        return Intent.QA