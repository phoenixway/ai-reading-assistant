from app.protocol import Parsed, Record
from app.reader import (
    _extend_action_literal_complement,
    _sanitize_action_coverage,
)


def ev(payload, p=2):
    return Record(
        tag="EV",
        payload=payload,
        spans=[p],
        epistemic="EXPLICIT",
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


def test_rafi_quote_boundary_extends_into_catalog():
    payload = 'Rafi wrote “antenna cable”'

    source = (
        'Sol phoned from the roof to report a loose antenna cable. '
        'Rafi wrote “antenna cable” in the catalog, '
        'closed the book, and remained in the archive office.'
    )

    value, changed = (
        _extend_action_literal_complement(
            payload,
            source,
        )
    )

    assert changed

    assert value == (
        'Rafi wrote “antenna cable” in the catalog'
    )


def test_arden_destination_is_restored():
    payload = (
        "Arden carried the toolbox back"
    )

    source = (
        "Arden carried the toolbox back "
        "to the maintenance bench and sat beside it."
    )

    value, changed = (
        _extend_action_literal_complement(
            payload,
            source,
        )
    )

    assert changed

    assert value == (
        "Arden carried the toolbox back "
        "to the maintenance bench"
    )


def test_maeve_placement_complement_is_restored():
    payload = (
        "Maeve set a brass compass"
    )

    source = (
        "Maeve set a brass compass on a crate beside Ivo, "
        "a man in a dark coat."
    )

    value, changed = (
        _extend_action_literal_complement(
            payload,
            source,
        )
    )

    assert changed

    assert value == (
        "Maeve set a brass compass on a crate beside Ivo"
    )


def test_complete_action_is_unchanged():
    payload = (
        "Ada returned the ledger to the cabinet"
    )

    source = (
        "Ada returned the ledger to the cabinet, "
        "and stayed in the kitchen."
    )

    value, changed = (
        _extend_action_literal_complement(
            payload,
            source,
        )
    )

    assert not changed
    assert value == payload


def test_coordinated_pronoun_chain_does_not_fake_literal_match():
    payload = (
        "He tossed it across the room"
    )

    source = (
        "He snatched it, wrapped it in a scarf, "
        "and tossed it across the room to Lian."
    )

    value, changed = (
        _extend_action_literal_complement(
            payload,
            source,
        )
    )

    assert not changed
    assert value == payload


def test_ambiguous_duplicate_literal_occurrence_abstains():
    payload = (
        "Mira placed the report"
    )

    source = (
        "Mira placed the report under the radio. "
        "Later Mira placed the report on the desk."
    )

    value, changed = (
        _extend_action_literal_complement(
            payload,
            source,
        )
    )

    assert not changed
    assert value == payload


def test_sanitizer_applies_literal_complement():
    source = (
        'Rafi wrote “antenna cable” in the catalog, '
        'closed the book.'
    )

    clean = _sanitize_action_coverage(
        parsed(
            ev(
                'Rafi wrote “antenna cable”',
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

    assert payloads == [
        'Rafi wrote “antenna cable” in the catalog'
    ]

    assert clean.stats[
        "literal_complement_extended"
    ] == 1
