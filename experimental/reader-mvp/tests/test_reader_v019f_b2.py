from app.reader import (
    _say_content_bounds,
    _source_supports_speaker,
)


def supports(
    source,
    speaker,
    content,
):
    bounds = _say_content_bounds(
        source,
        content,
    )

    assert bounds is not None

    return _source_supports_speaker(
        source,
        speaker,
        bounds,
    )


def test_lora_after_interrupted_quote_is_supported():
    source = (
        'Dax started, “I thought the east room—” '
        'but Lora interrupted, “Not tonight.”'
    )

    assert supports(
        source,
        "Lora",
        "Not tonight",
    )


def test_dax_cannot_steal_lora_second_quote():
    source = (
        'Dax started, “I thought the east room—” '
        'but Lora interrupted, “Not tonight.”'
    )

    assert not supports(
        source,
        "Dax",
        "Not tonight",
    )


def test_first_dax_quote_still_supported():
    source = (
        'Dax started, “I thought the east room—” '
        'but Lora interrupted, “Not tonight.”'
    )

    assert supports(
        source,
        "Dax",
        "I thought the east room—",
    )


def test_object_listener_still_cannot_steal_quote():
    source = (
        'Mira looked at Jonas and replied, “Wait.”'
    )

    assert supports(
        source,
        "Mira",
        "Wait",
    )

    assert not supports(
        source,
        "Jonas",
        "Wait",
    )


def test_petro_still_cannot_steal_olek_quote():
    source = (
        "At dusk Olek met Petro beside the courtyard gate. "
        "He handed Petro the silver key and said, "
        "“Give this only to Nadia.”"
    )

    assert supports(
        source,
        "Olek",
        "Give this only to Nadia.",
    )

    assert not supports(
        source,
        "Petro",
        "Give this only to Nadia.",
    )
