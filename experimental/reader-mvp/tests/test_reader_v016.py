from app.protocol import parse_output
from app.reader import (
    ACTION_COVERAGE_SYSTEM,
    _is_structural_paragraph,
    _select_action_coverage_rows,
)


def test_structural_paragraph_detection():
    assert _is_structural_paragraph("CHAPTER 1")
    assert _is_structural_paragraph("***")
    assert _is_structural_paragraph("-----")
    assert not _is_structural_paragraph(
        "Mara opened the envelope."
    )


def test_action_coverage_selects_long_paragraphs_without_ev():
    parsed = parse_output(
        """SUM: summary
WHO: Mara
EV: Levin tests the handle @P02
END: present=Mara | loc= | situation=waiting @P06
""",
        {1, 2, 3, 4, 5, 6},
        required_end_span=6,
    )

    rows = [
        {
            "local_no": 1,
            "tok_len": 3,
            "text": "CHAPTER 1",
        },
        {
            "local_no": 2,
            "tok_len": 47,
            "text": "Levin tests the handle.",
        },
        {
            "local_no": 3,
            "tok_len": 44,
            "text": "Sava arrives and hands over an envelope.",
        },
        {
            "local_no": 4,
            "tok_len": 1,
            "text": "***",
        },
        {
            "local_no": 5,
            "tok_len": 47,
            "text": "Dialogue and a pause occur here.",
        },
        {
            "local_no": 6,
            "tok_len": 48,
            "text": "Mara opens the envelope and burns a note.",
        },
    ]

    targets = _select_action_coverage_rows(
        rows,
        parsed,
    )

    assert [
        x["local_no"]
        for x in targets
    ] == [3, 5, 6]


def test_action_coverage_prompt_is_ev_only():
    prompt = ACTION_COVERAGE_SYSTEM.lower()

    assert "extract only explicit narratively useful actions" in prompt
    assert "reply only with ev lines" in prompt
    assert "omit the hedged intent or interpretation" in prompt
    assert "written document content is not an action" in prompt
