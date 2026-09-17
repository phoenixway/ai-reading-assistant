from app.protocol import Parsed, Record
from app.reader import (
    ACTION_COVERAGE_SYSTEM,
    _sanitize_action_coverage,
    _select_action_completeness_rows,
)


def _parsed(*records):
    return Parsed(
        records=list(records),
        ignored=[],
        quarantined=[],
        stats={
            "parsed": len(records),
            "ignored": 0,
            "quarantined": 0,
            "no_span": 0,
            "span_needed": len(records),
            "span_valid": len(records),
            "span_validity": 1.0,
            "junk_ratio": 0.0,
            "content_count": len(records),
            "repaired_prefix": 0,
            "disallowed": 0,
            "shape_invalid": 0,
            "end_tail_miss": 0,
        },
        contract_pass=True,
    )


def test_action_completeness_selects_all_substantive_paragraphs():
    rows = [
        {
            "local_no": 2,
            "tok_len": 33,
            "text": (
                "Bruno left for the workshop. "
                "Ada opened the cabinet."
            ),
        },
        {
            "local_no": 3,
            "tok_len": 5,
            "text": "Too short.",
        },
        {
            "local_no": 4,
            "tok_len": 30,
            "text": "***",
        },
    ]

    targets = _select_action_completeness_rows(rows)

    assert [x["local_no"] for x in targets] == [2, 3]


def test_coverage_drops_speech_act_ev():
    parsed = _parsed(
        Record(
            "EV",
            "Levin asked whether Sava brought news",
            [5],
        ),
        Record(
            "EV",
            "Mara opened the envelope",
            [6],
        ),
    )

    clean = _sanitize_action_coverage(
        parsed,
        {
            5: "Levin asked whether the courier brought news.",
            6: "Mara opened the envelope.",
        },
    )

    assert [
        r.payload
        for r in clean.records
    ] == [
        "Mara opened the envelope",
    ]

    assert clean.stats["speech_ev_dropped"] == 1


def test_coverage_trims_promoted_hedged_intent():
    parsed = _parsed(
        Record(
            "EV",
            "Sava paused as he wanted to correct her",
            [5],
        ),
    )

    clean = _sanitize_action_coverage(
        parsed,
        {
            5: (
                "Sava paused as if he wanted to correct her, "
                "then said nothing."
            ),
        },
    )

    assert len(clean.records) == 1
    assert clean.records[0].payload == "Sava paused"
    assert clean.stats["hedge_trimmed"] == 1


def test_explicit_as_clause_without_source_hedge_is_preserved():
    parsed = _parsed(
        Record(
            "EV",
            "Mara waited as the kettle boiled",
            [2],
        ),
    )

    clean = _sanitize_action_coverage(
        parsed,
        {
            2: "Mara waited as the kettle boiled.",
        },
    )

    assert clean.records[0].payload == (
        "Mara waited as the kettle boiled"
    )
    assert clean.stats["hedge_trimmed"] == 0


def test_action_prompt_demands_exhaustive_inventory():
    assert (
        "Work exhaustively from left to right"
        in ACTION_COVERAGE_SYSTEM
    )
    assert (
        "Do not stop after finding one action"
        in ACTION_COVERAGE_SYSTEM
    )
    assert (
        "every explicit material action"
        in ACTION_COVERAGE_SYSTEM
    )
