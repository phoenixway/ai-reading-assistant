from app.reader import (
    _say_content_bounds,
    _select_say_coverage_rows,
    _source_supports_speaker,
)


def _bounds(source, content):
    bounds = _say_content_bounds(
        source,
        content,
    )

    assert bounds is not None

    return bounds


def test_postquote_murmured_name_is_direct_speech():
    source = (
        '"Great heaven!" murmured Sir John, '
        'as the note fell from his grasp.'
    )

    assert _source_supports_speaker(
        source,
        "Sir John",
        _bounds(
            source,
            "Great heaven!",
        ),
    )


def test_prequote_exclaimed_name_is_direct_speech():
    source = (
        'Irene exclaimed, "Leave me alone!"'
    )

    assert _source_supports_speaker(
        source,
        "Irene",
        _bounds(
            source,
            "Leave me alone!",
        ),
    )


def test_inverted_said_name_still_supported():
    source = (
        '"Wait," said Mira.'
    )

    assert _source_supports_speaker(
        source,
        "Mira",
        _bounds(
            source,
            "Wait,",
        ),
    )


def test_say_selector_drops_plain_narration():
    rows = [
        {
            "local_no": 1,
            "tok_len": 12,
            "text": (
                "The rain crossed the empty yard "
                "and darkened the stones."
            ),
        },
        {
            "local_no": 2,
            "tok_len": 8,
            "text": (
                'Mira said, "Wait here."'
            ),
        },
        {
            "local_no": 3,
            "tok_len": 10,
            "text": (
                "Sol phoned to report "
                "a loose antenna cable."
            ),
        },
    ]

    targets = _select_say_coverage_rows(
        rows
    )

    assert [
        row["local_no"]
        for row in targets
    ] == [
        2,
        3,
    ]


def test_say_selector_keeps_quote_without_attribution():
    rows = [
        {
            "local_no": 7,
            "tok_len": 7,
            "text": (
                '"Relative to my affections, '
                'nothing whatever."'
            ),
        },
    ]

    targets = _select_say_coverage_rows(
        rows
    )

    assert [
        row["local_no"]
        for row in targets
    ] == [
        7,
    ]


def _say_record(
    speaker,
    content,
    local_no,
):
    from app.protocol import Record

    return Record(
        tag="SAY",
        payload=f"{speaker} | {content}",
        spans=[local_no],
        epistemic=None,
        raw="",
    )


def test_say_selector_keeps_strong_cross_paragraph_leadin():
    from app.reader import _select_say_coverage_rows

    rows = [
        {
            "local_no": 12,
            "tok_len": 20,
            "text": (
                "Sir John looked directly at Irene "
                "and then began--"
            ),
        },
        {
            "local_no": 13,
            "tok_len": 15,
            "text": (
                '"Irene, if I may use such familiarity, '
                'I summoned you here."'
            ),
        },
    ]

    targets = _select_say_coverage_rows(
        rows
    )

    assert [
        x["local_no"]
        for x in targets
    ] == [
        12,
        13,
    ]


def test_say_selector_drops_noncommunication_demands_narration():
    from app.reader import _select_say_coverage_rows

    rows = [
        {
            "local_no": 2,
            "tok_len": 12,
            "text": (
                "Ambition demands unison and "
                "patience demands restraint."
            ),
        },
    ]

    assert _select_say_coverage_rows(
        rows
    ) == []


def test_named_leadin_supports_next_quoted_paragraph():
    from app.reader import _say_source_evidence

    sources = {
        12: (
            "Sir John looked fully into her face "
            "and began--"
        ),
        13: (
            '"Irene, if I may use such familiarity, '
            'I have summoned you hither."'
        ),
    }

    record = _say_record(
        "Sir John",
        (
            "Irene, if I may use such familiarity, "
            "I have summoned you hither."
        ),
        13,
    )

    assert _say_source_evidence(
        record,
        sources,
    ) == "spoken"


def test_open_quote_run_supports_consecutive_paragraph():
    from app.reader import _say_source_evidence

    sources = {
        18: (
            'Rachel followed. "This," said Sir John, '
            '"is the room of correction, the room of death.'
        ),
        19: (
            '"First of all, the lady who shared its midst '
            'was a born imbecile.'
        ),
        20: (
            '"It was not known until next day about noon '
            'that anything extraordinary had happened.'
        ),
    }

    record = _say_record(
        "Sir John",
        (
            "It was not known until next day about noon "
            "that anything extraordinary had happened."
        ),
        20,
    )

    assert _say_source_evidence(
        record,
        sources,
    ) == "spoken"


def test_open_quote_run_rejects_wrong_candidate_speaker():
    from app.reader import _say_source_evidence

    sources = {
        18: (
            'Rachel followed. "This," said Sir John, '
            '"is the room of correction, the room of death.'
        ),
        19: (
            '"First of all, the lady who shared its midst '
            'was a born imbecile.'
        ),
    }

    record = _say_record(
        "Irene",
        (
            "First of all, the lady who shared its midst "
            "was a born imbecile."
        ),
        19,
    )

    assert _say_source_evidence(
        record,
        sources,
    ) == "unknown"


def test_open_quote_run_does_not_cross_missing_paragraph():
    from app.reader import _say_source_evidence

    sources = {
        18: (
            'Rachel followed. "This," said Sir John, '
            '"is the room of correction.'
        ),
        20: (
            '"This paragraph must not inherit '
            'a speaker across an unseen gap.'
        ),
    }

    record = _say_record(
        "Sir John",
        (
            "This paragraph must not inherit "
            "a speaker across an unseen gap."
        ),
        20,
    )

    assert _say_source_evidence(
        record,
        sources,
    ) == "unknown"


def test_cross_paragraph_document_leadin_blocks_spoken_run():
    from app.reader import _say_source_evidence

    sources = {
        4: (
            "He found a Christmas card written "
            "with the same hand. The lines were these:--"
        ),
        5: (
            '"Accept my warmest greeting, friendship, love."'
        ),
    }

    record = _say_record(
        "Oscar Otwell",
        "Accept my warmest greeting, friendship, love.",
        5,
    )

    assert _say_source_evidence(
        record,
        sources,
    ) == "document"


def test_same_paragraph_anchor_supports_later_quote_same_speaker():
    from app.reader import _say_source_evidence

    source = (
        '"Great heaven!" murmured Sir John, '
        'as the note fell from his grasp, '
        '"Am I blind to touch or truth?"'
    )

    sources = {
        3: source,
    }

    record = _say_record(
        "Sir John",
        "Am I blind to touch or truth?",
        3,
    )

    assert _say_source_evidence(
        record,
        sources,
    ) == "spoken"


def test_quoted_vocative_is_not_named_prequote_speaker():
    from app.reader import (
        _say_content_bounds,
        _source_supports_speaker,
    )

    source = (
        '"Sir and husband," she said, '
        'with great nervousness, '
        '"you have summoned me hither."'
    )

    content = (
        "you have summoned me hither."
    )

    bounds = _say_content_bounds(
        source,
        content,
    )

    assert bounds is not None

    assert not _source_supports_speaker(
        source,
        "Sir and husband",
        bounds,
    )


def test_quoted_vocative_is_not_indirect_speaker():
    from app.reader import (
        _source_supports_indirect_speech,
    )

    source = (
        '"Sir and husband," she said, '
        'with great nervousness, '
        '"you have summoned me hither."'
    )

    assert not _source_supports_indirect_speech(
        source,
        "Sir and husband",
        "you have summoned me hither",
    )


def test_pronoun_actor_after_name_blocks_name_stealing_quote():
    from app.reader import (
        _say_content_bounds,
        _source_supports_speaker,
    )

    source = (
        'Mira looked at Jonas and she said, '
        '"Wait here."'
    )

    bounds = _say_content_bounds(
        source,
        "Wait here.",
    )

    assert bounds is not None

    assert not _source_supports_speaker(
        source,
        "Mira",
        bounds,
    )


def test_named_actor_with_object_still_supports_quote():
    from app.reader import (
        _say_content_bounds,
        _source_supports_speaker,
    )

    source = (
        'Mira looked at Jonas and replied, '
        '"Wait here."'
    )

    bounds = _say_content_bounds(
        source,
        "Wait here.",
    )

    assert bounds is not None

    assert _source_supports_speaker(
        source,
        "Mira",
        bounds,
    )


