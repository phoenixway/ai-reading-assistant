from app.protocol import Parsed, Record
from app.reader import (
    ACTION_COVERAGE_SYSTEM,
    _sanitize_action_coverage,
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
        stats={},
        contract_pass=True,
    )


def sanitize(payload, source, p=1):
    return _sanitize_action_coverage(
        parsed(ev(payload, p)),
        {p: source},
        existing=None,
    )


def test_g1_drops_pure_prompt_leak_on_structural_source():
    clean = sanitize(
        "Keva checked the service door handle",
        "CHAPTER VII.",
    )

    assert clean.records == []
    assert clean.stats["source_role_unsupported_dropped"] == 1


def test_g1_drops_pure_prompt_leak_on_unrelated_narrative():
    clean = sanitize(
        "Mira copied 02:10 into her notebook",
        (
            "There seemed to be no rival now of buried lineage "
            "to mar their desire."
        ),
    )

    assert clean.records == []
    assert clean.stats["source_role_unsupported_dropped"] == 1


def test_g1_drops_predicate_hijack_from_real_source_action():
    clean = sanitize(
        "Keva knelt beside the bed",
        (
            "The frantic father moved in the direction of the bed "
            "on which his beloved lay, and knelt beside it."
        ),
    )

    assert clean.records == []
    assert clean.stats["source_role_unsupported_dropped"] == 1


def test_g1_drops_speech_surface_hijack():
    clean = sanitize(
        "Keva spoke of snowy tufts appearing",
        (
            '"You speak of your snowy tufts appearing where once '
            'there dwelt locks of glossy jet."'
        ),
    )

    assert clean.records == []
    assert clean.stats["source_role_unsupported_dropped"] == 1


def test_g1_keeps_direct_named_actor_action():
    clean = sanitize(
        "Pavel entered the ticket booth",
        (
            "A bell rang. Pavel entered the ticket booth while "
            "Marek remained beside the gate."
        ),
    )

    assert [
        r.payload
        for r in clean.records
    ] == [
        "Pavel entered the ticket booth",
    ]

    assert clean.stats["source_role_unsupported_dropped"] == 0


def test_g1_keeps_coordinated_named_actor_action():
    clean = sanitize(
        "Mara opened the door",
        "Mara handed Levin the key and opened the door.",
    )

    assert [
        r.payload
        for r in clean.records
    ] == [
        "Mara opened the door",
    ]


def test_g1_preserves_literal_pronoun_repair():
    clean = sanitize(
        "Marek nodded once",
        (
            "Marek and Pavel stood beside the gate. "
            "He nodded once."
        ),
    )

    assert [
        r.payload
        for r in clean.records
    ] == [
        "He nodded once",
    ]

    assert clean.stats["surface_subject_repaired"] == 1
    assert clean.stats["source_role_unsupported_dropped"] == 0


def test_g1_keeps_positive_identity_bridge_after_surface_proof():
    clean = sanitize(
        "Arden closed the inspection cover",
        (
            'Supervisor Nessa told him, "Do not vent the chamber." '
            "Arden refused to pull the lever and did not open the valve. "
            "Instead he closed the inspection cover."
        ),
    )

    assert [
        r.payload
        for r in clean.records
    ] == [
        "Arden closed the inspection cover",
    ]

    assert clean.stats["positive_subject_bridged"] == 1
    assert clean.stats["source_role_unsupported_dropped"] == 0


def test_g1_does_not_claim_article_led_subject_support():
    clean = sanitize(
        "A courier arrived",
        "A courier arrived soaked through.",
    )

    # Article-led nominal subjects are outside the narrow G1a
    # source-role parser. Preserve existing behavior rather than
    # guessing or introducing a false negative.
    assert [
        r.payload
        for r in clean.records
    ] == [
        "A courier arrived",
    ]


def test_action_prompt_contains_no_reusable_fixture_world_facts():
    forbidden = (
        "Keva checked the service door handle",
        "Mira copied 02:10 into her notebook",
        "Mira placed the folded report under the radio",
    )

    for value in forbidden:
        assert value not in ACTION_COVERAGE_SYSTEM
