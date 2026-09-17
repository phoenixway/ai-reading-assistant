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


def test_nadia_post_quote_pronoun_attribution():
    source = (
        "Nadia placed a silver key on the kitchen table. "
        "“This opens the archive room, not the cellar,” "
        "she told Olek."
    )

    assert supports(
        source,
        "Nadia",
        "This opens the archive room, not the cellar",
    )


def test_olek_pre_quote_pronoun_elimination():
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


def test_petro_cannot_steal_olek_quote():
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


def test_two_named_men_abstain():
    source = (
        "Marek and Pavel stood beside the gate. "
        "“Wait,” he said."
    )

    assert not supports(
        source,
        "Marek",
        "Wait",
    )

    assert not supports(
        source,
        "Pavel",
        "Wait",
    )


def test_two_named_women_abstain():
    source = (
        "Nadia spoke quietly with Mira. "
        "“Wait,” she said."
    )

    assert not supports(
        source,
        "Nadia",
        "Wait",
    )

    assert not supports(
        source,
        "Mira",
        "Wait",
    )


def test_name_gender_is_not_evidence():
    source = (
        "Mara spoke to Levin beside the stairs. "
        "“Stop,” she said."
    )

    assert not supports(
        source,
        "Mara",
        "Stop",
    )


def test_existing_explicit_name_attribution_still_works():
    source = (
        'Mira folded the report and said, “Wait.”'
    )

    assert supports(
        source,
        "Mira",
        "Wait",
    )
