import re

# "page 42", "p. 42", "pg 42", "pages 10-12", "pages 10 to 12", "pages 3 and 5"
PAGE_REF = re.compile(
    r"\b(?:pages?|pgs?\.?|p\.)\s*(\d{1,4})"
    r"(?:\s*(?:-|–|to|through)\s*(\d{1,4})|\s*(?:,|and|&)\s*(\d{1,4}))?",
    re.IGNORECASE,
)

MAX_PAGES = 10


def parse_page_refs(question: str) -> list[int]:
    """
    Page numbers a question explicitly asks about, in ascending order.
    Ranges are expanded and capped at MAX_PAGES so "pages 1-500" can't
    pull a whole book into one prompt.
    """
    pages: set[int] = set()

    for start, end, other in PAGE_REF.findall(question):
        first = int(start)

        if end:
            last = int(end)
            low, high = min(first, last), max(first, last)
            pages.update(range(low, min(high, low + MAX_PAGES - 1) + 1))
        else:
            pages.add(first)

        if other:
            pages.add(int(other))

    return sorted(pages)[:MAX_PAGES]
