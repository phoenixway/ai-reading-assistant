from __future__ import annotations

import re
import time

from app.db import connect, init_db
from app.llama import LlamaClient
from scripts.benchmark_suite import (
    discover_gold_paths,
    load_fixture,
    run_fixture,
)


CASES = {
    "b17-baseline",
    "document-vs-speech",
    "gen-document-map",
    "hedged-perception",
}

_PASS_BY_TAG = {
    "EV": "ACTION-COVERAGE",
    "SAY": "SAY-COVERAGE",
    "DET": "DOCUMENT-CONTENT",
}

_HEADER_RE = re.compile(
    r"^---\s+(.+?)\s+---$"
)


def split_raw_sections(raw: str):
    sections = {}
    current = "FAST"

    sections.setdefault(
        current,
        [],
    )

    for line in raw.splitlines():
        match = _HEADER_RE.match(
            line.strip()
        )

        if match:
            current = match.group(1)

            sections.setdefault(
                current,
                [],
            )

            continue

        sections.setdefault(
            current,
            [],
        ).append(line)

    return sections


def lines_for_p(
    sections,
    p,
):
    marker = re.compile(
        rf"@P{p:02}\b"
    )

    out = {}

    for name, lines in sections.items():
        hits = [
            line
            for line in lines
            if marker.search(line)
        ]

        if hits:
            out[name] = hits

    return out


