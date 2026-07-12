from retrieval.filters import build_chroma_filter, merge_filters


def test_build_chroma_filter_none():
    assert build_chroma_filter(None) is None


def test_build_chroma_filter_tuple_to_list():
    filt = {"tags": ("a", "b"), "filename": "file.pdf"}
    out = build_chroma_filter(filt)
    assert isinstance(out["tags"], list)
    assert out["filename"] == "file.pdf"


def test_merge_filters_overrides():
    a = {"a": 1, "b": 2}
    b = {"b": 3, "c": 4}
    merged = merge_filters(a, b)
    assert merged["a"] == 1
    assert merged["b"] == 3
    assert merged["c"] == 4