def test_false_sir_and_husband_record_is_unknown():
    from app.reader import _say_source_evidence

    sources = {
        25: (
            '"Sir and husband," she said, '
            'with great nervousness at first, '
            '"you have summoned me hither to lash '
            'your rebuke unmercifully upon me."'
        ),
    }

    record = _say_record(
        "Sir and husband",
        (
            "you have summoned me hither to lash "
            "your rebuke unmercifully upon me."
        ),
        25,
    )

    assert _say_source_evidence(
        record,
        sources,
    ) == "unknown"


def test_run_evidence_survives_attribution_firewall():
    from app.reader import _say_source_evidence

    sources = {
        18: (
            'Rachel followed. "This," said Sir John, '
            '"is the room of correction, the room of death.'
        ),
        19: (
            '"First of all, the lady who shared its midst '
            'was a born imbecile.'
        ),
        20: (
            '"It was not known until next day about noon '
            'that anything extraordinary had happened.'
        ),
    }

    record = _say_record(
        "Sir John",
        (
            "It was not known until next day about noon "
            "that anything extraordinary had happened."
        ),
        20,
    )

    assert _say_source_evidence(
        record,
        sources,
    ) == "spoken"


def test_say_batches_keep_contiguous_windows_with_overlap():
    from app.reader import (
        _say_coverage_batches,
    )

    targets = [
        {
            "local_no": n,
            "tok_len": 10,
            "text": f"P{n}",
        }
        for n in [
            9,
            10,
            11,
            12,
            13,
            20,
            21,
        ]
    ]

    batches = _say_coverage_batches(
        targets,
        batch_size=3,
        overlap=1,
    )

    assert [
        [
            x["local_no"]
            for x in batch
        ]
        for batch in batches
    ] == [
        [9, 10, 11],
        [11, 12, 13],
        [20, 21],
    ]


def test_say_batches_cover_every_target():
    from app.reader import (
        _say_coverage_batches,
    )

    targets = [
        {
            "local_no": n,
            "tok_len": 10,
            "text": f"P{n}",
        }
        for n in range(
            1,
            9,
        )
    ]

    batches = _say_coverage_batches(
        targets,
        batch_size=3,
        overlap=1,
    )

    covered = {
        x["local_no"]
        for batch in batches
        for x in batch
    }

    assert covered == set(
        range(
            1,
            9,
        )
    )


def test_say_batches_never_bridge_source_gap():
    from app.reader import (
        _say_coverage_batches,
    )

    targets = [
        {
            "local_no": 3,
            "tok_len": 10,
            "text": "P3",
        },
        {
            "local_no": 4,
            "tok_len": 10,
            "text": "P4",
        },
        {
            "local_no": 9,
            "tok_len": 10,
            "text": "P9",
        },
        {
            "local_no": 10,
            "tok_len": 10,
            "text": "P10",
        },
    ]

    batches = _say_coverage_batches(
        targets,
        batch_size=3,
        overlap=1,
    )

    assert [
        [
            x["local_no"]
            for x in batch
        ]
        for batch in batches
    ] == [
        [3, 4],
        [9, 10],
    ]


def test_say_prompt_demands_single_separator():
    from app.reader import (
        SAY_COVERAGE_SYSTEM,
    )

    assert (
        "EXACTLY ONE `|`"
        in SAY_COVERAGE_SYSTEM
    )

    assert (
        "ONLY the speaker name"
        in SAY_COVERAGE_SYSTEM
    )


def test_say_speaker_surface_rejects_pronoun():
    from app.reader import (
        _say_speaker_surface_valid,
    )

    sources = {
        11: (
            'He requested her '
            '"to have a seat right opposite his."'
        ),
    }

    record = _say_record(
        "he",
        "to have a seat right opposite his.",
        11,
    )

    assert not _say_speaker_surface_valid(
        record,
        sources,
    )


def test_say_speaker_surface_rejects_pronoun_phrase():
    from app.reader import (
        _say_speaker_surface_valid,
    )

    sources = {
        11: (
            'he requested her '
            '"to have a seat."'
        ),
    }

    record = _say_record(
        "he requested",
        "to have a seat.",
        11,
    )

    assert not _say_speaker_surface_valid(
        record,
        sources,
    )


def test_say_speaker_surface_rejects_hallucinated_name():
    from app.reader import (
        _say_speaker_surface_valid,
    )

    sources = {
        14: (
            '"I, as you see, am tinged '
            'with slightly snowy tufts."'
        ),
    }

    record = _say_record(
        "Silas",
        (
            "I, as you see, am tinged "
            "with slightly snowy tufts."
        ),
        14,
    )

    assert not _say_speaker_surface_valid(
        record,
        sources,
    )


def test_say_speaker_surface_accepts_explicit_source_name():
    from app.reader import (
        _say_speaker_surface_valid,
    )

    sources = {
        12: (
            "Sir John looked at Irene "
            "and began--"
        ),
        13: (
            '"Irene, if I may use such familiarity, '
            'I have summoned you hither."'
        ),
    }

    record = _say_record(
        "Sir John",
        "I have summoned you hither.",
        13,
    )

    assert _say_speaker_surface_valid(
        record,
        sources,
    )


def test_indirect_speech_accepts_simple_explicit_actor():
    from app.reader import (
        _source_supports_indirect_speech,
    )

    source = (
        "Selene asked what happened."
    )

    assert _source_supports_indirect_speech(
        source,
        "Selene",
        "what happened",
    )


def test_indirect_speech_accepts_explicit_actor_with_adverb():
    from app.reader import (
        _source_supports_indirect_speech,
    )

    source = (
        "Mira quietly warned Jonas "
        "that the bridge was unsafe."
    )

    assert _source_supports_indirect_speech(
        source,
        "Mira",
        "the bridge was unsafe",
    )


def test_indirect_speech_rejects_recipient_of_orders():
    from app.reader import (
        _source_supports_indirect_speech,
    )

    source = (
        "Rachel, after receiving orders in confidence "
        "from her master, set matters to right, being "
        "strictly charged to admit no visitor."
    )

    assert not _source_supports_indirect_speech(
        source,
        "Rachel",
        (
            "being strictly charged to admit "
            "no visitor"
        ),
    )


def test_indirect_speech_rejects_candidate_before_new_pronoun_actor():
    from app.reader import (
        _source_supports_indirect_speech,
    )

    source = (
        "Nothing could astonish Sir John at this time, "
        "and informing Rachel of his intention he ordered "
        "the key of the room."
    )

    assert not _source_supports_indirect_speech(
        source,
        "Sir John",
        (
            "informing Rachel of his intention "
            "he ordered the key of the room"
        ),
    )


def test_sanitizer_drops_pronoun_speaker_even_if_source_supports_quote():
    from app.protocol import Parsed
    from app.reader import (
        _sanitize_say_coverage,
    )

    sources = {
        25: (
            '"Sir and husband," she said, '
            '"you have summoned me hither."'
        ),
    }

    parsed = Parsed(
        records=[
            _say_record(
                "she",
                "you have summoned me hither.",
                25,
            ),
        ],
        ignored=[],
        quarantined=[],
        stats={
            "parsed": 1,
            "content_count": 1,
        },
        contract_pass=True,
    )

    clean = _sanitize_say_coverage(
        parsed,
        sources,
    )

    assert clean.records == []

    assert (
        clean.stats[
            "say_speaker_surface_dropped"
        ]
        == 1
    )


def test_speaker_surface_without_source_does_not_invent_negative_evidence():
    from app.reader import (
        _say_speaker_surface_valid,
    )

    record = _say_record(
        "Jonas",
        "Wait here.",
        3,
    )

    assert _say_speaker_surface_valid(
        record,
        {},
    )


def test_document_evidence_precedes_missing_speaker_surface():
    from app.reader import (
        _say_source_evidence,
    )

    sources = {
        4: (
            "He found a Christmas card written "
            "with the same hand. "
            "The lines were these:--"
        ),
        5: (
            '"Accept my warmest greeting, '
            'friendship, love."'
        ),
    }

    # The candidate author is deliberately absent from source.
    # We still need DOCUMENT evidence rather than UNKNOWN.
    record = _say_record(
        "Oscar Otwell",
        (
            "Accept my warmest greeting, "
            "friendship, love."
        ),
        5,
    )

    assert _say_source_evidence(
        record,
        sources,
    ) == "document"


