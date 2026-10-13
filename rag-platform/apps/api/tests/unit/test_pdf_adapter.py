from ingestion.pdf_adapter import normalize_text


def test_non_breaking_spaces_and_soft_hyphens_are_normalised():
    assert normalize_text("human\xadlike\xa0brains") == "human-like brains"


def test_image_placeholders_are_removed():
    assert normalize_text("## QUESTION 1\n\n<!-- image -->\n\n<!-- image -->") == "## QUESTION 1"


def test_table_padding_collapsed_but_code_indentation_kept():
    text = "| Prologue      | 3   |\n    int x = 1;"

    assert normalize_text(text) == "| Prologue | 3 |\n    int x = 1;"
