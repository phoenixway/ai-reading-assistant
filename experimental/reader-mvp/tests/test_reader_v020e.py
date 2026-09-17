from app.protocol import Parsed, Record
from app.reader import (
    _bridge_action_object_reference,
    _sanitize_action_coverage,
)


def rec(
    tag,
    payload,
    p,
    epistemic="EXPLICIT",
):
    return Record(
        tag=tag,
        payload=payload,
        spans=[p],
        epistemic=epistemic,
        raw="",
    )


def parsed(*records):
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


def test_explicit_possession_resolves_ivo_it():
    source = (
        "Maeve set a brass compass on a crate beside Ivo, "
        "a man in a dark coat. "
        "He snatched it."
    )

    existing = parsed(
        rec(
            "ST",
            "Ivo | possession | holding compass",
            2,
        ),
    )

    value, changed, reason = (
        _bridge_action_object_reference(
            "Ivo snatched it",
            source,
            2,
            existing,
        )
    )

    assert changed
    assert reason == "explicit-possession"
    assert value == "Ivo snatched the compass"


def test_possession_wrong_span_is_not_used():
    source = (
        "Ivo snatched it."
    )

    existing = parsed(
        rec(
            "ST",
            "Ivo | possession | holding compass",
            1,
        ),
    )

    value, changed, reason = (
        _bridge_action_object_reference(
            "Ivo snatched it",
            source,
            2,
            existing,
        )
    )

    assert not changed
    assert reason is None
    assert value == "Ivo snatched it"


def test_inferred_possession_is_not_used():
    source = (
        "Ivo snatched it near the compass."
    )

    existing = parsed(
        rec(
            "ST",
            "Ivo | possession | holding compass",
            2,
            epistemic="INFERRED",
        ),
    )

    value, changed, reason = (
        _bridge_action_object_reference(
            "Ivo snatched it",
            source,
            2,
            existing,
        )
    )

    assert not changed
    assert reason is None


def test_explicit_transfer_resolves_tomas_it():
    source = (
        "Without stopping, Elena crossed the catwalk "
        "and returned the canister to Tomas. "
        "Tomas tucked it beneath his coat."
    )

    value, changed, reason = (
        _bridge_action_object_reference(
            "Tomas tucked it beneath his coat",
            source,
            3,
            existing=None,
        )
    )

    assert changed
    assert reason == "explicit-transfer"
    assert value == (
        "Tomas tucked the canister beneath his coat"
    )


def test_no_positive_evidence_abstains():
    source = (
        "Marek stood beside the table. "
        "Marek moved it aside."
    )

    value, changed, reason = (
        _bridge_action_object_reference(
            "Marek moved it aside",
            source,
            2,
            existing=None,
        )
    )

    assert not changed
    assert reason is None
    assert value == "Marek moved it aside"


def test_conflicting_positive_evidence_abstains():
    source = (
        "Elena returned the canister to Tomas. "
        "Tomas tucked it beneath his coat. "
        "A compass lay nearby."
    )

    existing = parsed(
        rec(
            "ST",
            "Tomas | possession | holding compass",
            3,
        ),
    )

    value, changed, reason = (
        _bridge_action_object_reference(
            "Tomas tucked it beneath his coat",
            source,
            3,
            existing,
        )
    )

    assert not changed
    assert reason is None
    assert value == (
        "Tomas tucked it beneath his coat"
    )


def test_sanitizer_chains_subject_then_object_bridge():
    source = (
        "Maeve set a brass compass on a crate beside Ivo, "
        "a man in a dark coat. "
        "He snatched it, wrapped it in a scarf."
    )

    existing = parsed(
        rec(
            "ST",
            "Ivo | possession | holding compass",
            2,
        ),
    )

    clean = _sanitize_action_coverage(
        parsed(
            rec(
                "EV",
                "He snatched it",
                2,
            ),
        ),
        {
            2: source,
        },
        existing=existing,
    )

    payloads = [
        record.payload
        for record in clean.records
    ]

    assert (
        "Ivo snatched the compass"
        in payloads
    )

    assert clean.stats[
        "positive_subject_bridged"
    ] == 1

    assert clean.stats[
        "positive_object_bridged"
    ] == 1


def test_ambiguous_pronoun_case_does_not_gain_object_resolution():
    source = (
        "Marek and Pavel stood beside the gate. "
        "He moved it."
    )

    clean = _sanitize_action_coverage(
        parsed(
            rec(
                "EV",
                "Marek moved it",
                4,
            ),
        ),
        {
            4: source,
        },
        existing=None,
    )

    payloads = [
        record.payload
        for record in clean.records
    ]

    assert "Marek moved it" not in payloads
    assert "He moved it" in payloads

    assert clean.stats[
        "positive_object_bridged"
    ] == 0
