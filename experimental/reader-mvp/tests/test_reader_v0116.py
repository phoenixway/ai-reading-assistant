from app.protocol import Parsed, Record
from app.reader import _sanitize_say_coverage


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


def test_document_note_text_is_dropped():
    parsed = _parsed(
        Record(
            "SAY",
            (
                "Mara | The eastern stair was "
                "opened yesterday. Come alone."
            ),
            [6],
        ),
    )

    clean = _sanitize_say_coverage(
        parsed,
        {
            6: (
                "She opened the envelope. Inside was "
                "a railway receipt and a short note: "
                "The eastern stair was opened yesterday. "
                "Come alone. She read it twice."
            ),
        },
    )

    assert clean.records == []
    assert (
        clean.stats["say_document_dropped"]
        == 1
    )


def test_report_text_is_dropped_without_speech():
    parsed = _parsed(
        Record(
            "SAY",
            (
                "Mira | Generator 4 failed at "
                "02:10. Do not restart."
            ),
            [2],
        ),
    )

    clean = _sanitize_say_coverage(
        parsed,
        {
            2: (
                "The top sheet was an incident report. "
                "In red ink someone had written: "
                "Generator 4 failed at 02:10. "
                "Do not restart."
            ),
        },
    )

    assert clean.records == []


def test_conflict_resolves_from_post_attribution():
    parsed = _parsed(
        Record(
            "SAY",
            "Mira | It says we wait for the mechanic",
            [3],
        ),
        Record(
            "SAY",
            "Jonas | It says we wait for the mechanic",
            [3],
        ),
    )

    source = (
        "Mira read the warning silently, copied "
        "02:10 into her notebook, and folded the "
        "report in half. Jonas asked what it said. "
        "“It says we wait for the mechanic,” "
        "Mira replied."
    )

    clean = _sanitize_say_coverage(
        parsed,
        {3: source},
    )

    assert [
        r.payload
        for r in clean.records
    ] == [
        "Mira | It says we wait for the mechanic"
    ]

    assert (
        clean.stats["say_conflict_resolved"]
        == 1
    )

    assert (
        clean.stats["say_conflict_dropped"]
        == 1
    )


def test_explicit_speech_beats_document_context():
    parsed = _parsed(
        Record(
            "SAY",
            "Mira | Wait for the mechanic",
            [3],
        ),
    )

    clean = _sanitize_say_coverage(
        parsed,
        {
            3: (
                "Mira folded the report and said, "
                "“Wait for the mechanic.”"
            ),
        },
    )

    assert len(clean.records) == 1
    assert (
        clean.stats["say_document_dropped"]
        == 0
    )


def test_unknown_nonconflicting_say_is_preserved():
    parsed = _parsed(
        Record(
            "SAY",
            "Ada | she would stay inside",
            [2],
        ),
    )

    clean = _sanitize_say_coverage(
        parsed,
        {
            2: (
                "Ada said she would stay inside "
                "and check the household ledger."
            ),
        },
    )

    assert len(clean.records) == 1


def test_unresolved_conflict_is_dropped():
    parsed = _parsed(
        Record(
            "SAY",
            "Ada | Stay here",
            [2],
        ),
        Record(
            "SAY",
            "Bruno | Stay here",
            [2],
        ),
    )

    clean = _sanitize_say_coverage(
        parsed,
        {2: '"Stay here."'},
    )

    assert clean.records == []

    assert (
        clean.stats["say_conflict_dropped"]
        == 2
    )


def test_document_noun_alone_does_not_make_dialogue_document_text():
    parsed = _parsed(
        Record(
            "SAY",
            "Mira | Wait",
            [3],
        ),
    )

    clean = _sanitize_say_coverage(
        parsed,
        {
            3: (
                "Mira checked the report, closed it, "
                "and said, “Wait.”"
            ),
        },
    )

    assert len(clean.records) == 1
    assert (
        clean.stats["say_source_supported"]
        == 1
    )
    assert (
        clean.stats["say_document_dropped"]
        == 0
    )
