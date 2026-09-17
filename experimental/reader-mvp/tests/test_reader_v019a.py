from app.reader import (
    _select_action_completeness_rows,
)


def test_action_completeness_includes_short_substantive_paragraph():
    rows = [
        {
            "local_no": 1,
            "tok_len": 3,
            "text": "CHAPTER 1",
        },
        {
            "local_no": 2,
            "tok_len": 42,
            "text": "A longer narrative paragraph with an action.",
        },
        {
            "local_no": 3,
            "tok_len": 8,
            "text": "Priya placed the map in her pack.",
        },
    ]

    targets = _select_action_completeness_rows(rows)

    assert [
        row["local_no"]
        for row in targets
    ] == [2, 3]


def test_action_completeness_excludes_empty_rows():
    rows = [
        {
            "local_no": 1,
            "tok_len": 0,
            "text": "",
        },
        {
            "local_no": 2,
            "tok_len": 0,
            "text": "   ",
        },
    ]

    assert _select_action_completeness_rows(rows) == []


def test_action_completeness_excludes_structural_heading_even_if_tokenized():
    rows = [
        {
            "local_no": 1,
            "tok_len": 2,
            "text": "CHAPTER 7",
        },
        {
            "local_no": 2,
            "tok_len": 5,
            "text": "Arden carried the toolbox back.",
        },
    ]

    targets = _select_action_completeness_rows(rows)

    assert [
        row["local_no"]
        for row in targets
    ] == [2]
