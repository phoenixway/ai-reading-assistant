from app.protocol import Parsed, Record
from app.reader import (
    _repair_action_surface_subject,
    _sanitize_action_coverage,
)


def _ev(
    payload,
    *,
    p=2,
):
    return Record(
        tag="EV",
        payload=payload,
        spans=[p],
        epistemic="EXPLICIT",
        raw="",
    )


def _parsed(*records):
    return Parsed(
        records=list(records),
        ignored=[],
        quarantined=[],
        stats={
            "parsed": len(records),
            "content_count": len(records),
        },
        contract_pass=True,
    )


def test_ambiguous_named_subject_restores_source_pronoun():
    payload, changed = (
        _repair_action_surface_subject(
            "Marek nodded once",
            (
                "Marek and Pavel stood beside the gate. "
                "He nodded once. Neither man spoke."
            ),
        )
    )

    assert changed is True
    assert payload == "He nodded once"


def test_named_source_subject_is_preserved():
    payload, changed = (
        _repair_action_surface_subject(
            "Pavel entered the ticket booth",
            (
                "A bell rang. Pavel entered the "
                "ticket booth while Marek remained "
                "beside the gate."
            ),
        )
    )

    assert changed is False
    assert (
        payload
        == "Pavel entered the ticket booth"
    )


def test_named_exact_match_wins_over_other_pronoun_match():
    payload, changed = (
        _repair_action_surface_subject(
            "Marek nodded once",
            (
                "Marek nodded once. "
                "Later he nodded once."
            ),
        )
    )

    assert changed is False
    assert payload == "Marek nodded once"


def test_multiple_pronoun_matches_abstain():
    payload, changed = (
        _repair_action_surface_subject(
            "Marek nodded once",
            (
                "He nodded once. "
                "The bell rang. "
                "He nodded once."
            ),
        )
    )

    assert changed is False
    assert payload == "Marek nodded once"


def test_existing_pronoun_is_untouched():
    payload, changed = (
        _repair_action_surface_subject(
            "He snatched the compass",
            (
                "He snatched the compass."
            ),
        )
    )

    assert changed is False
    assert payload == "He snatched the compass"


def test_action_sanitizer_repairs_subject_only():
    record = _ev(
        "Dax set the crate beside the furnace",
        p=3,
    )

    clean = _sanitize_action_coverage(
        _parsed(record),
        {
            3: (
                'Dax started, “I thought the east room—” '
                'but Lora interrupted, “Not tonight.” '
                "He set the crate beside the furnace."
            ),
        },
        existing=None,
    )

    assert len(clean.records) == 1

    repaired = clean.records[0]

    assert (
        repaired.payload
        == "He set the crate beside the furnace"
    )
    assert repaired.spans == [3]
    assert repaired.epistemic == "EXPLICIT"

    assert clean.stats[
        "surface_subject_repaired"
    ] == 1


def test_explicit_tomas_subject_is_not_changed():
    record = _ev(
        "Tomas tucked the canister beneath his coat",
        p=3,
    )

    clean = _sanitize_action_coverage(
        _parsed(record),
        {
            3: (
                "Elena returned the canister to Tomas. "
                "Tomas tucked the canister beneath his coat."
            ),
        },
        existing=None,
    )

    assert clean.records[0].payload == (
        "Tomas tucked the canister beneath his coat"
    )

    assert clean.stats[
        "surface_subject_repaired"
    ] == 0
