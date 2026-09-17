from __future__ import annotations

import re

from app.reader import (
    _action_meaningful_words,
    _action_possible_bases,
)


# ------------------------------------------------------------
# Minimal candidate decomposition.
#
# GAP output is intentionally constrained to the ordinary:
#
#   SUBJECT VERB ...
#
# form. If that shape is absent, abstain rather than trying to
# perform general semantic-role parsing.
# ------------------------------------------------------------

_SUBJECT_PRONOUNS = {
    "he",
    "she",
    "they",
    "it",
}


def action_parts(payload: str):
    tokens = re.findall(
        r"[A-Za-z][A-Za-z'-]*|[0-9]+",
        payload,
    )

    if len(tokens) < 2:
        return None

    return (
        tokens[0],
        tokens[1],
        tokens,
    )


def same_predicate(
    left: str,
    right: str,
) -> bool:
    return bool(
        _action_possible_bases(left)
        & _action_possible_bases(right)
    )


# ------------------------------------------------------------
# NOVELTY
#
# Drop an audit candidate if an existing EV at the same paragraph
# already expresses the same predicate with essentially the same
# content.
#
# This deliberately does NOT solve paraphrase equivalence.
# Precision is more important than aggressive deduplication.
# ------------------------------------------------------------

def action_content_words(
    payload: str,
):
    parts = action_parts(payload)

    if parts is None:
        return set()

    _subject, _predicate, tokens = parts

    tail = " ".join(
        tokens[2:]
    )

    return _action_meaningful_words(
        tail
    )


def candidate_is_already_covered(
    candidate: str,
    existing: list[str],
) -> bool:
    cparts = action_parts(
        candidate
    )

    if cparts is None:
        return True

    _csubject, cpred, _ = cparts

    cwords = action_content_words(
        candidate
    )

    for prior in existing:
        pparts = action_parts(
            prior
        )

        if pparts is None:
            continue

        _psubject, ppred, _ = pparts

        if not same_predicate(
            cpred,
            ppred,
        ):
            continue

        pwords = action_content_words(
            prior
        )

        # Predicate alone is not enough:
        #
        #   opened envelope
        #   opened door
        #
        # are distinct actions.
        if not cwords and not pwords:
            return True

        if not cwords or not pwords:
            continue

        overlap = (
            len(cwords & pwords)
            / max(
                1,
                min(
                    len(cwords),
                    len(pwords),
                ),
            )
        )

        if overlap >= 0.75:
            return True

    return False


# ------------------------------------------------------------
# SOURCE ROLE SUPPORT
#
# GAP is stricter than ordinary ACTION-COVERAGE.
#
# A candidate survives only when SOURCE itself supports its
# subject + predicate relation.
#
# Supported:
#
#   Sava arrived ...
#   She waited ...
#
# and same-subject coordinated continuation:
#
#   She circled checkpoint C ... and folded the map.
#
# We do NOT:
# - infer gender from names;
# - replace "someone" with a nearby character;
# - resolve arbitrary multi-sentence coreference;
# - let an object name become the actor.
# ------------------------------------------------------------

def sentence_chunks_with_candidate_predicate(
    source: str,
    predicate: str,
):
    sentences = [
        chunk.strip()
        for chunk in re.split(
            r'(?<=[.!?])["”’]?\s+',
            source,
        )
        if chunk.strip()
    ]

    out = []

    for sentence in sentences:
        words = re.findall(
            r"[A-Za-z][A-Za-z'-]*|[0-9]+",
            sentence,
        )

        if any(
            same_predicate(
                word,
                predicate,
            )
            for word in words
        ):
            out.append(
                sentence
            )

    return out


def direct_subject_predicate_supported(
    sentence: str,
    subject: str,
    predicate: str,
) -> bool:
    words = re.findall(
        r"[A-Za-z][A-Za-z'-]*|[0-9]+",
        sentence,
    )

    subject_cf = subject.casefold()

    for i, word in enumerate(words):
        if word.casefold() != subject_cf:
            continue

        # Direct:
        #
        #   Sava arrived
        #   She waited
        #
        if (
            i + 1 < len(words)
            and same_predicate(
                words[i + 1],
                predicate,
            )
        ):
            return True

        # Permit a very small auxiliary bridge:
        #
        #   Mara had opened ...
        #
        if (
            i + 2 < len(words)
            and words[i + 1].casefold()
            in {
                "has",
                "have",
                "had",
                "is",
                "are",
                "was",
                "were",
            }
            and same_predicate(
                words[i + 2],
                predicate,
            )
        ):
            return True

    return False