def test_indirect_same_subject_action_then_asked():
    from app.reader import (
        _source_supports_indirect_speech,
    )

    source = (
        "Selene entered the operations bay "
        "and asked what happened."
    )

    assert _source_supports_indirect_speech(
        source,
        "Selene",
        "what happened",
    )


def test_indirect_new_pronoun_subject_still_blocked():
    from app.reader import (
        _source_supports_indirect_speech,
    )

    source = (
        "Nothing could astonish Sir John at this time, "
        "and informing Rachel of his intention "
        "he ordered the key of the room."
    )

    assert not _source_supports_indirect_speech(
        source,
        "Sir John",
        "ordered the key of the room",
    )


def test_receiving_orders_noun_is_not_communication_by_recipient():
    from app.reader import (
        _source_supports_indirect_speech,
    )

    source = (
        "Rachel, after receiving orders in confidence "
        "from her master, set matters to right."
    )

    assert not _source_supports_indirect_speech(
        source,
        "Rachel",
        "orders in confidence",
    )


def test_say_missing_provenance_unique_literal_is_completed():
    from app.reader import (
        _repair_say_missing_provenance,
    )

    raw = (
        "SAY: Sir John | "
        "I felt and do feel quite hurt."
    )

    sources = {
        10: (
            '"The sole object of my visit..."'
        ),
        11: (
            '"I felt and do feel quite hurt. '
            'I promised to be at the castle."'
        ),
    }

    repaired, count = (
        _repair_say_missing_provenance(
            raw,
            sources,
        )
    )

    assert repaired == (
        "SAY: Sir John | "
        "I felt and do feel quite hurt. "
        "@P11"
    )

    assert count == 1


def test_say_missing_provenance_accepts_outer_quote_difference():
    from app.reader import (
        _repair_say_missing_provenance,
    )

    raw = (
        'SAY: Sir John | '
        '"Wait here."'
    )

    sources = {
        7: (
            'Sir John replied, '
            '“Wait here.”'
        ),
    }

    repaired, count = (
        _repair_say_missing_provenance(
            raw,
            sources,
        )
    )

    assert repaired.endswith(
        "@P07"
    )

    assert count == 1


def test_say_missing_provenance_ambiguous_content_is_not_completed():
    from app.reader import (
        _repair_say_missing_provenance,
    )

    raw = (
        "SAY: Mira | Wait here."
    )

    sources = {
        2: (
            'Mira said, "Wait here."'
        ),
        5: (
            'Later Mira repeated, "Wait here."'
        ),
    }

    repaired, count = (
        _repair_say_missing_provenance(
            raw,
            sources,
        )
    )

    assert repaired == raw
    assert count == 0


def test_say_missing_provenance_does_not_decide_speaker_identity():
    from app.reader import (
        _repair_say_missing_provenance,
    )

    raw = (
        "SAY: Silas | "
        "I was led to believe this."
    )

    sources = {
        16: (
            '"I was led to believe this."'
        ),
    }

    repaired, count = (
        _repair_say_missing_provenance(
            raw,
            sources,
        )
    )

    # d2 establishes provenance only.
    # Speaker identity remains d1a's responsibility.
    assert repaired == (
        "SAY: Silas | "
        "I was led to believe this. "
        "@P16"
    )

    assert count == 1


def test_say_provenance_completion_does_not_legitimize_hallucinated_speaker():
    from app.protocol import parse_output
    from app.reader import (
        _repair_say_missing_provenance,
        _sanitize_say_coverage,
    )

    raw = (
        "SAY: Silas | "
        "I was led to believe this."
    )

    sources = {
        16: (
            '"I was led to believe this."'
        ),
    }

    repaired, count = (
        _repair_say_missing_provenance(
            raw,
            sources,
        )
    )

    parsed = parse_output(
        repaired,
        {16},
        allowed_tags={
            "SAY",
        },
        required_tags=set(),
        min_content=0,
    )

    clean = _sanitize_say_coverage(
        parsed,
        sources,
    )

    assert count == 1
    assert len(parsed.records) == 1

    # Provenance was successfully established...
    assert parsed.records[0].spans == [
        16
    ]

    # ...but d1a still refuses to turn an invented
    # speaker into canonical memory.
    assert clean.records == []

    assert (
        clean.stats[
            "say_speaker_surface_dropped"
        ]
        == 1
    )


def test_say_missing_provenance_pronoun_speaker_is_not_completed():
    from app.reader import (
        _repair_say_missing_provenance,
    )

    raw = (
        "SAY: he | Come in!"
    )

    sources = {
        10: (
            'Sir John called, "Come in!"'
        ),
    }

    repaired, count = (
        _repair_say_missing_provenance(
            raw,
            sources,
        )
    )

    assert repaired == raw
    assert count == 0


def test_say_existing_provenance_is_never_rewritten():
    from app.reader import (
        _repair_say_missing_provenance,
    )

    raw = (
        "SAY: Sir John | Wait here. @P99"
    )

    sources = {
        3: (
            'Sir John said, "Wait here."'
        ),
    }

    repaired, count = (
        _repair_say_missing_provenance(
            raw,
            sources,
        )
    )

    assert repaired == raw
    assert count == 0


def test_say_shape_invalid_multi_separator_is_not_repaired():
    from app.reader import (
        _repair_say_missing_provenance,
    )

    raw = (
        "SAY: Sir John | Wait | here."
    )

    sources = {
        3: (
            'Sir John said, "Wait | here."'
        ),
    }

    repaired, count = (
        _repair_say_missing_provenance(
            raw,
            sources,
        )
    )

    assert repaired == raw
    assert count == 0


def test_say_provenance_completion_integrates_with_parser():
    from app.protocol import parse_output
    from app.reader import (
        _repair_say_missing_provenance,
    )

    raw = (
        "SAY: Irene | "
        "Your words sting like a wasp."
    )

    sources = {
        12: (
            "Irene considered her answer "
            "and then began:"
        ),
        13: (
            '"Your words sting like a wasp."'
        ),
    }

    repaired, count = (
        _repair_say_missing_provenance(
            raw,
            sources,
        )
    )

    parsed = parse_output(
        repaired,
        {12, 13},
        allowed_tags={
            "SAY",
        },
        required_tags=set(),
        min_content=0,
    )

    assert count == 1
    assert parsed.stats[
        "no_span"
    ] == 0

    assert len(
        parsed.records
    ) == 1

    assert parsed.records[
        0
    ].spans == [
        13
    ]


def test_previous_terminal_subject_can_anchor_pronoun_speech_run():
    from app.reader import (
        _say_source_evidence,
    )

    sources = {
        8: (
            "Sir John chatted gaily until he gained "
            "good ground for delivering his message."
        ),
        9: (
            '"Irene, my beloved one," he began; '
            '"it is now only a score of days.'
        ),
        10: (
            '"The sole object of my visit is '
            'to speak plainly.'
        ),
    }

    record = _say_record(
        "Sir John",
        (
            "The sole object of my visit is "
            "to speak plainly."
        ),
        10,
    )

    assert _say_source_evidence(
        record,
        sources,
    ) == "spoken"


def test_previous_terminal_subject_pronoun_anchor_is_candidate_conditioned():
    from app.reader import (
        _say_run_candidate_previous_subject_pronoun_anchor,
    )

    previous = (
        "Sir John chatted gaily until "
        "he prepared his message."
    )

    current = (
        '"Irene, my beloved one," he began; '
        '"the matter is serious.'
    )

    assert (
        _say_run_candidate_previous_subject_pronoun_anchor(
            previous,
            current,
            "Sir John",
        )
    )

    assert not (
        _say_run_candidate_previous_subject_pronoun_anchor(
            previous,
            current,
            "Irene",
        )
    )


