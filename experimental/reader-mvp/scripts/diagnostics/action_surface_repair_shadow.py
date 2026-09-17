import re


ARTICLES = {
    "a",
    "an",
    "the",
}

SUBJECT_PRONOUNS = {
    "he",
    "she",
    "they",
    "it",
}


def tokens(text):
    return [
        {
            "raw": match.group(0),
            "norm": match.group(0).casefold(),
        }
        for match in re.finditer(
            r"[A-Za-z][A-Za-z'-]*|[0-9]+",
            text,
        )
    ]


def filtered_tokens(text):
    return [
        token
        for token in tokens(text)
        if token["norm"] not in ARTICLES
    ]


def candidate_parts(payload):
    parts = payload.strip().split(
        maxsplit=1,
    )

    if len(parts) != 2:
        return None

    subject, tail = parts

    return (
        subject,
        tail,
    )


def repair_surface_subject(
    payload,
    source,
):
    parsed = candidate_parts(payload)

    if parsed is None:
        return payload, False

    subject, tail = parsed

    # Already surface-safe.
    if subject.casefold() in SUBJECT_PRONOUNS:
        return payload, False

    # Only inspect candidates that currently claim
    # an explicit named/capitalized actor.
    if not subject[:1].isupper():
        return payload, False

    tail_tokens = [
        token["norm"]
        for token in filtered_tokens(tail)
    ]

    if not tail_tokens:
        return payload, False

    source_tokens = filtered_tokens(source)

    hits = []

    n = len(tail_tokens)

    for i in range(
        1,
        len(source_tokens) - n + 1,
    ):
        actual = [
            token["norm"]
            for token in source_tokens[
                i:i + n
            ]
        ]

        if actual != tail_tokens:
            continue

        previous = source_tokens[i - 1]

        if (
            previous["norm"]
            in SUBJECT_PRONOUNS
        ):
            hits.append(
                previous["raw"]
            )

    # Precision-first:
    # exactly one literal surface-subject match.
    if len(hits) != 1:
        return payload, False

    pronoun = hits[0]

    repaired = (
        pronoun
        + " "
        + tail
    )

    return repaired, True


CASES = [
    (
        "ambiguous-nod",
        "Marek nodded once",
        (
            "Marek and Pavel stood beside the gate. "
            "He nodded once. Neither man spoke."
        ),
    ),
    (
        "named-enter",
        "Pavel entered the ticket booth",
        (
            "A bell rang. Pavel entered the ticket booth "
            "while Marek remained beside the gate."
        ),
    ),
    (
        "named-open",
        "Marek opened the ledger",
        (
            "Marek opened the ledger and marked the time. "
            "He stayed beside the gate with the ledger open."
        ),
    ),
    (
        "canonicalized-stay",
        "Marek stayed beside the gate",
        (
            "Marek opened the ledger and marked the time. "
            "He stayed beside the gate with the ledger open."
        ),
    ),
    (
        "dax-set",
        "Dax set the crate beside the furnace",
        (
            'Dax started, “I thought the east room—” '
            'but Lora interrupted, “Not tonight.” '
            "He set the crate beside the furnace."
        ),
    ),
    (
        "already-pronoun",
        "He snatched the compass",
        (
            "Maeve set a brass compass beside Ivo. "
            "He snatched the compass."
        ),
    ),
    (
        "tomas-named",
        "Tomas tucked the canister beneath his coat",
        (
            "Elena returned the canister to Tomas. "
            "Tomas tucked it beneath his coat."
        ),
    ),
]


for name, payload, source in CASES:
    repaired, changed = repair_surface_subject(
        payload,
        source,
    )

    print()
    print("=" * 72)
    print(name)
    print("input:   ", payload)
    print("output:  ", repaired)
    print("changed: ", changed)
