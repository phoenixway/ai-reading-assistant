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

_PRONOUNS = {
    "he",
    "she",
    "they",
}

_NAME_RE = re.compile(
    r"\b[A-Z][A-Za-z'-]+\b"
)

_NON_NAMES = {
    "A",
    "An",
    "At",
    "After",
    "Before",
    "But",
    "Later",
    "Next",
    "On",
    "Instead",
    "Meanwhile",
    "The",
    "Then",
    "They",
    "He",
    "She",
    "When",
    "While",
}

_DISCOURSE_PREFIX_RE = re.compile(
    r"^\s*(?:"
    r"instead|then|later|next|"
    r"afterward|afterwards|meanwhile"
    r")?\s*",
    re.I,
)

_QUOTED_RE = re.compile(
    r'["“][^"”]*["”]',
    re.S,
)

_PERSON_DESCRIPTOR_RE = re.compile(
    r"\b(?:"
    r"a|an"
    r")\s+(?:"
    r"man|woman|boy|girl|person"
    r")\b",
    re.I,
)

_APPOSITION_RE = re.compile(
    r"\b(?P<name>[A-Z][A-Za-z'-]+)"
    r"\s*,\s+(?:a|an)\s+"
    r"(?P<label>"
    r"man|woman|boy|girl|male|female"
    r")\b",
)

_LABEL_PRONOUN = {
    "man": "he",
    "boy": "he",
    "male": "he",
    "woman": "she",
    "girl": "she",
    "female": "she",
}


def sentence_spans(text):
    out = []

    for match in re.finditer(
        r"[^.!?]+(?:[.!?]+[\"”’]?)?",
        text,
        re.S,
    ):
        value = match.group(0)

        if not value.strip():
            continue

        out.append(
            {
                "start": match.start(),
                "end": match.end(),
                "text": value.strip(),
            }
        )

    return out


def names_outside_quotes(text):
    clean = _QUOTED_RE.sub(
        " ",
        text,
    )

    names = []

    for name in _NAME_RE.findall(
        clean
    ):
        if name in _NON_NAMES:
            continue

        if name not in names:
            names.append(name)

    return names


def subject_tail(payload):
    parts = payload.strip().split(
        maxsplit=1,
    )

    if len(parts) != 2:
        return None

    subject, tail = parts

    if subject.casefold() not in _PRONOUNS:
        return None

    return subject, tail


def locate_action_sentence(
    source,
    pronoun,
    tail,
):
    """
    Locate the sentence containing the literal extracted action tail.

    This deliberately does not require the pronoun before every
    coordinated verb. Thus:

        He snatched it, wrapped it ..., and tossed it ...

    can support surface EVs:
        He snatched it
        He wrapped it ...
        He tossed it ...

    while the sentence-level grammatical subject remains literal He.
    """

    source_fold = source.casefold()
    tail_fold = tail.casefold()

    starts = []

    pos = 0

    while True:
        idx = source_fold.find(
            tail_fold,
            pos,
        )

        if idx < 0:
            break

        starts.append(idx)
        pos = idx + 1

    if len(starts) != 1:
        return None

    hit = starts[0]

    for index, sentence in enumerate(
        sentence_spans(source)
    ):
        if (
            sentence["start"]
            <= hit
            < sentence["end"]
        ):
            text = sentence["text"]

            head = _DISCOURSE_PREFIX_RE.sub(
                "",
                text,
                count=1,
            ).lstrip(
                ' "\'“”‘’'
            )

            if not re.match(
                rf"^{re.escape(pronoun)}\b",
                head,
                re.I,
            ):
                return None

            previous = (
                sentence_spans(source)[
                    index - 1
                ]["text"]
                if index > 0
                else ""
            )

            return {
                "sentence": text,
                "previous": previous,
            }

    return None


def apposition_antecedent(
    previous,
    pronoun,
):
    matches = []

    for match in _APPOSITION_RE.finditer(
        previous
    ):
        label = (
            match.group("label")
            .casefold()
        )

        if (
            _LABEL_PRONOUN.get(label)
            != pronoun.casefold()
        ):
            continue

        matches.append(
            match.group("name")
        )

    unique = list(
        dict.fromkeys(matches)
    )

    if len(unique) != 1:
        return None

    return unique[0]


def unique_previous_subject(
    previous,
):
    """
    Conservative discourse continuation:

        Priya answered ... . She circled ...
        Arden refused ... . Instead he closed ...

    Requirements:
    - quote contents do not contribute names;
    - exactly one proper name remains;
    - previous sentence begins with that name;
    - no unnamed person descriptor such as "a woman".

    Therefore:
        Marek and Pavel ... . He ...
    abstains.

        Mara waited until Levin ... . She ...
    abstains.
    """

    unquoted = _QUOTED_RE.sub(
        " ",
        previous,
    ).strip()

    if _PERSON_DESCRIPTOR_RE.search(
        unquoted
    ):
        return None

    names = names_outside_quotes(
        previous
    )

    if len(names) != 1:
        return None

    name = names[0]

    if not re.match(
        rf"^\s*{re.escape(name)}\b",
        unquoted,
    ):
        return None

    return name


def bridge_subject(
    payload,
    source,
):
    parsed = subject_tail(
        payload
    )

    if parsed is None:
        return payload, False, None

    pronoun, tail = parsed

    located = locate_action_sentence(
        source,
        pronoun,
        tail,
    )

    if located is None:
        return payload, False, None

    previous = located[
        "previous"
    ]

    # Strongest evidence first:
    # explicit textual gender/apposition.
    name = apposition_antecedent(
        previous,
        pronoun,
    )

    reason = None

    if name is not None:
        reason = "explicit-apposition"
    else:
        # Strong discourse evidence only:
        #
        #   Arden refused to pull the lever.
        #   Instead he closed the inspection cover.
        #
        # "Instead" explicitly contrasts the new action with the
        # immediately preceding actor's alternative action.
        #
        # Plain:
        #   Marek marked the time. He stayed ...
        #
        # is intentionally NOT enough.
        sentence = located["sentence"]

        if re.match(
            r"^\s*Instead\s+"
            r"(?:he|she|they)\b",
            sentence,
            re.I,
        ):
            candidate = unique_previous_subject(
                previous
            )

            if candidate is not None:
                name = candidate
                reason = "contrastive-instead"

    if name is None:
        return payload, False, None

    return (
        name + " " + tail,
        True,
        reason,
    )


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
                reason,
            ) = bridge_subject(
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
                        "reason": reason,
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
            payload
            for payload
            in transformed.get(
                p,
                [],
            )
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
                {
                    "case": gold["case"],
                    "id": rule["id"],
                    "matches": matched,
                }
            )


print(
    "=== SUBJECT BRIDGE CHANGES ==="
)

for item in changes:
    print()
    print(
        f"[{item['case']}] "
        f"P{item['p']:02} "
        f"{item['reason']}"
    )

    print(
        "  BEFORE:",
        item["before"],
    )

    print(
        "  AFTER: ",
        item["after"],
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


ambiguous_changes = [
    item
    for item in changes
    if item["case"]
    == "gen-ambiguous-pronoun"
]

print()
print(
    "AMBIGUOUS-PRONOUN CHANGES:",
    len(ambiguous_changes),
)

for item in ambiguous_changes:
    print(
        "  ",
        item["before"],
        "=>",
        item["after"],
    )
