from generation.page_refs import MAX_PAGES, parse_page_refs


def test_single_pages_and_abbreviations():
    assert parse_page_refs("What is on page 42?") == [42]
    assert parse_page_refs("summarize p. 7") == [7]
    assert parse_page_refs("Explain pg 12 please") == [12]


def test_ranges_and_lists():
    assert parse_page_refs("pages 10-12") == [10, 11, 12]
    assert parse_page_refs("pages 10 to 12") == [10, 11, 12]
    assert parse_page_refs("compare page 3 and 5") == [3, 5]


def test_ranges_are_capped():
    assert len(parse_page_refs("summarize pages 1-500")) == MAX_PAGES


def test_no_page_reference():
    assert parse_page_refs("How many neurons does a worm have?") == []
    assert parse_page_refs("What does the paper say about 42 nodes?") == []