def test_previous_terminal_subject_pronoun_anchor_abstains_with_competing_name():
    from app.reader import (
        _say_run_candidate_previous_subject_pronoun_anchor,
    )

    previous = (
        "Marek met Pavel beside the gate."
    )

    current = (
        '"Come here," he began; '
        '"we need to talk.'
    )

    assert not (
        _say_run_candidate_previous_subject_pronoun_anchor(
            previous,
            current,
            "Marek",
        )
    )

    assert not (
        _say_run_candidate_previous_subject_pronoun_anchor(
            previous,
            current,
            "Pavel",
        )
    )


def test_previous_terminal_coordinated_subject_does_not_anchor_pronoun():
    from app.reader import (
        _say_run_candidate_previous_subject_pronoun_anchor,
    )

    previous = (
        "Marek and Pavel waited beside the gate."
    )

    current = (
        '"Come here," he said.'
    )

    assert not (
        _say_run_candidate_previous_subject_pronoun_anchor(
            previous,
            current,
            "Marek",
        )
    )


def test_previous_subject_anchor_does_not_use_pronoun_gender():
    from app.reader import (
        _say_run_candidate_previous_subject_pronoun_anchor,
    )

    previous = (
        "Alex prepared the message."
    )

    current = (
        '"Come here," she said.'
    )

    # This helper deliberately knows nothing about gender.
    # The candidate is justified structurally as the sole explicit
    # previous actor. No name->gender inference occurs.
    assert (
        _say_run_candidate_previous_subject_pronoun_anchor(
            previous,
            current,
            "Alex",
        )
    )


def test_generation_selector_can_omit_previous_anchor_while_verifier_uses_it():
    from app.reader import (
        _select_say_coverage_rows,
        _say_source_evidence,
    )

    rows = [
        {
            "local_no": 8,
            "tok_len": 14,
            "text": (
                "Sir John chatted gaily until "
                "he prepared his message."
            ),
        },
        {
            "local_no": 9,
            "tok_len": 12,
            "text": (
                '"Irene," he began; '
                '"listen carefully.'
            ),
        },
        {
            "local_no": 10,
            "tok_len": 10,
            "text": (
                '"The matter is serious.'
            ),
        },
    ]

    targets = _select_say_coverage_rows(
        rows
    )

    target_nos = [
        row["local_no"]
        for row in targets
    ]

    # P08 need not be sent to the model.
    assert 8 not in target_nos

    full_source = {
        row["local_no"]:
            row["text"]
        for row in rows
    }

    record = _say_record(
        "Sir John",
        "The matter is serious.",
        10,
    )

    # But P08 remains available to deterministic verification.
    assert _say_source_evidence(
        record,
        full_source,
    ) == "spoken"


def test_pronoun_chain_leadin_supports_next_quoted_paragraph():
    from app.reader import (
        _say_source_evidence,
    )

    sources = {
        12: (
            "At this stage Irene began to consider "
            "the difficult question, knowing well she "
            "had avoided it before. "
            "She pondered whether honesty should prevail. "
            "Raising her eyes, she thus began:"
        ),
        13: (
            '"Your words have astounded me greatly.'
        ),
    }

    record = _say_record(
        "Irene",
        "Your words have astounded me greatly.",
        13,
    )

    assert _say_source_evidence(
        record,
        sources,
    ) == "spoken"


def test_pronoun_chain_leadin_is_candidate_conditioned():
    from app.reader import (
        _say_run_candidate_pronoun_chain_leadin,
    )

    source = (
        "At this stage Irene began to consider "
        "the difficult question, knowing well she "
        "had avoided it before. "
        "She pondered whether honesty should prevail. "
        "Raising her eyes, she thus began:"
    )

    assert (
        _say_run_candidate_pronoun_chain_leadin(
            source,
            "Irene",
        )
    )

    assert not (
        _say_run_candidate_pronoun_chain_leadin(
            source,
            "Sir John",
        )
    )


def test_pronoun_chain_leadin_requires_same_literal_pronoun_bridge():
    from app.reader import (
        _say_run_candidate_pronoun_chain_leadin,
    )

    source = (
        "Irene began to consider the question, "
        "knowing well she had avoided it. "
        "He pondered the answer. "
        "Raising her eyes, she thus began:"
    )

    assert not (
        _say_run_candidate_pronoun_chain_leadin(
            source,
            "Irene",
        )
    )


def test_pronoun_chain_leadin_requires_anchor_pronoun_continuity():
    from app.reader import (
        _say_run_candidate_pronoun_chain_leadin,
    )

    source = (
        "Irene began to consider the question carefully. "
        "She pondered the answer. "
        "Raising her eyes, she thus began:"
    )

    # Candidate sentence does not itself connect Irene to the
    # literal pronoun chain.
    assert not (
        _say_run_candidate_pronoun_chain_leadin(
            source,
            "Irene",
        )
    )


def test_pronoun_chain_leadin_rejects_coordinated_candidate_subject():
    from app.reader import (
        _say_run_candidate_pronoun_chain_leadin,
    )

    source = (
        "Marek and Pavel began to consider the problem, "
        "knowing he had seen it before. "
        "He pondered the answer. "
        "At last he thus began:"
    )

    assert not (
        _say_run_candidate_pronoun_chain_leadin(
            source,
            "Marek",
        )
    )

    assert not (
        _say_run_candidate_pronoun_chain_leadin(
            source,
            "Pavel",
        )
    )


def test_pronoun_chain_leadin_does_not_use_name_gender():
    from app.reader import (
        _say_run_candidate_pronoun_chain_leadin,
    )

    source = (
        "Alex began to consider the question, "
        "knowing well she had avoided it before. "
        "She pondered the answer. "
        "Quietly she then began:"
    )

    # The helper follows the literal token "she".
    # It contains no rule mapping Alex to male/female gender.
    assert (
        _say_run_candidate_pronoun_chain_leadin(
            source,
            "Alex",
        )
    )


def test_pronoun_chain_leadin_allows_leading_discourse_adjunct():
    from app.reader import (
        _say_run_candidate_pronoun_chain_leadin,
    )

    source = (
        "At this stage Irene began to consider "
        "the question, knowing well she had avoided it. "
        "She pondered the answer. "
        "Raising her eyes, she thus began:"
    )

    assert (
        _say_run_candidate_pronoun_chain_leadin(
            source,
            "Irene",
        )
    )


def test_pronoun_chain_leadin_rejects_or_coordinated_candidate():
    from app.reader import (
        _say_run_candidate_pronoun_chain_leadin,
    )

    source = (
        "Marek or Pavel began to consider the problem, "
        "knowing he had seen it before. "
        "He pondered the answer. "
        "At last he thus began:"
    )

    assert not (
        _say_run_candidate_pronoun_chain_leadin(
            source,
            "Pavel",
        )
    )


def test_pronoun_chain_leadin_rejects_with_companion_candidate():
    from app.reader import (
        _say_run_candidate_pronoun_chain_leadin,
    )

    source = (
        "Marek with Pavel began to consider the problem, "
        "knowing he had seen it before. "
        "He pondered the answer. "
        "At last he thus began:"
    )

    assert not (
        _say_run_candidate_pronoun_chain_leadin(
            source,
            "Pavel",
        )
    )


def test_say_semantic_dedupe_collapses_outer_quote_variant():
    from app.protocol import Parsed
    from app.reader import (
        _sanitize_say_coverage,
    )

    source = {
        1: (
            'Mira said, "Wait here."'
        ),
    }

    parsed = Parsed(
        records=[
            _say_record(
                "Mira",
                '"Wait here."',
                1,
            ),
            _say_record(
                "Mira",
                "Wait here.",
                1,
            ),
        ],
        ignored=[],
        quarantined=[],
        stats={},
        contract_pass=True,
    )

    clean = _sanitize_say_coverage(
        parsed,
        source,
    )

    assert len(clean.records) == 1

    assert clean.stats[
        "say_duplicate_dropped"
    ] == 1


def test_say_semantic_dedupe_preserves_different_spans():
    from app.protocol import Parsed
    from app.reader import (
        _sanitize_say_coverage,
    )

    source = {
        1: (
            'Mira said, "Wait here."'
        ),
        2: (
            'Mira said, "Wait here."'
        ),
    }

    parsed = Parsed(
        records=[
            _say_record(
                "Mira",
                "Wait here.",
                1,
            ),
            _say_record(
                "Mira",
                "Wait here.",
                2,
            ),
        ],
        ignored=[],
        quarantined=[],
        stats={},
        contract_pass=True,
    )

    clean = _sanitize_say_coverage(
        parsed,
        source,
    )

    assert len(clean.records) == 2

    assert clean.stats[
        "say_duplicate_dropped"
    ] == 0


