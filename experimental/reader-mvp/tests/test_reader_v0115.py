from app.protocol import Parsed, Record
from app.reader import (
    SAY_COVERAGE_SYSTEM,
    _replace_say_records,
    _sanitize_say_coverage,
    _select_say_coverage_rows,
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


def test_say_targets_include_short_nonstructural_paragraphs():
    rows = [
        {
            "local_no": 1,
            "tok_len": 2,
            "text": '"Wait."',
        },
        {
            "local_no": 2,
            "tok_len": 1,
            "text": "***",
        },
        {
            "local_no": 3,
            "tok_len": 8,
            "text": "Mira said she would remain.",
        },
    ]

    targets = _select_say_coverage_rows(rows)

    assert [
        x["local_no"]
        for x in targets
    ] == [1, 3]


def test_say_replacement_removes_old_document_as_speech():
    existing = _parsed(
        Record(
            "EV",
            "Mara opened the envelope",
            [6],
        ),
        Record(
            "SAY",
            (
                'Mara | “The eastern stair was '
                'opened yesterday. Come alone.”'
            ),
            [6],
        ),
    )

    authoritative = _parsed(
        Record(
            "SAY",
            'Mara | “Only an invoice”',
            [5],
        ),
    )

    result = _replace_say_records(
        existing,
        authoritative,
    )

    say = [
        r.payload
        for r in result.records
        if r.tag == "SAY"
    ]

    assert say == [
        'Mara | “Only an invoice”',
    ]

    assert any(
        r.tag == "EV"
        and "opened the envelope" in r.payload
        for r in result.records
    )


def test_say_conflicting_speakers_are_dropped():
    parsed = _parsed(
        Record(
            "SAY",
            'Jonas | “Wait for the mechanic”',
            [3],
        ),
        Record(
            "SAY",
            'Mira | “Wait for the mechanic”',
            [3],
        ),
    )

    clean = _sanitize_say_coverage(parsed)

    assert clean.records == []
    assert (
        clean.stats["say_conflict_dropped"]
        == 2
    )


def test_say_prompt_excludes_written_documents():
    assert (
        "spoken aloud"
        in SAY_COVERAGE_SYSTEM
    )
    assert (
        "Written content"
        in SAY_COVERAGE_SYSTEM
    )
    assert (
        "silently read"
        in SAY_COVERAGE_SYSTEM
    )
    assert (
        "spoken question"
        in SAY_COVERAGE_SYSTEM
    )
