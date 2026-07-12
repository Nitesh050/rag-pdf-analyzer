from enum import Enum


class Intent(str, Enum):
    QA = "qa"

    SUMMARY = "summary"

    EXPLANATION = "explanation"

    COMPARISON = "comparison"

    CHAPTER = "chapter"

    METADATA = "metadata"

    UNKNOWN = "unknown"