def test_say_conflict_resolution_counts_supported_speakers_not_records():
    from app.protocol import Parsed
    from app.reader import (
        _sanitize_say_coverage,
    )

    source = {
        1: (
            'Mira said, "Wait here."'
        ),
    }

    parsed = Parsed(
        records=[
            _say_record(
                "Mira",
                '"Wait here."',
                1,
            ),
            _say_record(
                "Mira",
                "Wait here.",
                1,
            ),
            _say_record(
                "Jonas",
                "Wait here.",
                1,
            ),
        ],
        ignored=[],
        quarantined=[],
        stats={},
        contract_pass=True,
    )

    clean = _sanitize_say_coverage(
        parsed,
        source,
    )

    assert len(clean.records) == 1

    assert clean.records[
        0
    ].payload.startswith(
        "Mira |"
    )

    assert clean.stats[
        "say_conflict_resolved"
    ] == 1

    assert clean.stats[
        "say_conflict_dropped"
    ] == 1

    assert clean.stats[
        "say_duplicate_dropped"
    ] == 1


def test_say_conflict_with_two_supported_speakers_still_abstains():
    from app.protocol import Parsed
    from app.reader import (
        _sanitize_say_coverage,
    )

    # Both candidates have explicit positive attribution in SOURCE.
    # The verifier must not choose between them.
    source = {
        1: (
            'Mira said, "Wait here." '
            'Jonas also said, "Wait here."'
        ),
    }

    parsed = Parsed(
        records=[
            _say_record(
                "Mira",
                "Wait here.",
                1,
            ),
            _say_record(
                "Jonas",
                "Wait here.",
                1,
            ),
        ],
        ignored=[],
        quarantined=[],
        stats={},
        contract_pass=True,
    )

    clean = _sanitize_say_coverage(
        parsed,
        source,
    )

    assert clean.records == []

    assert clean.stats[
        "say_conflict_dropped"
    ] == 2


def test_say_semantic_dedupe_keeps_different_speakers_separate_before_conflict():
    from app.reader import (
        _say_identity,
    )

    mira = _say_record(
        "Mira",
        '"Wait here."',
        1,
    )

    jonas = _say_record(
        "Jonas",
        "Wait here.",
        1,
    )

    mira_identity = _say_identity(
        mira
    )

    jonas_identity = _say_identity(
        jonas
    )

    # Same semantic content/provenance group...
    assert (
        mira_identity[0]
        == jonas_identity[0]
    )

    # ...but distinct proposed speakers.
    assert (
        mira_identity[1]
        != jonas_identity[1]
    )


def test_say_relocation_abstains_when_declared_span_contains_literal_content():
    from app.reader import (
        _relocate_say_provenance,
    )

    sources = {
        1: (
            'Mira said, "Wait here."'
        ),
        2: (
            'The room fell silent. "Wait here."'
        ),
    }

    record = _say_record(
        "Mira",
        "Wait here.",
        2,
    )

    repaired, changed = (
        _relocate_say_provenance(
            record,
            sources,
        )
    )

    # P01 has stronger attribution, but P02 literally contains
    # the proposed content. UNKNOWN speaker evidence at P02 does
    # not authorize rewriting its provenance.
    assert not changed
    assert repaired.spans == [2]


def test_say_relocation_still_repairs_truly_wrong_provenance():
    from app.reader import (
        _relocate_say_provenance,
    )

    sources = {
        1: (
            'Mira said, "Wait here."'
        ),
        2: (
            "The room fell silent."
        ),
    }

    record = _say_record(
        "Mira",
        "Wait here.",
        2,
    )

    repaired, changed = (
        _relocate_say_provenance(
            record,
            sources,
        )
    )

    assert changed
    assert repaired.spans == [1]


def test_same_spoken_words_at_two_source_spans_are_two_observations():
    from app.protocol import Parsed
    from app.reader import (
        _sanitize_say_coverage,
    )

    sources = {
        1: (
            'Mira said, "Wait here."'
        ),
        2: (
            'Mira said, "Wait here."'
        ),
    }

    parsed = Parsed(
        records=[
            _say_record(
                "Mira",
                '"Wait here."',
                1,
            ),
            _say_record(
                "Mira",
                "Wait here.",
                2,
            ),
        ],
        ignored=[],
        quarantined=[],
        stats={},
        contract_pass=True,
    )

    clean = _sanitize_say_coverage(
        parsed,
        sources,
    )

    assert len(clean.records) == 2

    assert {
        tuple(record.spans)
        for record in clean.records
    } == {
        (1,),
        (2,),
    }

    assert clean.stats[
        "say_duplicate_dropped"
    ] == 0


def test_run_speaker_repair_uses_grounded_seed():
    from app.reader import (
        _repair_say_run_speakers,
    )

    sources = {
        1: (
            "Mira looked at the room and began--"
        ),
        2: (
            '"The first thing you must know is this.'
        ),
        3: (
            '"The second thing is even more important.'
        ),
    }

    records = [
        _say_record(
            "Mira",
            (
                "The first thing you must know "
                "is this."
            ),
            2,
        ),
        _say_record(
            "Jonas",
            (
                "The second thing is even more "
                "important."
            ),
            3,
        ),
    ]

    repaired, count = (
        _repair_say_run_speakers(
            records,
            sources,
        )
    )

    assert count == 1

    assert repaired[0].payload.startswith(
        "Mira |"
    )

    assert repaired[1].payload.startswith(
        "Mira |"
    )

    assert repaired[1].spans == [3]


def test_run_speaker_repair_requires_grounded_seed():
    from app.reader import (
        _repair_say_run_speakers,
    )

    sources = {
        1: (
            "Mira looked at the room and began--"
        ),
        2: (
            '"The first thing you must know is this.'
        ),
        3: (
            '"The second thing is even more important.'
        ),
    }

    records = [
        _say_record(
            "Jonas",
            (
                "The second thing is even more "
                "important."
            ),
            3,
        ),
    ]

    repaired, count = (
        _repair_say_run_speakers(
            records,
            sources,
        )
    )

    assert count == 0
    assert repaired[0].payload.startswith(
        "Jonas |"
    )


def test_run_speaker_repair_does_not_rewrite_unanchored_later_quote():
    from app.reader import (
        _repair_say_run_speakers,
    )

    sources = {
        1: (
            'Mira said, "The first conversation ends here."'
        ),
        2: (
            "Hours later the room was silent."
        ),
        3: (
            '"A completely new quotation begins here."'
        ),
    }

    records = [
        _say_record(
            "Mira",
            "The first conversation ends here.",
            1,
        ),
        _say_record(
            "Jonas",
            (
                "A completely new quotation "
                "begins here."
            ),
            3,
        ),
    ]

    repaired, count = (
        _repair_say_run_speakers(
            records,
            sources,
        )
    )

    assert count == 0
    assert repaired[1].payload.startswith(
        "Jonas |"
    )


def test_run_speaker_repair_preserves_document_classification():
    from app.reader import (
        _repair_say_run_speakers,
    )

    sources = {
        1: (
            'Mira said, "The spoken line."'
        ),
        2: (
            "She found a card. "
            "The lines were these:--"
        ),
        3: (
            '"The written line."'
        ),
    }

    records = [
        _say_record(
            "Mira",
            "The spoken line.",
            1,
        ),
        _say_record(
            "Jonas",
            "The written line.",
            3,
        ),
    ]

    repaired, count = (
        _repair_say_run_speakers(
            records,
            sources,
        )
    )

    assert count == 0
    assert repaired[1].payload.startswith(
        "Jonas |"
    )