def coordinated_subject_predicate_supported(
    sentence: str,
    subject: str,
    predicate: str,
) -> bool:
    """
    Precision-safe same-subject coordination.

        She circled checkpoint C in red pencil
        and folded the map.

    The candidate subject must be the leading actor of the
    current clause, not merely any name before the coordinated
    predicate.

    Therefore:

        Mara handed Levin the key and opened the door.

    supports Mara -> opened, but never Levin -> opened.

    This is deliberately structural rather than semantic:
    - no narrative verb ontology;
    - no name/gender inference;
    - no arbitrary object->subject promotion.
    """

    words = re.findall(
        r"[A-Za-z][A-Za-z'-]*|[0-9]+",
        sentence,
    )

    if not words:
        return False

    folded = [
        word.casefold()
        for word in words
    ]

    subject_cf = subject.casefold()

    subject_positions = [
        i
        for i, word in enumerate(
            folded
        )
        if word == subject_cf
    ]

    predicate_positions = [
        i
        for i, word in enumerate(
            words
        )
        if same_predicate(
            word,
            predicate,
        )
    ]

    # Function/discourse words allowed before a clause-leading
    # subject. These are grammatical scaffolding, not a narrative
    # action ontology.
    prefix_words = {
        "a",
        "an",
        "the",
        "at",
        "after",
        "before",
        "later",
        "then",
        "when",
        "while",
        "on",
        "in",
        "during",
        "near",
        "inside",
        "outside",
        "by",
        "under",
        "over",
        "beside",
        "around",
        "toward",
        "towards",
        "through",
    }

    for predicate_i in predicate_positions:
        prior_subjects = [
            i
            for i in subject_positions
            if i < predicate_i
        ]

        if not prior_subjects:
            continue

        subject_i = max(
            prior_subjects
        )

        between = folded[
            subject_i + 1:
            predicate_i
        ]

        if not between:
            continue

        # Candidate predicate must be explicitly introduced as a
        # coordinated continuation.
        if between[-1] not in {
            "and",
            "then",
            "but",
            "or",
        }:
            continue

        # A fresh explicit personal-pronoun subject breaks
        # same-subject inheritance.
        if any(
            word in _SUBJECT_PRONOUNS
            for word in between[:-1]
        ):
            continue

        # ----------------------------------------------------
        # CLAUSE-HEAD GUARD
        #
        # Before the proposed subject there may be only harmless
        # introductory scaffolding. Another proper-name-like
        # participant before it means this subject can be an
        # object/listener/recipient and must not inherit the
        # coordinated predicate.
        #
        # Examples:
        #
        #   She circled ... and folded ...      -> OK
        #   At dusk Mara took ... and left ...  -> OK
        #   Mara handed Levin ... and opened... -> Levin DROP
        # ----------------------------------------------------

        prefix = words[:subject_i]

        prefix_has_person_subject = False

        for token in prefix:
            token_cf = token.casefold()

            if token_cf in _SUBJECT_PRONOUNS:
                prefix_has_person_subject = True
                break

            if (
                token[:1].isupper()
                and token_cf
                not in prefix_words
            ):
                prefix_has_person_subject = True
                break

        if prefix_has_person_subject:
            continue

        return True

    return False



_GAP_COORDINATED_SUBJECT_PRONOUNS = {
    "he",
    "she",
    "they",
}


