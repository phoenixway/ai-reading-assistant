import json
import re
from pathlib import Path

from app.db import connect
from app.reader import (
    _ACTION_COMPLEMENT_END_RE,
    _ACTION_COMPLEMENT_PREFIX_RE,
    _action_surface_positioned_filtered_tokens,
)
from scripts.score_smoke import (
    _latest_fixture_book,
    _match_patterns,
    score_book,
)


ROOT = Path("samples")


def paragraphs(text):
    return [
        p.strip()
        for p in re.split(
            r"\n\s*\n",
            text,
        )
        if p.strip()
    ]


def recover_tail_complement(
    payload,
    source,
):
    """
    Recover a literal trailing complement from SOURCE when the
    canonical EV itself no longer literally matches the clause.

    Intended shape:

        canonical:
            Ivo tossed the compass across the room

        source:
            He snatched it, wrapped it in a scarf,
            and tossed it across the room to Lian

    Evidence required:
    - named canonical subject;
    - literal action verb;
    - >=2-token literal trailing suffix;
    - verb + suffix identify exactly one source occurrence;
    - complement follows the suffix immediately;
    - complement uses the existing structural-preposition grammar.

    No subject resolution.
    No object resolution.
    No semantic paraphrase.
    """

    payload_tokens = (
        _action_surface_positioned_filtered_tokens(
            payload
        )
    )

    source_tokens = (
        _action_surface_positioned_filtered_tokens(
            source
        )
    )

    if len(payload_tokens) < 4:
        return payload, False, None

    subject = payload_tokens[0]["raw"]

    if not re.fullmatch(
        r"[A-Z][A-Za-z'-]+",
        subject,
    ):
        return payload, False, None

    action_tokens = payload_tokens[1:]

    if len(action_tokens) < 3:
        return payload, False, None

    verb = action_tokens[0]["norm"]

    # Try the longest trailing literal suffix first.
    # Minimum 2 filtered tokens prevents weak one-word anchors.
    suffix_candidates = []

    for start in range(
        1,
        len(action_tokens) - 1,
    ):
        suffix = [
            token["norm"]
            for token
            in action_tokens[start:]
        ]

        if len(suffix) >= 2:
            suffix_candidates.append(
                (
                    start,
                    suffix,
                )
            )

    suffix_candidates.sort(
        key=lambda item: len(item[1]),
        reverse=True,
    )

    for _, suffix in suffix_candidates:
        matches = []

        for verb_i, token in enumerate(
            source_tokens
        ):
            if token["norm"] != verb:
                continue

            # Find the suffix after this verb, but keep the window
            # local enough to remain within the same action clause.
            max_start = min(
                len(source_tokens)
                - len(suffix),
                verb_i + 8,
            )

            for suffix_i in range(
                verb_i + 1,
                max_start + 1,
            ):
                actual = [
                    t["norm"]
                    for t in source_tokens[
                        suffix_i:
                        suffix_i + len(suffix)
                    ]
                ]

                if actual != suffix:
                    continue

                # Do not jump across sentence punctuation between
                # the action verb and the suffix.
                between = source[
                    source_tokens[verb_i]["end"]:
                    source_tokens[
                        suffix_i
                        + len(suffix)
                        - 1
                    ]["end"]
                ]

                if re.search(
                    r"[.!?]",
                    between,
                ):
                    continue

                matches.append(
                    {
                        "verb_i": verb_i,
                        "suffix_i": suffix_i,
                        "end": source_tokens[
                            suffix_i
                            + len(suffix)
                            - 1
                        ]["end"],
                        "suffix": suffix,
                    }
                )

        # This suffix must identify exactly one source action.
        if len(matches) != 1:
            continue

        match = matches[0]

        remainder = source[
            match["end"]:
        ]

        prefix = (
            _ACTION_COMPLEMENT_PREFIX_RE.match(
                remainder
            )
        )

        if prefix is None:
            continue

        complement_source = remainder[
            prefix.start("prep"):
        ]

        boundary = (
            _ACTION_COMPLEMENT_END_RE.search(
                complement_source
            )
        )

        if boundary is None:
            complement = (
                complement_source.strip()
            )
        else:
            complement = (
                complement_source[
                    :boundary.start()
                ].strip()
            )

        if not complement:
            continue

        # Avoid adding something already represented.
        if complement.casefold() in payload.casefold():
            continue

        value = (
            payload.rstrip()
            + " "
            + complement
        )

        return (
            value,
            True,
            {
                "verb": verb,
                "suffix": " ".join(
                    match["suffix"]
                ),
                "complement": complement,
            },
        )

    return payload, False, None


