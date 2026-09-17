from app.protocol import Parsed, Record
from app.reader import (
    _extend_action_coordinated_tail_complement,
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


def test_toss_recovers_to_lian_from_coordinated_source():
    source = (
        "Maeve set a brass compass on a crate beside Ivo, "
        "a man in a dark coat. "
        "He snatched it, wrapped it in a scarf, "
        "and tossed it across the room to Lian, "
        "a woman waiting by the window."
    )

    value, changed = (
        _extend_action_coordinated_tail_complement(
            "Ivo tossed the compass across the room",
            source,
        )
    )

    assert changed
    assert value == (
        "Ivo tossed the compass across the room to Lian"
    )


def test_literal_map_tail_is_safe():
    source = (
        "Priya unfolded a survey map across the truck hood."
    )

    value, changed = (
        _extend_action_coordinated_tail_complement(
            "Priya unfolded a survey map",
            source,
        )
    )

    assert changed
    assert value == (
        "Priya unfolded a survey map across the truck hood"
    )


def test_literal_canister_tail_is_safe():
    source = (
        "Elena retrieved a sealed canister "
        "from the lower shelf."
    )

    value, changed = (
        _extend_action_coordinated_tail_complement(
            "Elena retrieved a sealed canister",
            source,
        )
    )

    assert changed
    assert value == (
        "Elena retrieved a sealed canister "
        "from the lower shelf"
    )


def test_duplicate_source_evidence_abstains():
    source = (
        "Ivo tossed it across the room to Lian. "
        "Later Ivo tossed it across the room to Maeve."
    )

    value, changed = (
        _extend_action_coordinated_tail_complement(
            "Ivo tossed the compass across the room",
            source,
        )
    )

    assert not changed
    assert value == (
        "Ivo tossed the compass across the room"
    )


def test_does_not_cross_sentence_boundary():
    source = (
        "Ivo tossed it. "
        "Across the room to Lian was a scarf."
    )

    value, changed = (
        _extend_action_coordinated_tail_complement(
            "Ivo tossed the compass across the room",
            source,
        )
    )

    assert not changed


def test_pronoun_subject_is_not_handled_by_this_layer():
    source = (
        "He tossed it across the room to Lian."
    )

    value, changed = (
        _extend_action_coordinated_tail_complement(
            "He tossed it across the room",
            source,
        )
    )

    assert not changed
    assert value == (
        "He tossed it across the room"
    )


def test_full_sanitizer_chain_reaches_named_object_and_destination():
    source = (
        "Maeve set a brass compass on a crate beside Ivo, "
        "a man in a dark coat. "
        "He snatched it, wrapped it in a scarf, "
        "and tossed it across the room to Lian, "
        "a woman waiting by the window."
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
                "He tossed it across the room",
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
        "Ivo tossed the compass across the room to Lian"
        in payloads
    )

    assert clean.stats[
        "positive_subject_bridged"
    ] == 1

    assert clean.stats[
        "positive_object_bridged"
    ] == 1

    assert clean.stats[
        "coordinated_tail_extended"
    ] == 1
