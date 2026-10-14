import re

from langchain_core.documents import Document

CITATION = re.compile(r"Source\s*(\d+)", re.IGNORECASE)


def cited_documents(answer: str, contexts: list[Document]) -> list[Document]:
    """
    The context documents an answer cites as "Source N", in order of first
    mention. Numbers outside 1..len(contexts) are ignored.
    """
    cited = []
    seen = set()

    for match in CITATION.finditer(answer):
        index = int(match.group(1))

        if 1 <= index <= len(contexts) and index not in seen:
            seen.add(index)
            cited.append(contexts[index - 1])

    return cited
