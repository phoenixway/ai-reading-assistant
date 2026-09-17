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

_NAME_SUBJECT_RE = re.compile(
    r"^(?P<subject>[A-Z][A-Za-z'-]+)\s+"
)

_IT_RE = re.compile(
    r"\bit\b",
    re.I,
)

_POSSESSION_RE = re.compile(
    r"^\s*(?P<subject>[A-Z][A-Za-z'-]+)"
    r"\s*\|\s*possession\s*\|\s*"
    r"holding\s+(?P<object>.+?)\s*$",
    re.I,
)

_TRANSFER_OBJECT_RE_TEMPLATE = (
    r"\b(?P<object>"
    r"(?:the|a|an)\s+"
    r"[A-Za-z][A-Za-z'-]*"
    r"(?:\s+[A-Za-z][A-Za-z'-]*){{0,3}}"
    r")\s+to\s+{subject}\b"
)


def paragraphs(text):
    return [
        p.strip()
        for p in re.split(
            r"\n\s*\n",
            text,
        )
        if p.strip()
    ]


def sentence_spans(text):
    out = []

    for m in re.finditer(
        r"[^.!?]+(?:[.!?]+[\"”’]?)?",
        text,
        re.S,
    ):
        value = m.group(0).strip()

        if value:
            out.append(value)

    return out


def canonical_object_phrase(value):
    value = value.strip(
        " \t\r\n\"'“”‘’.,;:!?"
    )

    if not value:
        return None

    # ST often says "holding compass".
    # For EV readability use the definite form.
    if not re.match(
        r"^(?:the|a|an)\b",
        value,
        re.I,
    ):
        value = "the " + value

    return value


def source_contains_object(
    source,
    object_phrase,
):
    bare = re.sub(
        r"^(?:the|a|an)\s+",
        "",
        object_phrase,
        flags=re.I,
    ).strip()

    if not bare:
        return False

    return bool(
        re.search(
            rf"\b{re.escape(bare)}\b",
            source,
            re.I,
        )
    )


def possession_candidate(
    subject,
    source,
    st_payloads,
):
    candidates = []

    for payload in st_payloads:
        m = _POSSESSION_RE.match(
            payload
        )

        if m is None:
            continue

        if (
            m.group("subject").casefold()
            != subject.casefold()
        ):
            continue

        value = canonical_object_phrase(
            m.group("object")
        )

        if value is None:
            continue

        if not source_contains_object(
            source,
            value,
        ):
            continue

        candidates.append(value)

    unique = list(
        dict.fromkeys(
            value.casefold()
            for value in candidates
        )
    )

    if len(unique) != 1:
        return None

    for value in candidates:
        if (
            value.casefold()
            == unique[0]
        ):
            return value

    return None


def transfer_candidate(
    subject,
    payload,
    source,
):
    """
    Strong local pattern:

        ... returned the canister to Tomas.
        Tomas tucked it beneath his coat.

    Requirements:
    - current EV has explicit named subject;
    - source contains a sentence beginning with that subject and
      containing the EV tail;
    - immediately preceding sentence ends with an article-headed
      object phrase transferred "to <subject>";
    - the object phrase occurs literally in source.

    No general nearest-noun heuristic.
    """

    sentences = sentence_spans(
        source
    )

    payload_tail = payload.split(
        maxsplit=1
    )

    if len(payload_tail) != 2:
        return None

    tail = payload_tail[1]

    current_index = None

    for i, sentence in enumerate(
        sentences
    ):
        if not re.match(
            rf"^\s*{re.escape(subject)}\b",
            sentence,
            re.I,
        ):
            continue

        if tail.casefold() not in (
            sentence.casefold()
        ):
            continue

        if current_index is not None:
            # Multiple possible source sentences: abstain.
            return None

        current_index = i

    if (
        current_index is None
        or current_index == 0
    ):
        return None

    previous = sentences[
        current_index - 1
    ]

    pattern = re.compile(
        _TRANSFER_OBJECT_RE_TEMPLATE.format(
            subject=re.escape(subject)
        ),
        re.I,
    )

    matches = list(
        pattern.finditer(previous)
    )

    if len(matches) != 1:
        return None

    value = canonical_object_phrase(
        matches[0].group("object")
    )

    if value is None:
        return None

    if not source_contains_object(
        source,
        value,
    ):
        return None

    return value


def bridge_object(
    payload,
    source,
    st_payloads,
):
    """
    Replace literal object pronoun `it` only with positive evidence.

    Evidence priority:
    1. EXPLICIT possession state for the same named subject.
    2. Immediate explicit transfer-to-subject pattern.

    Both methods must agree with literal source vocabulary.

    No nearest-noun selection.
    No gender inference.
    No general pronoun resolution.
    """

    if not _IT_RE.search(payload):
        return payload, False, None

    subject_match = _NAME_SUBJECT_RE.match(
        payload
    )

    if subject_match is None:
        return payload, False, None

    subject = subject_match.group(
        "subject"
    )

    evidence = []

    possession = possession_candidate(
        subject,
        source,
        st_payloads,
    )

    if possession is not None:
        evidence.append(
            (
                possession,
                "explicit-possession",
            )
        )

    transfer = transfer_candidate(
        subject,
        payload,
        source,
    )

    if transfer is not None:
        evidence.append(
            (
                transfer,
                "explicit-transfer",
            )
        )

    if not evidence:
        return payload, False, None

    normalized = {
        value.casefold()
        for value, _ in evidence
    }

    # Conflicting positive evidence means abstain.
    if len(normalized) != 1:
        return payload, False, None

    object_phrase = evidence[0][0]

    reasons = "+".join(
        reason
        for _, reason in evidence
    )

    value = _IT_RE.sub(
        object_phrase,
        payload,
    )

    if value == payload:
        return payload, False, None

    return value, True, reasons


def records_by_p(
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

        span_to_p = {
            row["span_id"]: int(
                row["local_no"]
            )
            for row in span_rows
        }

        rows = con.execute(
            """
            SELECT
                tag,
                payload,
                epistemic,
                spans
            FROM observations
            WHERE book_id=?
              AND seg_id=?
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
            part.strip()
            for part in (
                row["spans"]
                or ""
            ).split(",")
            if part.strip()
        ):
            p = span_to_p.get(
                span_id
            )

            if p is None:
                continue

            out.setdefault(
                p,
                [],
            ).append(
                {
                    "tag": row["tag"],
                    "payload": row["payload"],
                }
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

    by_p = records_by_p(
        book_id,
        scored["segment"],
    )

    transformed = {}

    for p, records in by_p.items():
        if not (
            1 <= p <= len(story)
        ):
            continue

        source = story[p - 1]

        st_payloads = [
            item["payload"]
            for item in records
            if item["tag"] == "ST"
        ]

        for item in records:
            if item["tag"] != "EV":
                continue

            payload = item["payload"]

            (
                value,
                changed,
                reason,
            ) = bridge_object(
                payload,
                source,
                st_payloads,
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
    "=== POSITIVE OBJECT BRIDGE CHANGES ==="
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

for canary in (
    "gen-ambiguous-pronoun",
    "gen-epistemic-claim",
):
    canary_changes = [
        item
        for item in changes
        if item["case"] == canary
    ]

    print(
        f"{canary} CHANGES:",
        len(canary_changes),
    )

    for item in canary_changes:
        print(
            "  ",
            item["before"],
            "=>",
            item["after"],
        )