def repair_gap_coordinated_surface_subject(
    candidate: str,
    source: str,
):
    """
    GAP-only precision repair.

    Undo unsupported named-subject canonicalization when the
    candidate predicate + tail is literally anchored in a
    same-subject coordinated SOURCE clause whose actor is a
    literal personal pronoun.

        candidate:
            Priya folded the map

        source:
            She circled checkpoint C ... and folded the map.

        result:
            She folded the map

    This deliberately does NOT resolve She -> Priya.
    It moves only toward literal SOURCE surface evidence.
    """

    parts = action_parts(
        candidate
    )

    if parts is None:
        return candidate, False

    subject, predicate, tokens = parts

    if (
        not subject[:1].isupper()
        or subject.casefold()
        in _GAP_COORDINATED_SUBJECT_PRONOUNS
    ):
        return candidate, False

    # Tail after predicate, with articles ignored for literal
    # alignment.
    article_words = {
        "a",
        "an",
        "the",
    }

    wanted_tail = [
        token.casefold()
        for token in tokens[2:]
        if token.casefold()
        not in article_words
    ]

    hits = []

    for sentence in (
        sentence_chunks_with_candidate_predicate(
            source,
            predicate,
        )
    ):
        source_words = re.findall(
            r"[A-Za-z][A-Za-z'-]*|[0-9]+",
            sentence,
        )

        folded = [
            word.casefold()
            for word in source_words
        ]

        for predicate_i, word in enumerate(
            source_words
        ):
            if not same_predicate(
                word,
                predicate,
            ):
                continue

            # Candidate tail must match SOURCE immediately after
            # the predicate, modulo articles.
            source_tail = []

            for token in source_words[
                predicate_i + 1:
            ]:
                token_cf = token.casefold()

                if token_cf not in article_words:
                    source_tail.append(
                        token_cf
                    )

                if (
                    wanted_tail
                    and len(source_tail)
                    >= len(wanted_tail)
                ):
                    break

            if (
                wanted_tail
                and source_tail[
                    :len(wanted_tail)
                ] != wanted_tail
            ):
                continue

            # Require an explicit coordinator immediately before
            # the candidate predicate.
            if predicate_i <= 0:
                continue

            coordinator_i = (
                predicate_i - 1
            )

            if folded[
                coordinator_i
            ] not in {
                "and",
                "then",
                "but",
                "or",
            }:
                continue

            # Find literal personal-subject pronouns before the
            # coordinator. More than one => ambiguity => abstain.
            pronoun_positions = [
                i
                for i, token in enumerate(
                    folded[:coordinator_i]
                )
                if token
                in _GAP_COORDINATED_SUBJECT_PRONOUNS
            ]

            if len(
                pronoun_positions
            ) != 1:
                continue

            pronoun_i = (
                pronoun_positions[0]
            )

            # Another explicit personal subject between the
            # pronoun and coordinator would make inheritance
            # unsafe.
            later_pronouns = [
                token
                for token in folded[
                    pronoun_i + 1:
                    coordinator_i
                ]
                if token
                in _GAP_COORDINATED_SUBJECT_PRONOUNS
            ]

            if later_pronouns:
                continue

            hits.append(
                source_words[
                    pronoun_i
                ]
            )

    # Exactly one literal source anchor required.
    if len(hits) != 1:
        return candidate, False

    repaired = (
        hits[0]
        + " "
        + " ".join(tokens[1:])
    )

    return repaired, True


def candidate_has_source_role_support(
    candidate: str,
    source: str,
) -> bool:
    parts = action_parts(
        candidate
    )

    if parts is None:
        return False

    subject, predicate, _tokens = (
        parts
    )

    for sentence in (
        sentence_chunks_with_candidate_predicate(
            source,
            predicate,
        )
    ):
        if direct_subject_predicate_supported(
            sentence,
            subject,
            predicate,
        ):
            return True

        if coordinated_subject_predicate_supported(
            sentence,
            subject,
            predicate,
        ):
            return True

    return False


def gap_keep(
    candidate: str,
    source: str,
    existing: list[str],
):
    if candidate_is_already_covered(
        candidate,
        existing,
    ):
        return False, "already-covered"

    if not candidate_has_source_role_support(
        candidate,
        source,
    ):
        return False, "no-source-role-support"

    return True, "supported-novel-action"


