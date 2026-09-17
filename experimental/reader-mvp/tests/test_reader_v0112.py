from app.protocol import Parsed, Record
from app.reader import (
    ACTION_COVERAGE_SYSTEM,
    _salvage_fast,
)


def _parsed(records):
    return Parsed(
        records=records,
        ignored=[],
        quarantined=[
            ("bad-line", "missing-span"),
        ],
        stats={
            "parsed": len(records),
            "ignored": 0,
            "quarantined": 1,
            "no_span": 1,
            "span_needed": 5,
            "span_valid": 4,
            "span_validity": 0.8,
            "junk_ratio": 0.0,
            "content_count": 5,
            "repaired_prefix": 0,
            "disallowed": 0,
            "shape_invalid": 0,
            "end_tail_miss": 0,
        },
        contract_pass=False,
    )


def test_dirty_fast_salvage_drops_interpretive_records():
    parsed = _parsed([
        Record("SUM", "summary"),
        Record("WHO", "Keva | Rian"),
        Record(
            "EV",
            "Keva checked the service door handle",
            [2],
        ),
        Record(
            "DET",
            "canvas bag",
            [2],
        ),
        Record(
            "Q",
            "She looked frightened to me",
            [3],
        ),
        Record(
            "ST",
            "Keva | state | frightened",
            [3],
            epistemic="INF",
        ),
        Record(
            "KN",
            "Rian | Keva appeared frightened",
            [3],
        ),
        Record(
            "REL",
            "Rian -> Keva | trust_gain | concern",
            [3],
        ),
        Record("LOC", "service door"),
        Record("TIME", "noon"),
    ])

    salvaged = _salvage_fast(parsed)
    tags = [r.tag for r in salvaged.records]

    assert "SUM" in tags
    assert "WHO" in tags
    assert "EV" in tags
    assert "DET" in tags
    assert "Q" in tags

    assert "ST" not in tags
    assert "KN" not in tags
    assert "REL" not in tags
    assert "LOC" not in tags
    assert "TIME" not in tags


def test_conflicting_say_attribution_is_not_canonicalized():
    parsed = _parsed([
        Record("SUM", "summary"),
        Record("WHO", "Jonas | Mira"),
        Record(
            "SAY",
            'Jonas | “It says we wait for the mechanic”',
            [3],
        ),
        Record(
            "SAY",
            'Mira | “It says we wait for the mechanic”',
            [3],
        ),
        Record(
            "DET",
            "incident report",
            [2],
        ),
    ])

    salvaged = _salvage_fast(parsed)

    assert not any(
        r.tag == "SAY"
        for r in salvaged.records
    )

    assert any(
        r.tag == "DET"
        and "incident report" in r.payload
        for r in salvaged.records
    )


def test_non_conflicting_say_survives_salvage():
    parsed = _parsed([
        Record("SUM", "summary"),
        Record("WHO", "Jonas | Mira"),
        Record(
            "SAY",
            'Mira | “Call Dena”',
            [4],
        ),
    ])

    salvaged = _salvage_fast(parsed)

    assert any(
        r.tag == "SAY"
        and r.payload.startswith("Mira |")
        for r in salvaged.records
    )


def test_same_words_in_different_spans_are_not_a_conflict():
    parsed = _parsed([
        Record("SUM", "summary"),
        Record("WHO", "A | B"),
        Record(
            "SAY",
            'A | “Wait”',
            [2],
        ),
        Record(
            "SAY",
            'B | “Wait”',
            [4],
        ),
    ])

    salvaged = _salvage_fast(parsed)

    assert sum(
        r.tag == "SAY"
        for r in salvaged.records
    ) == 2


def test_action_coverage_requires_self_contained_events():
    assert (
        "standalone memory record"
        in ACTION_COVERAGE_SYSTEM
    )
    assert (
        "actor, verb, and complete object/target"
        in ACTION_COVERAGE_SYSTEM
    )
    assert (
        "Keva checked the service door handle"
        in ACTION_COVERAGE_SYSTEM
    )
    assert (
        "Mira copied 02:10 into her notebook"
        in ACTION_COVERAGE_SYSTEM
    )
    assert (
        "Mira placed the folded report under the radio"
        in ACTION_COVERAGE_SYSTEM
    )
