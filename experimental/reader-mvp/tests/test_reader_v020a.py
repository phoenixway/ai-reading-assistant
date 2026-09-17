from app.protocol import Parsed, Record
from app.reader import (
    _coverage_ev_is_hedged_proposition,
    _coverage_ev_is_reported_speech,
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


def test_seemed_to_lean_is_not_actual_ev():
    source = (
        "On the rooftop Vero examined the cracked antenna. "
        "It seemed to lean farther east than yesterday, "
        "though no measurement had been taken."
    )

    assert _coverage_ev_is_hedged_proposition(
        "Vero leaned the antenna farther east",
        source,
    )


def test_factual_examined_survives_same_hedged_paragraph():
    source = (
        "On the rooftop Vero examined the cracked antenna. "
        "It seemed to lean farther east than yesterday."
    )

    assert not _coverage_ev_is_hedged_proposition(
        "Vero examined the cracked antenna",
        source,
    )


def test_appeared_at_door_is_not_epistemic_appeared_to():
    source = (
        "Vero appeared at the door and moved the crate."
    )

    assert not _coverage_ev_is_hedged_proposition(
        "Vero moved the crate",
        source,
    )


def test_seemed_tired_does_not_drop_unrelated_move():
    source = (
        "Vero seemed tired. "
        "She moved the crate beside the door."
    )

    assert not _coverage_ev_is_hedged_proposition(
        "She moved the crate beside the door",
        source,
    )


def test_reported_claim_is_communication_not_ev():
    source = (
        "Later Hal claimed the mast had shifted again."
    )

    assert _coverage_ev_is_reported_speech(
        "Hal claimed the mast had shifted again",
        source,
    )


def test_claimed_prize_is_not_treated_as_reported_proposition():
    source = (
        "After the race Hal claimed the prize."
    )

    assert not _coverage_ev_is_reported_speech(
        "Hal claimed the prize",
        source,
    )


def test_sanitizer_drops_false_actuality_but_keeps_real_actions():
    source = (
        "On the rooftop Vero examined the cracked antenna. "
        "It seemed to lean farther east than yesterday, "
        "though no measurement had been taken."
    )

    clean = _sanitize_action_coverage(
        parsed(
            ev(
                "Vero examined the cracked antenna",
                2,
            ),
            ev(
                "Vero leaned the antenna farther east",
                2,
            ),
        ),
        {
            2: source,
        },
        existing=None,
    )

    payloads = [
        record.payload
        for record in clean.records
    ]

    assert (
        "Vero examined the cracked antenna"
        in payloads
    )

    assert (
        "Vero leaned the antenna farther east"
        not in payloads
    )

    assert clean.stats[
        "hedged_ev_dropped"
    ] == 1


def test_sanitizer_drops_reported_claim_ev():
    source = (
        "Later Hal claimed the mast had shifted again. "
        "Vero measured the distance to the chalk line."
    )

    clean = _sanitize_action_coverage(
        parsed(
            ev(
                "Hal claimed the mast had shifted again",
                4,
            ),
            ev(
                "Vero measured the distance to the chalk line",
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

    assert (
        "Hal claimed the mast had shifted again"
        not in payloads
    )

    assert (
        "Vero measured the distance to the chalk line"
        in payloads
    )

    assert clean.stats[
        "reported_speech_ev_dropped"
    ] == 1