CASES = [
    # --------------------------------------------------------
    # Desired GAP recoveries
    # --------------------------------------------------------
    (
        "KEEP sava arrival",
        "Sava arrived soaked through",
        (
            "The rain began after midnight. "
            "A courier named Sava arrived soaked through and handed "
            "Mara a narrow grey envelope."
        ),
        [
            "Sava handed Mara a grey envelope",
        ],
        True,
    ),
    (
        "KEEP keva wait after surface repair",
        "She waited a few seconds",
        (
            "Keva tilted her head as if she had heard a sound "
            "behind the door. "
            "She waited a few seconds, then walked to the platform."
        ),
        [
            "Keva tilted her head",
            "Keva walked to the platform",
        ],
        True,
    ),
    (
        "KEEP coordinated fold",
        "She folded the map",
        (
            "Malik asked whether the culvert was safe. "
            "Priya answered, “We take the ridge.” "
            "She circled checkpoint C in red pencil and folded the map."
        ),
        [
            "She circled checkpoint C in red pencil",
        ],
        True,
    ),

    # True event. Not necessarily important, but it is not a
    # fabricated world fact.
    (
        "KEEP literal rain event",
        "Rain began",
        (
            "The rain began after midnight."
        ),
        [],
        True,
    ),

    # --------------------------------------------------------
    # Repeated actions
    # --------------------------------------------------------
    (
        "DROP exact hand duplicate",
        "Sava handed Mara a grey envelope",
        (
            "Sava arrived soaked through and handed "
            "Mara a narrow grey envelope."
        ),
        [
            "Sava handed Mara a grey envelope",
        ],
        False,
    ),
    (
        "DROP near hand duplicate",
        "Sava handed a grey envelope",
        (
            "Sava arrived soaked through and handed "
            "Mara a narrow grey envelope."
        ),
        [
            "Sava handed Mara a grey envelope",
        ],
        False,
    ),
    (
        "DROP slip duplicate",
        "Mara slipped an envelope into her coat",
        (
            "Mara slipped it into her coat."
        ),
        [
            "Mara slipped the envelope into her coat",
        ],
        False,
    ),

    # --------------------------------------------------------
    # False-role adversarials
    # --------------------------------------------------------
    (
        "DROP invented Mara writer",
        "Mara wrote B17 in blue pencil",
        (
            "A courier named Sava arrived soaked through. "
            "On the front someone had written B17 in blue pencil. "
            "Mara slipped the envelope into her coat."
        ),
        [],
        False,
    ),
    (
        "DROP object steals coordinated action",
        "Levin opened the door",
        (
            "Mara handed Levin the key and opened the door."
        ),
        [],
        False,
    ),
    (
        "DROP ambiguous pronoun canonicalization",
        "Marek waited by the gate",
        (
            "Marek and Pavel stood beside the gate. "
            "He waited there."
        ),
        [],
        False,
    ),

    (
        "KEEP real leading actor coordination",
        "Mara opened the door",
        (
            "Mara handed Levin the key and opened the door."
        ),
        [],
        True,
    ),
    (
        "KEEP leading actor after discourse prefix",
        "Mara opened the door",
        (
            "At dusk Mara checked the lock and opened the door."
        ),
        [],
        True,
    ),
    (
        "DROP recipient steals then-coordination",
        "Levin opened the door",
        (
            "Mara handed Levin the key then opened the door."
        ),
        [],
        False,
    ),

    # Same predicate, different object must stay novel.
    (
        "KEEP distinct opened object",
        "Mara opened the envelope",
        (
            "Mara opened the envelope after checking the door."
        ),
        [
            "Mara opened the door",
        ],
        True,
    ),
]


def main():
    failed = 0

    print(
        "=== ACTION GAP FIREWALL SHADOW ==="
    )

    print()
    print(
        "=== COORDINATED SURFACE REPAIR ==="
    )

    repair_cases = [
        (
            "repair Priya to literal She",
            "Priya folded the map",
            (
                "Priya answered, “We take the ridge.” "
                "She circled checkpoint C in red pencil "
                "and folded the map."
            ),
            "She folded the map",
            True,
        ),
        (
            "do not steal from named Mara clause",
            "Levin opened the door",
            (
                "Mara handed Levin the key "
                "and opened the door."
            ),
            "Levin opened the door",
            False,
        ),
        (
            "no coordination no repair",
            "Marek waited by the gate",
            (
                "Marek and Pavel stood beside the gate. "
                "He waited there."
            ),
            "Marek waited by the gate",
            False,
        ),
    ]

    for (
        name,
        candidate,
        source,
        expected_value,
        expected_changed,
    ) in repair_cases:
        (
            value,
            changed,
        ) = repair_gap_coordinated_surface_subject(
            candidate,
            source,
        )

        ok = (
            value == expected_value
            and changed
            == expected_changed
        )

        print(
            "PASS" if ok else "FAIL",
            name,
        )
        print(
            "  value:  ",
            value,
        )
        print(
            "  changed:",
            changed,
        )

        if not ok:
            failed += 1

    for (
        name,
        candidate,
        source,
        existing,
        expected,
    ) in CASES:
        keep, reason = gap_keep(
            candidate,
            source,
            existing,
        )

        ok = (
            keep == expected
        )

        print()
        print(
            "PASS" if ok else "FAIL",
            name,
        )
        print(
            "  candidate:",
            candidate,
        )
        print(
            "  keep:     ",
            keep,
        )
        print(
            "  reason:   ",
            reason,
        )

        if not ok:
            print(
                "  expected: ",
                expected,
            )
            failed += 1

    print()
    print(
        f"RESULT: "
        f"{len(CASES) - failed}/"
        f"{len(CASES)}"
    )

    raise SystemExit(
        1 if failed else 0
    )


if __name__ == "__main__":
    main()
