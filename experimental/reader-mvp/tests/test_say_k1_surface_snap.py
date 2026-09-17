import app.reader as r


def record(speaker, content, p=1):
    return r.Record(
        tag="SAY",
        payload=f"{speaker} | {content}",
        spans=[p],
        epistemic=None,
        raw="test",
    )


def payloads(records):
    return [x.payload for x in records]


def test_k1_typographic_apostrophe_snaps_to_exact_source():
    source = (
        '"Speak at once, for pity\'s sake! '
        'and do not hide from me the answer of truth '
        'and honest knowledge? Oh, merciful heavens!"'
    )

    candidate = record(
        "Lady Dunfern",
        (
            '"Speak at once, for pity’s sake! '
            'and do not hide from me the answer of truth '
            'and honest knowledge? Oh, merciful heavens!"'
        ),
    )

    out = r._snap_say_candidate_to_source_quote_surfaces(
        candidate,
        {1: source},
    )

    assert out is not None
    assert payloads(out) == [
        (
            "Lady Dunfern | "
            "Speak at once, for pity's sake! "
            "and do not hide from me the answer of truth "
            "and honest knowledge? Oh, merciful heavens!"
        )
    ]


def test_k1_missing_vocative_snaps_to_full_exact_source():
    source = (
        '"Tell me, I implore of you, Sir John and husband, '
        'why the once blithe and cheerful spot of peace is '
        'now apparently a dismal dungeon on the night of '
        'our home-coming, when all should have been a mass '
        'of dazzling glow and splendour?'
    )

    candidate = record(
        "Sir John and husband",
        (
            '"Tell me, I implore of you, why the once blithe '
            'and cheerful spot of peace is now apparently a '
            'dismal dungeon on the night of our home-coming, '
            'when all should have been a mass of dazzling glow '
            'and splendour?"'
        ),
    )

    out = r._snap_say_candidate_to_source_quote_surfaces(
        candidate,
        {1: source},
    )

    assert out is not None
    assert payloads(out) == [
        (
            "Sir John and husband | "
            "Tell me, I implore of you, Sir John and husband, "
            "why the once blithe and cheerful spot of peace is "
            "now apparently a dismal dungeon on the night of "
            "our home-coming, when all should have been a mass "
            "of dazzling glow and splendour?"
        )
    ]


def test_k1_split_quote_projects_to_two_exact_source_fragments():
    source = (
        '"Tom," cried Sir John, in great agony, '
        '"kindly wait for a few minutes, because '
        'her ladyship has been overcome." '
        'Tom stepped back.'
    )

    candidate = record(
        "Sir John",
        (
            '"Tom, kindly wait for a few minutes, because '
            'her ladyship has been overcome."'
        ),
    )

    out = r._snap_say_candidate_to_source_quote_surfaces(
        candidate,
        {1: source},
    )

    assert out is not None
    assert payloads(out) == [
        "Sir John | Tom,",
        (
            "Sir John | "
            "kindly wait for a few minutes, because "
            "her ladyship has been overcome."
        ),
    ]


def test_k1_does_not_snap_unquoted_narration():
    source = (
        "Sir John saw that delay was dangerous and "
        "summoned the village doctor immediately."
    )

    candidate = record(
        "Sir John",
        "Sir John saw that delay was dangerous",
    )

    assert (
        r._snap_say_candidate_to_source_quote_surfaces(
            candidate,
            {1: source},
        )
        is None
    )


def test_k1_leaves_existing_literal_candidate_to_old_path():
    source = '"Wait here until I return."'

    candidate = record(
        "Mira",
        "Wait here until I return.",
    )

    assert (
        r._snap_say_candidate_to_source_quote_surfaces(
            candidate,
            {1: source},
        )
        is None
    )


def test_k1_refuses_short_fuzzy_expansion():
    source = '"Wait here please, until I return tomorrow."'

    candidate = record(
        "Mira",
        "Wait here please",
    )

    assert (
        r._snap_say_candidate_to_source_quote_surfaces(
            candidate,
            {1: source},
        )
        is None
    )
