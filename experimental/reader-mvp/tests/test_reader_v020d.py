from app.protocol import Parsed, Record
from app.reader import (
    _bridge_action_surface_subject,
    _sanitize_action_coverage,
)


def ev(payload, p):
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


def test_explicit_man_apposition_bridges_he_to_ivo():
    source = (
        "Maeve set a brass compass on a crate beside Ivo, "
        "a man in a dark coat. "
        "He snatched it, wrapped it in a scarf, "
        "and tossed it across the room to Lian."
    )

    value, changed, reason = (
        _bridge_action_surface_subject(
            "He wrapped it in a scarf",
            source,
        )
    )

    assert changed
    assert reason == "explicit-apposition"
    assert value == "Ivo wrapped it in a scarf"


def test_explicit_woman_apposition_bridges_she_to_lian():
    source = (
        "He tossed it across the room to Lian, "
        "a woman waiting by the window. "
        "She caught the compass and slid it into her satchel."
    )

    value, changed, reason = (
        _bridge_action_surface_subject(
            "She slid it into her satchel",
            source,
        )
    )

    assert changed
    assert reason == "explicit-apposition"
    assert value == "Lian slid it into her satchel"


def test_instead_bridges_to_unique_previous_actor():
    source = (
        "Arden refused to pull the lever and did not open the valve. "
        "Instead he closed the inspection cover."
    )

    value, changed, reason = (
        _bridge_action_surface_subject(
            "he closed the inspection cover",
            source,
        )
    )

    assert changed
    assert reason == "contrastive-instead"
    assert value == "Arden closed the inspection cover"


def test_plain_previous_subject_is_not_enough():
    source = (
        "Marek opened the ledger and marked the time. "
        "He stayed beside the gate."
    )

    value, changed, reason = (
        _bridge_action_surface_subject(
            "He stayed beside the gate",
            source,
        )
    )

    assert not changed
    assert reason is None
    assert value == "He stayed beside the gate"


def test_ambiguous_marek_pavel_pronoun_abstains():
    source = (
        "Marek and Pavel stood beside the gate. "
        "He nodded once."
    )

    value, changed, reason = (
        _bridge_action_surface_subject(
            "He nodded once",
            source,
        )
    )

    assert not changed
    assert reason is None
    assert value == "He nodded once"


def test_no_gender_inference_from_name():
    source = (
        "Alex stood beside the gate. "
        "She opened the ledger."
    )

    value, changed, reason = (
        _bridge_action_surface_subject(
            "She opened the ledger",
            source,
        )
    )

    assert not changed
    assert reason is None
    assert value == "She opened the ledger"


def test_sanitizer_bridges_arden_after_surface_repair():
    source = (
        'Supervisor Nessa told him, “Do not vent the chamber.” '
        "Arden refused to pull the lever and did not open the valve. "
        "Instead he closed the inspection cover."
    )

    clean = _sanitize_action_coverage(
        parsed(
            ev(
                "Arden closed the inspection cover",
                3,
            ),
        ),
        {
            3: source,
        },
        existing=None,
    )

    payloads = [
        record.payload
        for record in clean.records
    ]

    assert (
        "Arden closed the inspection cover"
        in payloads
    )

    assert clean.stats[
        "positive_subject_bridged"
    ] == 1


def test_sanitizer_keeps_ambiguous_surface_pronoun():
    source = (
        "Marek and Pavel stood beside the gate. "
        "He nodded once."
    )

    clean = _sanitize_action_coverage(
        parsed(
            ev(
                "Marek nodded once",
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

    assert "He nodded once" in payloads
    assert "Marek nodded once" not in payloads

    assert clean.stats[
        "positive_subject_bridged"
    ] == 0
