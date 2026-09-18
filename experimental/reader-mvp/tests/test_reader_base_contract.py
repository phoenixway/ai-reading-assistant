from app.protocol import Parsed, Record
from app.reader import (
    _base_source_is_quote_only,
    _sanitize_base_extraction_contract,
)


def ev(payload, p=1):
    return Record(
        tag="EV",
        payload=payload,
        spans=[p],
        epistemic="EXPLICIT",
        raw=f"EV: {payload} @P{p:02}",
    )


def parsed(*records):
    return Parsed(
        records=list(records),
        ignored=[],
        quarantined=[],
        stats={
            "parsed": len(records),
            "content_count": len(records),
            "quarantined": 0,
        },
        contract_pass=True,
    )


def sanitize(payload, source):
    return _sanitize_base_extraction_contract(
        parsed(ev(payload)),
        {1: source},
    )


def test_quote_only_open_paragraph_detected():
    source = (
        '"I may here say I was mistress of my movements; '
        'nor was I ever thwarted in any way from acting.'
    )

    assert _base_source_is_quote_only(
        source
    )


def test_closed_quote_only_paragraph_detected():
    assert _base_source_is_quote_only(
        '"Speak, I implore you."'
    )


def test_mixed_quote_and_narration_is_not_quote_only():
    source = (
        '"Go now," said Sir John. '
        'He crossed the room.'
    )

    assert not _base_source_is_quote_only(
        source
    )


def test_plain_narration_is_not_quote_only():
    assert not _base_source_is_quote_only(
        "Sir John crossed the room."
    )


def test_paraphrased_orders_ev_dropped():
    source = (
        '"I may here say I was mistress, in a measure, '
        'of my movements; nor was I ever thwarted in any '
        'way from acting, and I, more than once, have '
        'given orders which were completely prohibited '
        'from being executed.'
    )

    result = sanitize(
        "I have given orders",
        source,
    )

    assert result.records == []
    assert (
        result.stats[
            "base_contract_quote_only_ev_dropped"
        ]
        == 1
    )


def test_paraphrased_thwarted_ev_dropped():
    source = (
        '"Nor was I ever thwarted in any way from acting '
        'throughout her entire household.'
    )

    result = sanitize(
        (
            "I was never thwarted "
            "in any way from acting"
        ),
        source,
    )

    assert result.records == []


def test_semantic_confrontation_from_quote_only_source_dropped():
    source = (
        '"Speak! Irene! Wife! Woman! '
        'Do not sit in silence!"'
    )

    result = sanitize(
        (
            "Sir John confronts Irene "
            "about her changed behavior"
        ),
        source,
    )

    assert result.records == []


def test_unsupported_action_from_quote_only_source_dropped():
    source = (
        '"You speak of your snowy tufts appearing '
        'where once there dwelt locks of glossy jet."'
    )

    result = sanitize(
        (
            "Irene Iddesleigh requests Sir John "
            "to have a seat opposite her"
        ),
        source,
    )

    assert result.records == []


def test_narrative_action_survives():
    result = sanitize(
        "Sir John crossed the room",
        "Sir John crossed the room.",
    )

    assert [
        r.payload
        for r in result.records
    ] == [
        "Sir John crossed the room",
    ]


def test_mixed_paragraph_narrative_action_survives():
    source = (
        '"Go now," said Sir John. '
        'Sir John crossed the room.'
    )

    result = sanitize(
        "Sir John crossed the room",
        source,
    )

    assert [
        r.payload
        for r in result.records
    ] == [
        "Sir John crossed the room",
    ]


def test_non_ev_from_quote_only_source_survives():
    record = Record(
        tag="SAY",
        payload="Sir John | Go now",
        spans=[1],
        epistemic="EXPLICIT",
        raw="",
    )

    result = _sanitize_base_extraction_contract(
        parsed(record),
        {1: '"Go now."'},
    )

    assert result.records == [record]