def test_sanitizer_rewrites_wrong_speaker_inside_grounded_open_run():
    from app.protocol import Parsed
    from app.reader import (
        _sanitize_say_coverage,
    )

    sources = {
        1: (
            "Mira looked at the room and began--"
        ),
        2: (
            '"The first thing you must know is this.'
        ),
        3: (
            '"The second thing is even more important.'
        ),
    }

    parsed = Parsed(
        records=[
            _say_record(
                "Mira",
                (
                    "The first thing you must know "
                    "is this."
                ),
                2,
            ),
            _say_record(
                "Jonas",
                (
                    "The second thing is even more "
                    "important."
                ),
                3,
            ),
        ],
        ignored=[],
        quarantined=[],
        stats={},
        contract_pass=True,
    )

    clean = _sanitize_say_coverage(
        parsed,
        sources,
    )

    assert len(clean.records) == 2

    assert all(
        record.payload.startswith(
            "Mira |"
        )
        for record in clean.records
    )

    assert clean.stats[
        "say_speaker_rewritten"
    ] == 1

    assert clean.stats[
        "say_source_supported"
    ] == 2


def test_run_speaker_repair_leaves_explicit_conflict_to_conflict_resolver():
    from app.reader import (
        _repair_say_run_speakers,
    )

    sources = {
        1: (
            'Mira said, "Wait here."'
        ),
    }

    records = [
        _say_record(
            "Mira",
            "Wait here.",
            1,
        ),
        _say_record(
            "Jonas",
            "Wait here.",
            1,
        ),
    ]

    repaired, count = (
        _repair_say_run_speakers(
            records,
            sources,
        )
    )

    assert count == 0

    assert [
        record.payload.split(
            "|",
            1,
        )[0].strip()
        for record in repaired
    ] == [
        "Mira",
        "Jonas",
    ]


def test_sanitizer_conflict_stats_survive_run_speaker_repair_layer():
    from app.protocol import Parsed
    from app.reader import (
        _sanitize_say_coverage,
    )

    sources = {
        1: (
            'Mira said, "Wait here."'
        ),
    }

    parsed = Parsed(
        records=[
            _say_record(
                "Mira",
                '"Wait here."',
                1,
            ),
            _say_record(
                "Mira",
                "Wait here.",
                1,
            ),
            _say_record(
                "Jonas",
                "Wait here.",
                1,
            ),
        ],
        ignored=[],
        quarantined=[],
        stats={},
        contract_pass=True,
    )

    clean = _sanitize_say_coverage(
        parsed,
        sources,
    )

    assert len(clean.records) == 1

    assert clean.records[
        0
    ].payload.startswith(
        "Mira |"
    )

    assert clean.stats[
        "say_speaker_rewritten"
    ] == 0

    assert clean.stats[
        "say_conflict_resolved"
    ] == 1

    assert clean.stats[
        "say_conflict_dropped"
    ] == 1

    assert clean.stats[
        "say_duplicate_dropped"
    ] == 1


def test_say_mixed_direct_surface_detects_post_attribution_bridge():
    from app.reader import (
        _say_crosses_direct_quote_surface,
    )

    sources = {
        1: (
            '"This," said Mira, '
            '"is the room of correction.'
        ),
    }

    record = _say_record(
        "Mira",
        (
            'This," said Mira, '
            '"is the room of correction.'
        ),
        1,
    )

    assert _say_crosses_direct_quote_surface(
        record,
        sources,
    )


def test_say_mixed_direct_surface_detects_mid_quote_narration():
    from app.reader import (
        _say_crosses_direct_quote_surface,
    )

    sources = {
        1: (
            '"He drew from that drawer" '
            'here Mira pointed to the wardrobe, '
            '"a weapon of curious design.'
        ),
    }

    record = _say_record(
        "Mira",
        (
            'He drew from that drawer" '
            'here Mira pointed to the wardrobe, '
            '"a weapon of curious design.'
        ),
        1,
    )

    assert _say_crosses_direct_quote_surface(
        record,
        sources,
    )


def test_say_clean_closed_quote_does_not_cross_surface():
    from app.reader import (
        _say_crosses_direct_quote_surface,
    )

    sources = {
        1: (
            '"This," said Mira, '
            '"is the room of correction.'
        ),
    }

    record = _say_record(
        "Mira",
        "This,",
        1,
    )

    assert not _say_crosses_direct_quote_surface(
        record,
        sources,
    )


def test_say_clean_second_open_quote_does_not_cross_surface():
    from app.reader import (
        _say_crosses_direct_quote_surface,
    )

    sources = {
        1: (
            '"This," said Mira, '
            '"is the room of correction.'
        ),
    }

    record = _say_record(
        "Mira",
        "is the room of correction.",
        1,
    )

    assert not _say_crosses_direct_quote_surface(
        record,
        sources,
    )


def test_say_old_style_open_paragraph_does_not_cross_surface():
    from app.reader import (
        _say_crosses_direct_quote_surface,
    )

    sources = {
        1: (
            '"The speech continues for the '
            'whole paragraph without a closing quote.'
        ),
    }

    record = _say_record(
        "Mira",
        (
            "The speech continues for the "
            "whole paragraph without a closing quote."
        ),
        1,
    )

    assert not _say_crosses_direct_quote_surface(
        record,
        sources,
    )


def test_sanitizer_salvages_mixed_direct_speech_surface():
    from app.protocol import Parsed
    from app.reader import (
        _sanitize_say_coverage,
    )

    sources = {
        1: (
            '"This," said Mira, '
            '"is the room of correction.'
        ),
    }

    parsed = Parsed(
        records=[
            _say_record(
                "Mira",
                (
                    'This," said Mira, '
                    '"is the room of correction.'
                ),
                1,
            ),
        ],
        ignored=[],
        quarantined=[],
        stats={},
        contract_pass=True,
    )

    clean = _sanitize_say_coverage(
        parsed,
        sources,
    )

    assert [
        record.payload
        for record in clean.records
    ] == [
        'Mira | This,',
        'Mira | is the room of correction.',
    ]

    assert [
        record.spans
        for record in clean.records
    ] == [
        [1],
        [1],
    ]

    assert (
        clean.stats[
            'say_mixed_surface_salvaged'
        ]
        == 1
    )

    assert (
        clean.stats[
            'say_mixed_surface_salvaged_fragments'
        ]
        == 2
    )

    # j1 replaced the original mixed observation with clean
    # direct-speech SOURCE fragments before h1.
    assert (
        clean.stats[
            'say_mixed_surface_dropped'
        ]
        == 0
    )

    # Both projected fragments survive ordinary spoken-source
    # verification.
    assert (
        clean.stats[
            'say_direct_supported'
        ]
        == 2
    )

    assert (
        clean.stats[
            'say_indirect_supported'
        ]
        == 0
    )

    assert (
        clean.stats[
            'say_source_supported'
        ]
        == 2
    )

    assert (
        clean.stats[
            'say_unsupported_dropped'
        ]
        == 0
    )


def test_run_speaker_repair_does_not_rewrite_mixed_surface():
    from app.reader import (
        _repair_say_run_speakers,
    )

    sources = {
        1: (
            'Mira began: "The first line.'
        ),
        2: (
            '"He drew from that drawer" '
            'here Mira pointed aside, '
            '"and continued the story.'
        ),
    }

    records = [
        _say_record(
            "Mira",
            "The first line.",
            1,
        ),
        _say_record(
            "Jonas",
            (
                'He drew from that drawer" '
                'here Mira pointed aside, '
                '"and continued the story.'
            ),
            2,
        ),
    ]

    repaired, count = (
        _repair_say_run_speakers(
            records,
            sources,
        )
    )

    assert count == 0

    assert repaired[
        1
    ].payload.startswith(
        "Jonas |"
    )


def test_say_containment_dedupe_keeps_wider_source_observation():
    from app.reader import (
        _dedupe_say_contained_records,
    )

    sources = {
        1: (
            '"I was led to believe this. '
            'Was I falsely informed?"'
        ),
    }

    records = [
        _say_record(
            "Mira",
            (
                "I was led to believe this. "
                "Was I falsely informed?"
            ),
            1,
        ),
        _say_record(
            "Mira",
            "Was I falsely informed?",
            1,
        ),
    ]

    clean, dropped = (
        _dedupe_say_contained_records(
            records,
            sources,
        )
    )

    assert dropped == 1
    assert len(clean) == 1

    assert (
        "I was led to believe this."
        in clean[0].payload
    )


