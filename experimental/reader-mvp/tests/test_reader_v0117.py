from app.reader import (
    DOCUMENT_CONTENT_SYSTEM,
    _select_document_content_rows,
)


def test_document_selector_uses_document_cues():
    rows = [
        {
            "local_no": 2,
            "tok_len": 12,
            "text": (
                "A courier entered the room "
                "and sat down."
            ),
        },
        {
            "local_no": 3,
            "tok_len": 15,
            "text": (
                "Inside was a short note: "
                "Come alone."
            ),
        },
        {
            "local_no": 4,
            "tok_len": 15,
            "text": (
                "Someone had written B17 "
                "on the envelope."
            ),
        },
    ]

    targets = _select_document_content_rows(rows)

    assert [
        x["local_no"]
        for x in targets
    ] == [3, 4]


def test_document_prompt_is_written_content_only():
    assert (
        "explicit written content"
        in DOCUMENT_CONTENT_SYSTEM
    )
    assert (
        "Do not convert written content into SAY"
        in DOCUMENT_CONTENT_SYSTEM
    )
    assert (
        "Do not output actions"
        in DOCUMENT_CONTENT_SYSTEM
    )
    assert (
        "emit nothing"
        in DOCUMENT_CONTENT_SYSTEM
    )
