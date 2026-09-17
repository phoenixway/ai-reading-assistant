import json
import re
from pathlib import Path

from app.db import connect
from scripts.score_smoke import (
    _latest_fixture_book,
    score_book,
)


ROOT = Path("samples")


def discover():
    return [
        ROOT / "smoke_gold.json",
        *sorted(
            (ROOT / "benchmarks").glob(
                "*_gold.json"
            )
        ),
    ]


def story_paragraphs(text):
    return [
        part.strip()
        for part in re.split(
            r"\n\s*\n",
            text,
        )
        if part.strip()
    ]


def observations_by_local_p(
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

        obs_rows = con.execute(
            """
            SELECT
                id,
                tag,
                payload,
                epistemic,
                spans,
                raw_line
            FROM observations
            WHERE book_id=?
              AND seg_id=?
            ORDER BY pos, id
            """,
            (
                book_id,
                seg_id,
            ),
        ).fetchall()

    out = {}

    for row in obs_rows:
        raw_spans = (
            row["spans"]
            or ""
        )

        local_nos = []

        for span_id in (
            part.strip()
            for part
            in raw_spans.split(",")
            if part.strip()
        ):
            local_no = span_to_local.get(
                span_id
            )

            if local_no is not None:
                local_nos.append(
                    local_no
                )

        item = {
            "tag": row["tag"],
            "payload": row["payload"],
            "epistemic": row["epistemic"],
            "p": sorted(set(local_nos)),
            "raw": row["raw_line"],
        }

        for local_no in item["p"]:
            out.setdefault(
                local_no,
                [],
            ).append(item)

    return out


failure_count = 0


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

    failed = [
        item
        for item in scored["required"]
        if not item["provenance"]
    ]

    if not failed:
        continue

    failure_count += len(failed)

    story_path = (
        ROOT / gold["story"]
    )

    paragraphs = story_paragraphs(
        story_path.read_text(
            encoding="utf-8"
        )
    )

    by_p = observations_by_local_p(
        book_id,
        scored["segment"],
    )

    print()
    print("=" * 110)
    print(gold["case"])
    print("=" * 110)

    for item in failed:
        expected_p = item.get(
            "expected_p"
        )

        source = ""

        if (
            expected_p is not None
            and 1 <= expected_p <= len(paragraphs)
        ):
            source = paragraphs[
                expected_p - 1
            ]

        print()
        print("-" * 110)
        print(
            "MISS:",
            item["id"],
        )
        print(
            "semantic:",
            item["semantic"],
            "provenance:",
            item["provenance"],
        )

        rule = next(
            rule
            for rule in gold["required"]
            if rule["id"] == item["id"]
        )

        print(
            "expected tags:",
            rule.get("tags"),
        )
        print(
            "expected P:",
            expected_p,
        )
        print(
            "patterns:",
            rule.get("patterns"),
        )

        print()
        print(
            f"SOURCE P{expected_p:02}:"
            if expected_p is not None
            else "SOURCE:"
        )
        print(source)

        print()
        print("CANONICAL RECORDS AT P:")

        records = by_p.get(
            expected_p,
            [],
        )

        if not records:
            print("  (none)")
        else:
            for record in records:
                print(
                    f"  {record['tag']:4} "
                    f"{record['epistemic']:10} "
                    f"{record['payload']}"
                )

        if item["matches"]:
            print()
            print("SCORER PARTIAL MATCHES:")

            for match in item["matches"]:
                print(
                    f"  {match['tag']} "
                    f"P{match['p']} "
                    f"{match['epistemic']} "
                    f"{match['payload']}"
                )


print()
print("=" * 110)
print(
    "TOTAL REQUIRED FAILURES:",
    failure_count,
)
