import app.reader as r


SOURCE = {
    1: (
        '"You speak of your snowy tufts appearing where once '
        'there dwelt locks of glossy jet. Well, I am convinced '
        'they never originated through me.'
    ),
    2: (
        '"I now wish to retire, feeling greatly fatigued, '
        'and trusting our relations shall remain friendly '
        'and mutual, I bid thee good-night."'
    ),
    3: (
        "She left the room."
    ),
    4: (
        'Narration containing "some unrelated quoted words."'
    ),
}


def parsed(*records):
    return r.Parsed(
        records=list(records),
        ignored=[],
        quarantined=[],
        stats={},
        contract_pass=True,
    )


def say(speaker, content, p):
    return r.Record(
        tag="SAY",
        payload=f"{speaker} | {content}",
        spans=[p],
        epistemic=None,
        raw="test",
    )


def test_k2b_rewrites_wrong_speaker_in_leading_run():
    result = r._sanitize_say_coverage(
        parsed(
            say(
                "Silas",
                (
                    "You speak of your snowy tufts appearing "
                    "where once there dwelt locks of glossy jet."
                ),
                1,
            ),
            say(
                "Silas",
                (
                    "Well, I am convinced they never originated "
                    "through me."
                ),
                1,
            ),
            say(
                "Silas",
                (
                    "I now wish to retire, feeling greatly fatigued, "
                    "and trusting our relations shall remain friendly "
                    "and mutual, I bid thee good-night."
                ),
                2,
            ),
        ),
        SOURCE,
        boundary_speaker="Lady Dunfern",
    )

    assert len(result.records) == 3

    assert all(
        rec.payload.startswith(
            "Lady Dunfern | "
        )
        for rec in result.records
    )

    assert (
        result.stats[
            "say_boundary_speaker_rewritten"
        ]
        == 3
    )

    assert (
        result.stats[
            "say_boundary_direct_supported"
        ]
        == 3
    )


def test_k2b_does_not_need_name_repeated_in_current_source():
    source = dict(SOURCE)

    assert (
        "Lady Dunfern"
        not in " ".join(source.values())
    )

    result = r._sanitize_say_coverage(
        parsed(
            say(
                "Wrong Name",
                (
                    "I now wish to retire, feeling greatly fatigued, "
                    "and trusting our relations shall remain friendly "
                    "and mutual, I bid thee good-night."
                ),
                2,
            ),
        ),
        source,
        boundary_speaker="Lady Dunfern",
    )

    assert len(result.records) == 1
    assert result.records[0].payload.startswith(
        "Lady Dunfern | "
    )


def test_k2b_does_not_escape_leading_run():
    result = r._sanitize_say_coverage(
        parsed(
            say(
                "Silas",
                "some unrelated quoted words.",
                4,
            ),
        ),
        SOURCE,
        boundary_speaker="Lady Dunfern",
    )

    assert result.records == []


def test_k2b_without_capability_keeps_old_precision_behavior():
    result = r._sanitize_say_coverage(
        parsed(
            say(
                "Silas",
                (
                    "I now wish to retire, feeling greatly fatigued, "
                    "and trusting our relations shall remain friendly "
                    "and mutual, I bid thee good-night."
                ),
                2,
            ),
        ),
        SOURCE,
        boundary_speaker=None,
    )

    assert result.records == []