def test_say_containment_dedupe_preserves_disjoint_same_span():
    from app.reader import (
        _dedupe_say_contained_records,
    )

    sources = {
        1: (
            '"First sentence. '
            'Second sentence."'
        ),
    }

    records = [
        _say_record(
            "Mira",
            "First sentence.",
            1,
        ),
        _say_record(
            "Mira",
            "Second sentence.",
            1,
        ),
    ]

    clean, dropped = (
        _dedupe_say_contained_records(
            records,
            sources,
        )
    )

    assert dropped == 0
    assert len(clean) == 2


def test_say_containment_dedupe_preserves_same_text_different_spans():
    from app.reader import (
        _dedupe_say_contained_records,
    )

    sources = {
        1: (
            '"Wait here."'
        ),
        2: (
            '"Wait here."'
        ),
    }

    records = [
        _say_record(
            "Mira",
            "Wait here.",
            1,
        ),
        _say_record(
            "Mira",
            "Wait here.",
            2,
        ),
    ]

    clean, dropped = (
        _dedupe_say_contained_records(
            records,
            sources,
        )
    )

    assert dropped == 0
    assert len(clean) == 2


def test_say_containment_dedupe_preserves_different_speakers():
    from app.reader import (
        _dedupe_say_contained_records,
    )

    sources = {
        1: (
            '"The whole sentence contains '
            'this phrase."'
        ),
    }

    records = [
        _say_record(
            "Mira",
            (
                "The whole sentence contains "
                "this phrase."
            ),
            1,
        ),
        _say_record(
            "Jonas",
            "this phrase",
            1,
        ),
    ]

    clean, dropped = (
        _dedupe_say_contained_records(
            records,
            sources,
        )
    )

    assert dropped == 0
    assert len(clean) == 2


def test_sanitizer_drops_contained_say_fragment_after_verification():
    from app.protocol import Parsed
    from app.reader import (
        _sanitize_say_coverage,
    )

    sources = {
        1: (
            'Mira said, '
            '"I was led to believe this. '
            'Was I falsely informed?"'
        ),
    }

    parsed = Parsed(
        records=[
            _say_record(
                "Mira",
                (
                    "I was led to believe this. "
                    "Was I falsely informed?"
                ),
                1,
            ),
            _say_record(
                "Mira",
                "Was I falsely informed?",
                1,
            ),
        ],
        ignored=[],
        quarantined=[],
        stats={},
        contract_pass=True,
    )

    clean = _sanitize_say_coverage(
        parsed,
        sources,
    )

    assert len(clean.records) == 1

    assert clean.stats[
        "say_containment_duplicate_dropped"
    ] == 1


def test_say_containment_dedupe_handles_nested_quoted_words():
    from app.reader import (
        _dedupe_say_contained_records,
    )

    sources = {
        1: (
            '"Speak, and remember when she replied, '
            '\'You honoured me too highly\'. '
            'Are you doing likewise?"'
        ),
    }

    records = [
        _say_record(
            "Mira",
            (
                "Speak, and remember when she replied, "
                "'You honoured me too highly'. "
                "Are you doing likewise?"
            ),
            1,
        ),
        _say_record(
            "Mira",
            "You honoured me too highly",
            1,
        ),
    ]

    clean, dropped = (
        _dedupe_say_contained_records(
            records,
            sources,
        )
    )

    assert dropped == 1
    assert len(clean) == 1


def test_previous_pronoun_chain_anchor_positive():
    from app.reader import (
        _say_run_candidate_previous_pronoun_chain_anchor,
    )

    previous = (
        "Let it be understood that Mira was forced "
        "into an arrangement she disliked. "
        "She was almost compelled, through Rowan's "
        "interference, to accept it. "
        "All she could now do was answer him."
    )

    current = (
        '"Sir and husband," she said, '
        '"you have summoned me here.'
    )

    assert (
        _say_run_candidate_previous_pronoun_chain_anchor(
            previous,
            current,
            "Mira",
        )
    )


def test_previous_pronoun_chain_anchor_is_candidate_conditioned():
    from app.reader import (
        _say_run_candidate_previous_pronoun_chain_anchor,
    )

    previous = (
        "Let it be understood that Mira was forced "
        "into an arrangement she disliked. "
        "She was almost compelled, through Rowan's "
        "interference, to accept it. "
        "All she could now do was answer him."
    )

    current = (
        '"Sir and husband," she said, '
        '"you have summoned me here.'
    )

    assert not (
        _say_run_candidate_previous_pronoun_chain_anchor(
            previous,
            current,
            "Rowan",
        )
    )


def test_previous_pronoun_chain_anchor_requires_same_bridge_pronoun():
    from app.reader import (
        _say_run_candidate_previous_pronoun_chain_anchor,
    )

    previous = (
        "Let it be understood that Mira was forced "
        "into an arrangement she disliked. "
        "He was almost compelled to accept it. "
        "All she could now do was answer him."
    )

    current = (
        '"Sir and husband," she said, '
        '"you have summoned me here.'
    )

    assert not (
        _say_run_candidate_previous_pronoun_chain_anchor(
            previous,
            current,
            "Mira",
        )
    )


def test_previous_pronoun_chain_anchor_requires_same_terminal_pronoun():
    from app.reader import (
        _say_run_candidate_previous_pronoun_chain_anchor,
    )

    previous = (
        "Let it be understood that Mira was forced "
        "into an arrangement she disliked. "
        "She was almost compelled to accept it. "
        "All he could now do was answer."
    )

    current = (
        '"Sir and husband," she said, '
        '"you have summoned me here.'
    )

    assert not (
        _say_run_candidate_previous_pronoun_chain_anchor(
            previous,
            current,
            "Mira",
        )
    )


def test_previous_pronoun_chain_anchor_requires_current_same_pronoun():
    from app.reader import (
        _say_run_candidate_previous_pronoun_chain_anchor,
    )

    previous = (
        "Let it be understood that Mira was forced "
        "into an arrangement she disliked. "
        "She was almost compelled to accept it. "
        "All she could now do was answer."
    )

    current = (
        '"Sir and husband," he said, '
        '"you have summoned me here.'
    )

    assert not (
        _say_run_candidate_previous_pronoun_chain_anchor(
            previous,
            current,
            "Mira",
        )
    )


def test_previous_pronoun_chain_anchor_rejects_coordinated_candidate():
    from app.reader import (
        _say_run_candidate_previous_pronoun_chain_anchor,
    )

    previous = (
        "Marek and Pavel were forced to stay. "
        "He was almost compelled to agree. "
        "All he could now do was answer."
    )

    current = (
        '"Very well," he said, '
        '"I shall remain.'
    )

    assert not (
        _say_run_candidate_previous_pronoun_chain_anchor(
            previous,
            current,
            "Pavel",
        )
    )


def test_previous_pronoun_chain_anchor_does_not_use_name_gender():
    from app.reader import (
        _say_run_candidate_previous_pronoun_chain_anchor,
    )

    previous = (
        "It was understood that Alex was forced "
        "to remain. "
        "She was almost compelled to agree. "
        "All she could now do was answer."
    )

    current = (
        '"Very well," she said, '
        '"I shall remain.'
    )

    # Positive by literal structural chain alone.
    # No Alex -> she gender knowledge exists or is required.
    assert (
        _say_run_candidate_previous_pronoun_chain_anchor(
            previous,
            current,
            "Alex",
        )
    )


def test_previous_pronoun_chain_anchor_allows_embedded_other_name():
    from app.reader import (
        _say_run_candidate_previous_pronoun_chain_anchor,
    )

    previous = (
        "It was understood that Mira was forced "
        "to remain. "
        "She was almost compelled, through Rowan's "
        "interference, to agree. "
        "All she could now do was answer."
    )

    current = (
        '"Very well," she said, '
        '"I shall remain.'
    )

    assert (
        _say_run_candidate_previous_pronoun_chain_anchor(
            previous,
            current,
            "Mira",
        )
    )


