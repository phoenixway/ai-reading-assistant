from app.protocol import Record
from app.reader import _say_source_evidence


def _say(
    speaker,
    content,
    *,
    p=3,
):
    return Record(
        tag="SAY",
        payload=f"{speaker} | {content}",
        spans=[p],
        epistemic="EXPLICIT",
        raw="",
    )


def _evidence(
    source,
    speaker,
    content,
):
    return _say_source_evidence(
        _say(
            speaker,
            content,
        ),
        {
            3: source,
        },
    )


def test_started_can_introduce_direct_quote():
    source = (
        'Dax started, “I thought the east room—” '
        'but Lora interrupted, “Not tonight.”'
    )

    assert _evidence(
        source,
        "Dax",
        "I thought the east room—",
    ) == "spoken"


def test_interrupted_can_introduce_direct_quote():
    source = (
        'Dax started, “I thought the east room—” '
        'but Lora interrupted, “Not tonight.”'
    )

    assert _evidence(
        source,
        "Lora",
        "Not tonight",
    ) == "spoken"


def test_started_without_named_speaker_is_not_enough():
    source = (
        'The engine started. '
        'A display showed “READY”.'
    )

    assert _evidence(
        source,
        "Dax",
        "READY",
    ) != "spoken"


def test_interrupted_without_matching_speaker_is_not_enough():
    source = (
        'Mira interrupted, “Wait.”'
    )

    assert _evidence(
        source,
        "Jonas",
        "Wait",
    ) != "spoken"
