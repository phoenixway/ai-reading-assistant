import json
import re
from pathlib import Path

from app.db import connect
from scripts.score_smoke import (
    _latest_fixture_book,
    _match_patterns,
    score_book,
)


ROOT = Path("samples")

_ARTICLES = {
    "a",
    "an",
    "the",
}

# Structural argument/complement class only.
# No ordinary narrative verbs.
_COMPLEMENT_START_RE = re.compile(
    r"^\s+("
    r"in|into|inside|"
    r"on|onto|"
    r"under|beneath|beside|behind|"
    r"to|from|"
    r"through|across|"
    r"toward|towards|"
    r"near|at|over|around|within"
    r")\b",
    re.I,
)

_COMPLEMENT_END_RE = re.compile(
    r"[,.;!?]"
    r"|\s+\b(?:and|but|then)\b",
    re.I,
)


def tokens_with_spans(text):
    return [
        {
            "raw": m.group(0),
            "norm": m.group(0).casefold(),
            "start": m.start(),
            "end": m.end(),
        }
        for m in re.finditer(
            r"[A-Za-z0-9][A-Za-z0-9'-]*",
            text,
        )
    ]


def filtered(tokens):
    return [
        item
        for item in tokens
        if item["norm"] not in _ARTICLES
    ]


def extend_literal_complement(
    payload,
    source,
):
    """
    Extend an EV only when its filtered token sequence occurs
    uniquely and literally in SOURCE and is immediately followed
    by an explicit prepositional complement.

    No semantic rewriting.
    No subject/object resolution.
    No verb ontology.
    """

    payload_tokens = filtered(
        tokens_with_spans(payload)
    )

    source_tokens = filtered(
        tokens_with_spans(source)
    )

    if not payload_tokens:
        return payload, False

    wanted = [
        item["norm"]
        for item in payload_tokens
    ]

    n = len(wanted)
    hits = []

    for i in range(
        0,
        len(source_tokens) - n + 1,
    ):
        actual = [
            item["norm"]
            for item
            in source_tokens[i:i + n]
        ]

        if actual == wanted:
            hits.append(
                (
                    source_tokens[i]["start"],
                    source_tokens[i + n - 1]["end"],
                )
            )

    # Ambiguity means abstain.
    if len(hits) != 1:
        return payload, False

    _, end = hits[0]

    remainder = source[end:]

    start_match = _COMPLEMENT_START_RE.match(
        remainder
    )

    if start_match is None:
        return payload, False

    boundary = _COMPLEMENT_END_RE.search(
        remainder
    )

    if boundary is None:
        complement = remainder
    else:
        complement = remainder[
            :boundary.start()
        ]

    complement = complement.strip()

    if not complement:
        return payload, False

    result = (
        payload.rstrip()
        + " "
        + complement
    )

    return result, result != payload


def discover():
    return [
        ROOT / "smoke_gold.json",
        *sorted(
            (ROOT / "benchmarks").glob(
                "*_gold.json"
            )
        ),
    ]


def paragraphs(text):
    return [
        p.strip()
        for p in re.split(
            r"\n\s*\n",
            text,
        )
        if p.strip()
    ]


def evs_by_local_p(
    book_id,
    seg_id,
):
    with connect() as con:
        span_rows = con.execute(
            """
            SELECT
                ss.local_no,
                ss.span_id
            FROM segment_spans ss
            WHERE ss.seg_id=?
            """,
            (seg_id,),
        ).fetchall()

        span_to_local = {
            row["span_id"]: int(
                row["local_no"]
            )
            for row in span_rows
        }

        rows = con.execute(
            """
            SELECT
                id,
                payload,
                epistemic,
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
            p = span_to_local.get(
                span_id
            )

            if p is None:
                continue

            out.setdefault(
                p,
                [],
            ).append(
                row["payload"]
            )

    return out


repairs = []
changes = []


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

    by_p = evs_by_local_p(
        book_id,
        scored["segment"],
    )

    transformed_by_p = {}

    for p, payloads in by_p.items():
        if not (
            1 <= p <= len(story)
        ):
            continue

        source = story[p - 1]

        for payload in payloads:
            extended, changed = (
                extend_literal_complement(
                    payload,
                    source,
                )
            )

            transformed_by_p.setdefault(
                p,
                [],
            ).append(
                extended
            )

            if changed:
                changes.append(
                    (
                        gold["case"],
                        p,
                        payload,
                        extended,
                    )
                )

    for result in scored["required"]:
        if result["provenance"]:
            continue

        rule = next(
            item
            for item in gold["required"]
            if item["id"] == result["id"]
        )

        if "EV" not in rule.get(
            "tags",
            []
        ):
            continue

        p = rule.get("p")

        candidates = (
            transformed_by_p.get(
                p,
                [],
            )
        )

        matched = [
            payload
            for payload in candidates
            if _match_patterns(
                payload,
                rule.get(
                    "patterns",
                    [],
                ),
            )
        ]

        if matched:
            repairs.append(
                (
                    gold["case"],
                    rule["id"],
                    matched,
                )
            )


print(
    "=== LITERAL COMPLEMENT CHANGES ==="
)

for case, p, before, after in changes:
    print()
    print(
        f"[{case}] P{p:02}"
    )
    print(
        "  BEFORE:",
        before,
    )
    print(
        "  AFTER: ",
        after,
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

for case, rule_id, matches in repairs:
    print(
        f"{case}: {rule_id}"
    )

    for match in matches:
        print(
            "  ",
            match,
        )


print()
print(
    "REPAIR COUNT:",
    len(repairs),
)