def evs_by_p(
    book_id,
    seg_id,
):
    with connect() as con:
        spans = con.execute(
            """
            SELECT
                ss.local_no,
                ss.span_id
            FROM segment_spans ss
            WHERE ss.seg_id=?
            """,
            (seg_id,),
        ).fetchall()

        span_to_p = {
            row["span_id"]: int(
                row["local_no"]
            )
            for row in spans
        }

        rows = con.execute(
            """
            SELECT
                payload,
                spans
            FROM observations
            WHERE book_id=?
              AND seg_id=?
              AND tag='EV'
              AND epistemic='EXPLICIT'
            ORDER BY pos, id
            """,
            (
                book_id,
                seg_id,
            ),
        ).fetchall()

    out = {}

    for row in rows:
        for span_id in (
            x.strip()
            for x in (
                row["spans"]
                or ""
            ).split(",")
            if x.strip()
        ):
            p = span_to_p.get(
                span_id
            )

            if p is not None:
                out.setdefault(
                    p,
                    [],
                ).append(
                    row["payload"]
                )

    return out


def discover():
    return [
        ROOT / "smoke_gold.json",
        *sorted(
            (ROOT / "benchmarks").glob(
                "*_gold.json"
            )
        ),
    ]


changes = []
repairs = []


for gold_path in discover():
    gold = json.loads(
        gold_path.read_text(
            encoding="utf-8"
        )
    )

    with connect() as con:
        book_id = _latest_fixture_book(
            con,
            gold["fixture"],
        )

    scored = score_book(
        book_id,
        gold_path,
    )

    story = paragraphs(
        (
            ROOT / gold["story"]
        ).read_text(
            encoding="utf-8"
        )
    )

    by_p = evs_by_p(
        book_id,
        scored["segment"],
    )

    transformed = {}

    for p, payloads in by_p.items():
        if not (
            1 <= p <= len(story)
        ):
            continue

        source = story[p - 1]

        for payload in payloads:
            (
                value,
                changed,
                evidence,
            ) = recover_tail_complement(
                payload,
                source,
            )

            transformed.setdefault(
                p,
                [],
            ).append(value)

            if changed:
                changes.append(
                    {
                        "case": gold["case"],
                        "p": p,
                        "before": payload,
                        "after": value,
                        "evidence": evidence,
                    }
                )

    for result in scored["required"]:
        if result["provenance"]:
            continue

        rule = next(
            item
            for item in gold["required"]
            if item["id"]
            == result["id"]
        )

        if "EV" not in rule.get(
            "tags",
            []
        ):
            continue

        p = rule.get("p")

        matched = [
            value
            for value
            in transformed.get(
                p,
                [],
            )
            if _match_patterns(
                value,
                rule.get(
                    "patterns",
                    [],
                ),
            )
        ]

        if matched:
            repairs.append(
                {
                    "case": gold["case"],
                    "id": rule["id"],
                    "matches": matched,
                }
            )


print(
    "=== COORDINATED TAIL COMPLEMENT CHANGES ==="
)

for item in changes:
    print()
    print(
        f"[{item['case']}] "
        f"P{item['p']:02}"
    )
    print(
        "  BEFORE:",
        item["before"],
    )
    print(
        "  AFTER: ",
        item["after"],
    )
    print(
        "  EVIDENCE:",
        item["evidence"],
    )


print()
print(
    "=" * 100
)
print(
    "REPAIRED CURRENT FAILURES"
)
print(
    "=" * 100
)

for item in repairs:
    print(
        f"{item['case']}: "
        f"{item['id']}"
    )

    for match in item["matches"]:
        print(
            "  ",
            match,
        )


print()
print(
    "REPAIR COUNT:",
    len(repairs),
)


for canary in (
    "gen-ambiguous-pronoun",
    "gen-epistemic-claim",
    "gen-negative-intent",
):
    subset = [
        item
        for item in changes
        if item["case"] == canary
    ]

    print(
        f"{canary} CHANGES:",
        len(subset),
    )

    for item in subset:
        print(
            "  ",
            item["before"],
            "=>",
            item["after"],
        )
