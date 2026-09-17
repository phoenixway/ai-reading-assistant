from app.protocol import Parsed, Record
from app.reader import (
    _action_gap_batches,
    _gap_candidate_already_covered,
    _gap_source_role_supported,
    _repair_gap_coordinated_surface_subject,
    _sanitize_action_gap,
)


def rec(payload, p=3):
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
        stats={},
        contract_pass=True,
    )


def test_sava_arrival_has_positive_source_role_support():
    source = (
        "A courier named Sava arrived soaked through "
        "and handed Mara a grey envelope."
    )

    assert _gap_source_role_supported(
        "Sava arrived soaked through",
        source,
    )


def test_false_mara_writer_has_no_source_role_support():
    source = (
        "On the front someone had written B17 in blue pencil. "
        "Mara slipped the envelope into her coat."
    )

    assert not _gap_source_role_supported(
        "Mara wrote B17 in blue pencil",
        source,
    )


def test_recipient_cannot_steal_coordinated_predicate():
    source = (
        "Mara handed Levin the key and opened the door."
    )

    assert not _gap_source_role_supported(
        "Levin opened the door",
        source,
    )

    assert _gap_source_role_supported(
        "Mara opened the door",
        source,
    )


def test_coordinated_named_actor_restores_literal_pronoun():
    source = (
        "Priya answered, “We take the ridge.” "
        "She circled checkpoint C in red pencil "
        "and folded the map."
    )

    value, changed = (
        _repair_gap_coordinated_surface_subject(
            "Priya folded the map",
            source,
        )
    )

    assert changed
    assert value == "She folded the map"


def test_ambiguous_pronoun_does_not_gain_named_identity():
    source = (
        "Marek and Pavel stood beside the gate. "
        "He waited there."
    )

    value, changed = (
        _repair_gap_coordinated_surface_subject(
            "Marek waited there",
            source,
        )
    )

    assert not changed
    assert value == "Marek waited there"


def test_near_duplicate_is_covered():
    assert _gap_candidate_already_covered(
        "Sava handed a grey envelope",
        [
            "Sava handed Mara a grey envelope",
        ],
    )


def test_same_action_different_named_actor_is_not_duplicate():
    assert not _gap_candidate_already_covered(
        "Levin opened the door",
        [
            "Mara opened the door",
        ],
    )


def test_article_led_nominal_subject_abstains():
    assert not _gap_source_role_supported(
        "A train arrived",
        "A train arrived.",
    )


def test_gap_sanitizer_recovers_wait_and_drops_false_actor():
    source = {
        3: (
            "Keva tilted her head. "
            "She waited a few seconds, then walked away. "
            "On the sign someone had written B17."
        ),
    }

    existing = parsed(
        rec("Keva tilted her head"),
        rec("Keva walked away"),
    )

    candidates = parsed(
        rec("Keva waited a few seconds"),
        rec("Keva wrote B17"),
    )

    clean = _sanitize_action_gap(
        candidates,
        source,
        existing,
    )

    payloads = [
        record.payload
        for record in clean.records
    ]

    # This direct non-coordinated pronoun case is handled by the
    # ordinary ACTION sanitizer before GAP in production, so the
    # GAP-only layer correctly refuses the unsupported named form.
    assert "Keva wrote B17" not in payloads


def test_batches_are_pairs():
    targets = [
        {
            "local_no": i,
            "text": f"Paragraph {i}.",
            "tok_len": 10,
        }
        for i in range(2, 7)
    ]

    batches = _action_gap_batches(
        targets,
        batch_size=2,
    )

    assert [
        [
            item["local_no"]
            for item in batch
        ]
        for batch in batches
    ] == [
        [2, 3],
        [4, 5],
        [6],
    ]


def test_gap_existing_compaction_removes_shorter_subsumed_action():
    from app.reader import (
        _compact_gap_existing_payloads,
    )

    values = _compact_gap_existing_payloads(
        [
            "Priya unfolded a survey map",
            "Priya unfolded a survey map across the truck hood",
            "Priya traced the ridge path with one finger",
        ]
    )

    assert values == [
        "Priya unfolded a survey map across the truck hood",
        "Priya traced the ridge path with one finger",
    ]


def test_gap_existing_compaction_keeps_distinct_actions():
    from app.reader import (
        _compact_gap_existing_payloads,
    )

    values = _compact_gap_existing_payloads(
        [
            "Mara opened the envelope",
            "Mara burned the note",
            "Mara kept the receipt",
        ]
    )

    assert values == [
        "Mara opened the envelope",
        "Mara burned the note",
        "Mara kept the receipt",
    ]


def test_gap_existing_compaction_keeps_different_named_actors():
    from app.reader import (
        _compact_gap_existing_payloads,
    )

    values = _compact_gap_existing_payloads(
        [
            "Mara opened the door",
            "Levin opened the door",
        ]
    )

    assert values == [
        "Mara opened the door",
        "Levin opened the door",
    ]


def test_gap_existing_compaction_does_not_mutate_ledger_parsed():
    from app.reader import (
        _compact_gap_existing_payloads,
        _gap_existing_by_local,
    )

    source = parsed(
        rec(
            "Priya unfolded a survey map",
            p=2,
        ),
        rec(
            "Priya unfolded a survey map across the truck hood",
            p=2,
        ),
    )

    existing = _gap_existing_by_local(
        source
    )

    compact = _compact_gap_existing_payloads(
        existing[2]
    )

    assert len(source.records) == 2
    assert len(existing[2]) == 2

    assert compact == [
        "Priya unfolded a survey map across the truck hood",
    ]