def final_records_by_p(
    book_id,
    seg_idx,
):
    with connect() as con:
        seg = con.execute(
            """
            SELECT *
            FROM segments
            WHERE book_id=?
              AND idx=?
            """,
            (
                book_id,
                seg_idx,
            ),
        ).fetchone()

        if seg is None:
            raise RuntimeError(
                "segment not found"
            )

        span_rows = con.execute(
            """
            SELECT
                ss.local_no,
                ss.span_id,
                s.text
            FROM segment_spans ss
            JOIN spans s
              ON s.id=ss.span_id
            WHERE ss.seg_id=?
            ORDER BY ss.local_no
            """,
            (
                seg["id"],
            ),
        ).fetchall()

        span_to_p = {
            row["span_id"]:
                int(row["local_no"])
            for row in span_rows
        }

        source_by_p = {
            int(row["local_no"]):
                row["text"]
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
            ORDER BY pos, id
            """,
            (
                book_id,
                seg["id"],
            ),
        ).fetchall()

    by_p = {}

    for row in rows:
        local_refs = []

        for span_id in (
            part.strip()
            for part in (
                row["spans"]
                or ""
            ).split(",")
            if part.strip()
        ):
            local_no = span_to_p.get(
                span_id
            )

            if local_no is not None:
                local_refs.append(
                    local_no
                )

        for local_no in sorted(
            set(local_refs)
        ):
            by_p.setdefault(
                local_no,
                [],
            ).append(
                {
                    "tag": row["tag"],
                    "payload":
                        row["payload"],
                    "epistemic":
                        row["epistemic"],
                }
            )

    return (
        source_by_p,
        by_p,
    )


def target_map(attempts):
    out = {}

    for attempt in attempts:
        profile = attempt.get(
            "profile"
        )

        if profile not in {
            "ACTION-COVERAGE",
            "SAY-COVERAGE",
            "DOCUMENT-CONTENT",
        }:
            continue

        out[profile] = set(
            attempt.get(
                "targets",
                [],
            )
        )

    return out


def owner_passes(tags):
    passes = []

    for tag in tags:
        owner = _PASS_BY_TAG.get(
            tag
        )

        if (
            owner is not None
            and owner not in passes
        ):
            passes.append(owner)

    # Q may be supplied by FAST, while written-message gold
    # can also be satisfied by DET from DOCUMENT-CONTENT.
    if (
        "Q" in tags
        and "DOCUMENT-CONTENT"
        not in passes
    ):
        passes.append(
            "DOCUMENT-CONTENT"
        )

    return passes


def rule_for_id(
    gold,
    rule_id,
):
    return next(
        rule
        for rule in gold["required"]
        if rule["id"] == rule_id
    )


def print_raw_at_p(
    p,
    sections,
):
    raw_hits = lines_for_p(
        sections,
        p,
    )

    wanted_order = [
        "FAST",
        "FAST (salvage candidate)",
        "TARGETED-REPAIR",
        "ROBUST-A",
        "ACTION-COVERAGE",
        "SAY-COVERAGE",
        "DOCUMENT-CONTENT",
    ]

    printed = set()

    for name in wanted_order:
        lines = raw_hits.get(
            name
        )

        if not lines:
            continue

        printed.add(name)

        print(
            f"  [{name}]"
        )

        for line in lines:
            print(
                "    ",
                line,
            )

    for name, lines in raw_hits.items():
        if name in printed:
            continue

        print(
            f"  [{name}]"
        )

        for line in lines:
            print(
                "    ",
                line,
            )

    if not raw_hits:
        print(
            "  (no raw @P lines)"
        )


def main():
    init_db()

    health = LlamaClient().health()

    if not health.get("ok"):
        raise SystemExit(
            "llama-server is offline; "
            "start it first"
        )

    paths = []

    for gold_path in discover_gold_paths():
        gold, _ = load_fixture(
            gold_path
        )

        if gold["case"] in CASES:
            paths.append(
                gold_path
            )

    suite_id = (
        "recall-trace-"
        + str(time.time_ns())
    )

    print(
        "=== REMAINING RECALL TRACE ==="
    )
    print(
        "suite_id:",
        suite_id,
    )
    print()

    for gold_path in paths:
        gold, _ = load_fixture(
            gold_path
        )

        item = run_fixture(
            gold_path,
            suite_id,
            verbose=True,
        )

        misses = [
            result
            for result
            in item["required"]
            if not result["provenance"]
        ]

        if not misses:
            continue

        sections = split_raw_sections(
            item.get(
                "raw_output",
                "",
            )
        )

        targets = target_map(
            item.get(
                "attempts",
                [],
            )
        )

        (
            source_by_p,
            final_by_p,
        ) = final_records_by_p(
            item["book_id"],
            gold.get(
                "segment_idx",
                1,
            ),
        )

        print(
            "=" * 110
        )
        print(
            gold["case"],
            "|",
            item["profile"],
        )
        print(
            "=" * 110
        )

        for miss in misses:
            rule = rule_for_id(
                gold,
                miss["id"],
            )

            p = rule.get("p")
            tags = rule.get(
                "tags",
                [],
            )

            print()
            print(
                "-" * 110
            )
            print(
                "MISS:",
                miss["id"],
            )
            print(
                "tags:",
                tags,
            )
            print(
                "patterns:",
                rule.get(
                    "patterns",
                    [],
                ),
            )
            print(
                "semantic:",
                miss["semantic"],
                "provenance:",
                miss["provenance"],
            )

            if p is None:
                print(
                    "expected P: none"
                )
                continue

            print(
                f"expected P: P{p:02}"
            )

            print()
            print(
                "SOURCE:"
            )
            print(
                source_by_p.get(
                    p,
                    "(missing source)",
                )
            )

            print()
            print(
                "OWNER TARGET STATUS:"
            )

            owners = owner_passes(
                tags
            )

            if not owners:
                print(
                    "  no dedicated owner pass"
                )

            for owner in owners:
                owner_targets = (
                    targets.get(
                        owner,
                        set(),
                    )
                )

                if owner not in targets:
                    state = (
                        "PASS NOT RUN"
                    )
                elif p in owner_targets:
                    state = "TARGETED"
                else:
                    state = "NOT TARGETED"

                print(
                    f"  {owner}: {state}"
                )

            print()
            print(
                "RAW OUTPUT @P:"
            )
            print_raw_at_p(
                p,
                sections,
            )

            print()
            print(
                "FINAL LEDGER @P:"
            )

            records = final_by_p.get(
                p,
                [],
            )

            if not records:
                print(
                    "  (none)"
                )

            for record in records:
                print(
                    "  "
                    f"{record['tag']:4} "
                    f"{record['epistemic']:10} "
                    f"{record['payload']}"
                )

            if miss.get(
                "matches"
            ):
                print()
                print(
                    "SCORER PARTIAL MATCHES:"
                )

                for match in miss[
                    "matches"
                ]:
                    print(
                        " ",
                        match,
                    )

        print()

    print(
        "=" * 110
    )
    print(
        "TRACE COMPLETE"
    )


if __name__ == "__main__":
    main()
