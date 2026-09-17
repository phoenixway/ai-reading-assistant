import re

from app.reader import (
    _DIRECT_ATTRIBUTION_VERBS,
    _say_content_bounds,
)


PRONOUN = r"(?:he|she|they)"

PROPER_RE = re.compile(
    r"\b[A-Z][a-zA-Z'-]+\b"
)


def proper_names(text):
    # Synthetic shadow only.
    # Drop obvious sentence-initial non-person words used here.
    stop = {
        "At",
        "After",
        "Later",
        "The",
        "A",
        "An",
    }

    return [
        x
        for x in PROPER_RE.findall(text)
        if x not in stop
    ]


def sentence_before(text):
    text = text.rstrip()

    if not text:
        return ""

    cut = max(
        text.rfind("."),
        text.rfind("!"),
        text.rfind("?"),
    )

    if cut < 0:
        return text

    return text[cut + 1:]


def previous_sentence(text):
    text = text.rstrip()

    if not text:
        return ""

    last = max(
        text.rfind("."),
        text.rfind("!"),
        text.rfind("?"),
    )

    if last < 0:
        return ""

    prefix = text[:last].rstrip()

    prev = max(
        prefix.rfind("."),
        prefix.rfind("!"),
        prefix.rfind("?"),
    )

    return prefix[prev + 1:]


def post_quote_pronoun_anchor(
    source,
    speaker,
    bounds,
):
    start, end = bounds

    after = source[end:end + 120]

    if not re.search(
        rf'^[\s,;:!?\"\'“”‘’\-–—]*'
        rf'{PRONOUN}\s+'
        rf'(?:{_DIRECT_ATTRIBUTION_VERBS})\b',
        after,
        re.I,
    ):
        return False

    before_quote = source[:start]

    # The utterance begins immediately after the previous
    # discourse sentence. Examine that sentence only.
    prior = previous_sentence(
        before_quote
    )

    if not prior:
        # If quote starts directly after the only sentence
        # in the available paragraph.
        prior = before_quote

    names = proper_names(prior)

    # Precision-first: candidate must be the only named
    # discourse participant in the anchoring sentence.
    return names == [speaker]


def pre_quote_pronoun_elimination(
    source,
    speaker,
    bounds,
):
    start, _ = bounds

    before = source[:start]

    current = sentence_before(before)
    prior = previous_sentence(before)

    if not current or not prior:
        return False

    # Strong shape:
    #
    #   He handed Petro ... and said, “
    #
    m = re.search(
        rf'\b(?P<pro>{PRONOUN})\b'
        rf'(?P<body>[^.!?]{{0,180}}?)'
        rf'\b(?:{_DIRECT_ATTRIBUTION_VERBS})\b'
        rf'[^.!?]{{0,40}}'
        rf'[,:"“”\'‘’]\s*$',
        current,
        re.I,
    )

    if not m:
        return False

    current_names = proper_names(
        m.group("body")
    )

    prior_names = proper_names(prior)

    # Deduplicate while preserving order.
    prior_unique = list(
        dict.fromkeys(prior_names)
    )

    current_unique = list(
        dict.fromkeys(current_names)
    )

    # Precision-first local elimination:
    #
    # previous sentence introduces exactly two named
    # participants, one is candidate speaker;
    # the other one is explicitly named inside the
    # pronoun-subject clause.
    if len(prior_unique) != 2:
        return False

    if speaker not in prior_unique:
        return False

    other = next(
        x
        for x in prior_unique
        if x != speaker
    )

    if current_unique != [other]:
        return False

    return True


def supports(
    source,
    speaker,
    content,
):
    bounds = _say_content_bounds(
        source,
        content,
    )

    if bounds is None:
        return False, "no-bounds"

    if post_quote_pronoun_anchor(
        source,
        speaker,
        bounds,
    ):
        return True, "post-anchor"

    if pre_quote_pronoun_elimination(
        source,
        speaker,
        bounds,
    ):
        return True, "pre-elimination"

    return False, "abstain"


CASES = [
    (
        "nadia-positive",
        (
            'Nadia placed a silver key on the kitchen table. '
            '“This opens the archive room, not the cellar,” '
            'she told Olek.'
        ),
        "Nadia",
        "This opens the archive room, not the cellar",
        True,
    ),
    (
        "olek-positive",
        (
            'At dusk Olek met Petro beside the courtyard gate. '
            'He handed Petro the silver key and said, '
            '“Give this only to Nadia.”'
        ),
        "Olek",
        "Give this only to Nadia.",
        True,
    ),
    (
        "petro-must-not-steal-olek-quote",
        (
            'At dusk Olek met Petro beside the courtyard gate. '
            'He handed Petro the silver key and said, '
            '“Give this only to Nadia.”'
        ),
        "Petro",
        "Give this only to Nadia.",
        False,
    ),
    (
        "ambiguous-two-men",
        (
            'Marek and Pavel stood beside the gate. '
            '“Wait,” he said.'
        ),
        "Marek",
        "Wait",
        False,
    ),
    (
        "ambiguous-two-women",
        (
            'Nadia spoke quietly with Mira. '
            '“Wait,” she said.'
        ),
        "Nadia",
        "Wait",
        False,
    ),
    (
        "unrelated-prior-name",
        (
            'Mara spoke to Levin beside the stairs. '
            '“Stop,” she said.'
        ),
        "Mara",
        "Stop",
        False,
    ),
]


failed = False

for (
    name,
    source,
    speaker,
    content,
    expected,
) in CASES:
    actual, reason = supports(
        source,
        speaker,
        content,
    )

    ok = actual == expected

    print(
        f"{name:32} "
        f"expected={expected!s:5} "
        f"actual={actual!s:5} "
        f"{reason:16} "
        f"{'OK' if ok else 'FAIL'}"
    )

    failed |= not ok

if failed:
    raise SystemExit(1)