def test_previous_pronoun_chain_anchor_opens_speech_run():
    from app.protocol import Record
    from app.reader import (
        _source_supports_speaker_run,
    )

    sources = {
        1: (
            "It was understood that Mira was forced "
            "to remain. "
            "She was almost compelled to agree. "
            "All she could now do was answer."
        ),
        2: (
            '"Very well," she said, '
            '"I shall explain everything.'
        ),
        3: (
            '"The second part follows.'
        ),
        4: (
            '"And this concludes the answer."'
        ),
    }

    for local_no, content in [
        (
            2,
            "I shall explain everything.",
        ),
        (
            3,
            "The second part follows.",
        ),
        (
            4,
            "And this concludes the answer.",
        ),
    ]:
        record = Record(
            tag="SAY",
            payload=(
                f"Mira | {content}"
            ),
            spans=[local_no],
            epistemic=None,
            raw="",
        )

        assert _source_supports_speaker_run(
            record,
            sources,
            "Mira",
            content,
        )


def test_say_run_subject_candidates_keeps_full_multiword_surface():
    from app.reader import (
        _say_run_subject_candidates,
    )

    sentence = (
        "Let it be thoroughly understood that "
        "Lady Dunfern was forced into a union."
    )

    assert _say_run_subject_candidates(
        sentence
    ) == [
        "Lady Dunfern",
    ]


def test_say_run_subject_candidates_single_name():
    from app.reader import (
        _say_run_subject_candidates,
    )

    sentence = (
        "At this stage Irene began to reconsider."
    )

    assert _say_run_subject_candidates(
        sentence
    ) == [
        "Irene",
    ]


def test_say_run_subject_candidates_does_not_emit_name_fragments():
    from app.reader import (
        _say_run_subject_candidates,
    )

    sentence = (
        "Lady Dunfern was forced to remain."
    )

    candidates = _say_run_subject_candidates(
        sentence
    )

    assert candidates == [
        "Lady Dunfern",
    ]

    assert "Lady" not in candidates
    assert "Dunfern" not in candidates


def test_source_run_seed_discovers_unique_i1_candidate():
    from app.reader import (
        _say_source_run_seed_speakers,
    )

    sources = {
        1: (
            "Let it be understood that Mira was forced "
            "to remain. "
            "She was almost compelled, through Rowan's "
            "interference, to agree. "
            "All she could now do was answer."
        ),
        2: (
            '"Very well," she said, '
            '"I shall explain everything.'
        ),
        3: (
            '"The explanation continues.'
        ),
    }

    assert _say_source_run_seed_speakers(
        sources
    ) == {
        "Mira",
    }


def test_source_run_seed_uses_full_title_name():
    from app.reader import (
        _say_source_run_seed_speakers,
    )

    sources = {
        1: (
            "Let it be understood that Lady Dunfern was forced "
            "to remain. "
            "She was almost compelled, through Lady Dilworth's "
            "interference, to agree. "
            "All she could now do was answer."
        ),
        2: (
            '"Sir and husband," she said, '
            '"you have summoned me here.'
        ),
    }

    seeds = _say_source_run_seed_speakers(
        sources
    )

    assert seeds == {
        "Lady Dunfern",
    }

    assert "Lady" not in seeds
    assert "Dunfern" not in seeds
    assert "Lady Dilworth" not in seeds


def test_source_run_seed_abstains_when_two_candidates_validate():
    from app.reader import (
        _say_source_run_seed_speakers,
    )

    sources = {
        1: (
            "Mira was required to stay while Rowan was "
            "required to remain. "
            "She was almost compelled to agree. "
            "All she could now do was answer."
        ),
        2: (
            '"Very well," she said, '
            '"I shall remain.'
        ),
    }

    # Both Mira and Rowan satisfy the deliberately weak surface
    # relation to the same pronoun chain. SOURCE therefore must
    # abstain rather than choose.
    assert _say_source_run_seed_speakers(
        sources
    ) == set()


def test_run_speaker_repair_can_use_source_seed_without_model_seed():
    from app.reader import (
        _repair_say_run_speakers,
    )

    sources = {
        1: (
            "Let it be understood that Mira was forced "
            "to remain. "
            "She was almost compelled to agree. "
            "All she could now do was answer."
        ),
        2: (
            '"Very well," she said, '
            '"I shall explain everything.'
        ),
        3: (
            '"The explanation continues.'
        ),
    }

    # Model never proposes Mira at all.
    records = [
        _say_record(
            "Rowan",
            "I shall explain everything.",
            2,
        ),
        _say_record(
            "Jonas",
            "The explanation continues.",
            3,
        ),
    ]

    repaired, rewritten = (
        _repair_say_run_speakers(
            records,
            sources,
        )
    )

    assert rewritten == 2

    assert all(
        record.payload.startswith(
            "Mira |"
        )
        for record in repaired
    )


def test_source_seed_repair_still_abstains_on_multi_speaker_same_observation():
    from app.reader import (
        _repair_say_run_speakers,
    )

    sources = {
        1: (
            "Let it be understood that Mira was forced "
            "to remain. "
            "She was almost compelled to agree. "
            "All she could now do was answer."
        ),
        2: (
            '"Very well," she said, '
            '"I shall explain everything.'
        ),
    }

    records = [
        _say_record(
            "Rowan",
            "I shall explain everything.",
            2,
        ),
        _say_record(
            "Jonas",
            "I shall explain everything.",
            2,
        ),
    ]

    repaired, rewritten = (
        _repair_say_run_speakers(
            records,
            sources,
        )
    )

    # g1 conflict ownership remains intact.
    assert rewritten == 0

    assert {
        record.payload.split(
            "|",
            1,
        )[0].strip()
        for record in repaired
    } == {
        "Rowan",
        "Jonas",
    }



# ------------------------------------------------------------------
# SAY v0.1.20h-j1
# Mixed spoken/narrator/spoken SOURCE projection.
# ------------------------------------------------------------------

def test_say_j1_projects_mixed_candidate_onto_exact_spoken_surfaces():
    from app.reader import (
        Record,
        _salvage_say_mixed_quote_surface,
        _say_crosses_direct_quote_surface,
    )

    source_by_local_no = {
        1: (
            '"Sir and husband," she said, with great nervousness '
            'at first, "you have summoned me hither to answer."'
        ),
    }

    record = Record(
        tag='SAY',
        payload=(
            'she | '
            'Sir and husband," she said, with great nervousness '
            'at first, "you have summoned me hither to answer.'
        ),
        spans=[1],
    )

    assert _say_crosses_direct_quote_surface(
        record,
        source_by_local_no,
    )

    salvaged = _salvage_say_mixed_quote_surface(
        record,
        source_by_local_no,
    )

    assert salvaged is not None

    assert [
        candidate.payload
        for candidate in salvaged
    ] == [
        'she | Sir and husband,',
        'she | you have summoned me hither to answer.',
    ]

    assert all(
        candidate.spans == [1]
        for candidate in salvaged
    )

    assert all(
        not _say_crosses_direct_quote_surface(
            candidate,
            source_by_local_no,
        )
        for candidate in salvaged
    )


def test_say_j1_leaves_clean_open_quote_candidate_untouched():
    from app.reader import (
        Record,
        _salvage_say_mixed_quote_surface,
    )

    source_by_local_no = {
        1: (
            '"The speech continues all the way '
            'to paragraph end'
        ),
    }

    record = Record(
        tag='SAY',
        payload=(
            'Mira | '
            'The speech continues all the way '
            'to paragraph end'
        ),
        spans=[1],
    )

    assert (
        _salvage_say_mixed_quote_surface(
            record,
            source_by_local_no,
        )
        is None
    )


def test_say_j1_abstains_fragment_when_ordinary_locator_would_move_it():
    from app.reader import (
        Record,
        _salvage_say_mixed_quote_surface,
    )

    # The second "No." is a distinct quoted source surface, but
    # _say_content_bounds() would resolve it to the first literal
    # occurrence. j1 must therefore abstain from emitting that
    # second fragment rather than manufacture wrong geometry.
    source_by_local_no = {
        1: (
            '"No." Mira paused. "No."'
        ),
    }

    record = Record(
        tag='SAY',
        payload=(
            'Mira | '
            'No." Mira paused. "No.'
        ),
        spans=[1],
    )

    salvaged = _salvage_say_mixed_quote_surface(
        record,
        source_by_local_no,
    )

    assert salvaged is not None

    assert [
        candidate.payload
        for candidate in salvaged
    ] == [
        'Mira | No.',
    ]

