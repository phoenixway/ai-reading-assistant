from app.protocol import Parsed, Record
from app.reader import (
    _base_g1_ev_is_quote_only,
    _base_g1_exact_surface_occurrences,
    _sanitize_base_grounding,
)


def ev(payload, p=1, raw=""):
    return Record(
        tag="EV",
        payload=payload,
        spans=[p],
        epistemic="EXPLICIT",
        raw=raw,
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


def clean(payload, source):
    return _sanitize_base_grounding(
        parsed(ev(payload)),
        {1: source},
    )


def test_exact_surface_locator_is_token_exact():
    source = (
        'He said, "Speak, I implore you." '
        'Then he stopped.'
    )

    hits = _base_g1_exact_surface_occurrences(
        "Speak, I implore you",
        source,
    )

    assert len(hits) == 1

    start, end = hits[0]

    assert source[start:end] == (
        "Speak, I implore you"
    )


def test_quote_only_imperative_is_detected():
    source = (
        '"Speak, I implore you, for my sake, '
        'and act no more the deceitful Duchess."'
    )

    assert _base_g1_ev_is_quote_only(
        ev("Speak, I implore you"),
        {1: source},
    )


def test_quote_only_act_no_more_is_dropped():
    source = (
        '"Speak, I implore you, for my sake, '
        'and act no more the deceitful Duchess."'
    )

    result = clean(
        "Act no more",
        source,
    )

    assert result.records == []
    assert (
        result.stats[
            "base_g1_quote_only_ev_dropped"
        ]
        == 1
    )


def test_quote_only_sit_in_silence_is_dropped():
    result = clean(
        "Sit in silence",
        (
            '"Do not sit in silence and allow '
            'the blood that now boils in my veins..."'
        ),
    )

    assert result.records == []


def test_same_surface_in_quote_and_narration_abstains():
    source = (
        '"Mara waited outside," he said. '
        "Mara waited outside."
    )

    result = clean(
        "Mara waited outside",
        source,
    )

    assert [
        r.payload
        for r in result.records
    ] == [
        "Mara waited outside",
    ]

    assert (
        result.stats[
            "base_g1_quote_only_ev_dropped"
        ]
        == 0
    )


def test_plain_narrative_action_survives():
    result = clean(
        "Sir John moved softly to the bedside",
        (
            "Sir John moved softly to the bedside "
            "and stopped there."
        ),
    )

    assert [
        r.payload
        for r in result.records
    ] == [
        "Sir John moved softly to the bedside",
    ]


def test_multitoken_actor_is_not_subject_parsed_here():
    result = clean(
        "Lady Dunfern grew cross",
        (
            "Lady Dunfern grew cross and careless."
        ),
    )

    assert [
        r.payload
        for r in result.records
    ] == [
        "Lady Dunfern grew cross",
    ]


def test_structured_pipe_ev_is_dropped():
    result = clean(
        (
            "Sir John | demands explanation | "
            "regarding Irene’s conduct"
        ),
        "Sir John demanded an explanation.",
    )

    assert result.records == []

    assert (
        result.stats[
            "base_g1_malformed_ev_dropped"
        ]
        == 1
    )


def test_structured_pipe_ev_is_quarantined():
    result = clean(
        "Irene | claims snowy tufts appeared before marriage",
        (
            '"You speak of your snowy tufts appearing..."'
        ),
    )

    assert len(result.quarantined) == 1

    raw, reason = result.quarantined[0]

    assert "Irene | claims" in raw
    assert "structured pipe" in reason


def test_non_ev_pipe_record_is_untouched():
    record = Record(
        tag="DET",
        payload="letter | meet me at midnight",
        spans=[1],
        epistemic="EXPLICIT",
        raw="",
    )

    result = _sanitize_base_grounding(
        parsed(record),
        {
            1: (
                "The letter read: meet me at midnight."
            ),
        },
    )

    assert result.records == [record]
