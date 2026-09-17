from app.protocol import Parsed, Record
from app.reader import (
    ACTION_COVERAGE_SYSTEM,
    _sanitize_action_coverage,
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


def test_coverage_drops_same_action_different_actor():
    existing = _parsed(
        Record(
            "EV",
            "Levin tested the brass handle",
            [2],
        ),
    )

    coverage = _parsed(
        Record(
            "EV",
            "Mara tested the brass handle",
            [2],
        ),
    )

    clean = _sanitize_action_coverage(
        coverage,
        {
            2: (
                "Levin tested the brass handle "
                "while Mara watched."
            ),
        },
        existing=existing,
    )

    assert clean.records == []
    assert (
        clean.stats["role_conflict_dropped"]
        == 1
    )


def test_same_actor_duplicate_is_not_role_conflict():
    existing = _parsed(
        Record(
            "EV",
            "Levin tested the brass handle",
            [2],
        ),
    )

    coverage = _parsed(
        Record(
            "EV",
            "Levin tested the brass handle",
            [2],
        ),
    )

    clean = _sanitize_action_coverage(
        coverage,
        {2: "Levin tested the brass handle."},
        existing=existing,
    )

    assert len(clean.records) == 1
    assert (
        clean.stats["role_conflict_dropped"]
        == 0
    )


def test_different_action_same_span_is_preserved():
    existing = _parsed(
        Record(
            "EV",
            "Levin tested the brass handle",
            [2],
        ),
    )

    coverage = _parsed(
        Record(
            "EV",
            "Mara closed the eastern stair",
            [2],
        ),
    )

    clean = _sanitize_action_coverage(
        coverage,
        {
            2: (
                "Levin tested the brass handle. "
                "Mara closed the eastern stair."
            ),
        },
        existing=existing,
    )

    assert len(clean.records) == 1


def test_prompt_requires_full_action_specificity():
    assert (
        "complete object/target"
        in ACTION_COVERAGE_SYSTEM
    )
    assert (
        "most specific explicit noun phrase"
        in ACTION_COVERAGE_SYSTEM
    )
    assert (
        "destination, container, source, direction"
        in ACTION_COVERAGE_SYSTEM
    )
    assert (
        "read/write/copy actions"
        in ACTION_COVERAGE_SYSTEM
    )
