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


def test_object_name_before_said_cannot_steal_quote():
    source = (
        "At dusk Olek met Petro beside the courtyard gate. "
        "He handed Petro the silver key and said, "
        "“Give this only to Nadia.”"
    )

    assert not supports(
        source,
        "Petro",
        "Give this only to Nadia.",
    )


def test_other_named_participant_cannot_steal_quote():
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


def test_simple_named_subject_still_works():
    source = (
        'Mira folded the report and said, “Wait.”'
    )

    assert supports(
        source,
        "Mira",
        "Wait",
    )


def test_discourse_prefix_before_named_subject_still_works():
    source = (
        'At dusk Mira lowered her voice and said, “Wait.”'
    )

    assert supports(
        source,
        "Mira",
        "Wait",
    )


def test_pronoun_bridge_still_resolves_olek():
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
