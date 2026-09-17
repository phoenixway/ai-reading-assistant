from __future__ import annotations

import re

from app.db import connect
from app.llama import LlamaClient
from app.protocol import (
    merge_parsed,
    parse_output,
)
from app.reader import (
    _build_say_coverage_messages,
    _extraction_chat,
    _repair_say_missing_provenance,
    _sanitize_say_coverage,
    _say_coverage_batches,
    _say_segment_source_rows,
    _select_say_coverage_rows,
)


BOOK_ID = 364

# SEG5 is frozen-green. Exercise only the remaining real-book
# attribution cases.
SEGMENT_IDXS = [
    8,   # chapter 8
    11,  # chapter 10
]


def clip(
    text: str,
    n: int = 900,
):
    text = str(text)

    if len(text) <= n:
        return text

    return (
        text[:n]
        + " ...[clip]"
    )


def print_records(
    parsed,
):
    if not parsed.records:
        print("(none)")
        return

    for record in parsed.records:
        print(
            f"{record.tag}:",
            record.payload,
            "@",
            record.spans,
        )


def main():
    llama = LlamaClient()

    if not llama.health().get("ok"):
        raise SystemExit(
            "llama-server offline"
        )

    with connect() as con:
        segments = []

        for idx in SEGMENT_IDXS:
            seg = con.execute(
                """
                SELECT *
                FROM segments
                WHERE book_id=?
                  AND idx=?
                """,
                (
                    BOOK_ID,
                    idx,
                ),
            ).fetchone()

            if seg is None:
                segments.append(
                    (
                        idx,
                        None,
                        [],
                        [],
                    )
                )
                continue

            # Production topology:
            #
            # full SOURCE
            #   ├─ verifier evidence
            #   └─ selector -> LLM targets
            source_rows = list(
                _say_segment_source_rows(
                    con,
                    seg["id"],
                )
            )

            targets = (
                _select_say_coverage_rows(
                    source_rows
                )
            )

            segments.append(
                (
                    idx,
                    seg,
                    source_rows,
                    targets,
                )
            )

    # LLM calls happen outside the DB connection,
    # matching production.
    for (
        idx,
        seg,
        source_rows,
        targets,
    ) in segments:
        print()
        print(
            "=" * 118
        )

        if seg is None:
            print(
                f"SEG {idx}: missing"
            )
            print(
                "=" * 118
            )
            continue

        print(
            f"SEG {idx} "
            f"chapter={seg['chapter']} "
            f"tokens={seg['tok_len']}"
        )
        print(
            "=" * 118
        )

        source_by_local = {
            int(row["local_no"]):
                (row["text"] or "")
            for row in source_rows
        }

        print()
        print(
            "SOURCE ROW COUNT:",
            len(source_rows),
        )

        print(
            "TARGET COUNT:",
            len(targets),
        )

        if not targets:
            print(
                "NO SAY TARGETS"
            )
            continue

        batches = (
            _say_coverage_batches(
                targets,
            )
        )

        print(
            "BATCH COUNT:",
            len(batches),
        )

        print(
            "BATCH TARGETS:",
            [
                [
                    target["local_no"]
                    for target in batch
                ]
                for batch in batches
            ],
        )

        print()
        print(
            "--- ALL TARGETS ---"
        )

        for target in targets:
            local_no = int(
                target["local_no"]
            )

            text = target["text"]

            quote_count = len(
                re.findall(
                    r'["“”]',
                    text,
                )
            )

            print()
            print(
                f"[P{local_no:02}] "
                f"quotes={quote_count}"
            )

            print(
                clip(
                    text,
                    900,
                )
            )

        batch_parsed = []
        total_elapsed = 0.0
        total_provenance_completed = 0

        for batch_index, batch in enumerate(
            batches,
            start=1,
        ):
            batch_nos = [
                int(
                    target["local_no"]
                )
                for target in batch
            ]

            print()
            print(
                "#" * 118
            )
            print(
                f"BATCH {batch_index}/"
                f"{len(batches)} "
                f"targets={batch_nos}"
            )
            print(
                "#" * 118
            )

            messages = (
                _build_say_coverage_messages(
                    batch
                )
            )

            print()
            print(
                f"--- BATCH {batch_index} "
                "USER MESSAGE ---"
            )

            print(
                clip(
                    messages[-1][
                        "content"
                    ],
                    5000,
                )
            )

            raw, batch_elapsed = (
                _extraction_chat(
                    llama,
                    messages,
                )
            )

            total_elapsed += (
                batch_elapsed
            )

            print()
            print(
                f"--- BATCH {batch_index} "
                "RAW ---"
            )

            print(
                raw.strip()
                or "(empty)"
            )

            print(
                "elapsed:",
                f"{batch_elapsed:.2f}s",
            )

            # d2a, exactly as production:
            # missing provenance may be completed only against
            # the generation batch SOURCE.
            batch_source_by_local_no = {
                int(target["local_no"]):
                    (target["text"] or "")
                for target in batch
            }

            (
                repaired_raw,
                provenance_completed,
            ) = _repair_say_missing_provenance(
                raw,
                batch_source_by_local_no,
            )

            total_provenance_completed += (
                provenance_completed
            )

            print()
            print(
                f"BATCH {batch_index} "
                "PROVENANCE COMPLETED:",
                provenance_completed,
            )

            if repaired_raw != raw:
                print()
                print(
                    f"--- BATCH {batch_index} "
                    "AFTER D2A ---"
                )

                print(
                    repaired_raw.strip()
                    or "(empty)"
                )

            target_nos = set(
                batch_nos
            )

            parsed = parse_output(
                repaired_raw,
                target_nos,
                allowed_tags={
                    "SAY",
                },
                required_tags=set(),
                min_content=0,
            )

            batch_parsed.append(
                parsed
            )

            print()
            print(
                f"--- BATCH {batch_index} "
                "PARSED ---"
            )

            print_records(
                parsed
            )

            print()
            print(
                f"BATCH {batch_index} "
                "PARSE STATS:",
                parsed.stats,
            )

        if len(batch_parsed) == 1:
            merged = (
                batch_parsed[0]
            )
        else:
            merged = merge_parsed(
                batch_parsed,
                all(
                    part.contract_pass
                    for part in batch_parsed
                ),
            )

        print()
        print(
            "=" * 118
        )
        print(
            "--- MERGED BEFORE SANITIZER ---"
        )
        print(
            "=" * 118
        )

        print_records(
            merged
        )

        print()
        print(
            "MERGED STATS:",
            merged.stats,
        )

        print(
            "TOTAL PROVENANCE COMPLETED:",
            total_provenance_completed,
        )

        # Production topology:
        #
        # IMPORTANT: sanitizer gets ALL segment-local SOURCE,
        # not only the selected generation targets.
        clean = (
            _sanitize_say_coverage(
                merged,
                source_by_local,
            )
        )

        clean.stats[
            "say_provenance_completed"
        ] = total_provenance_completed

        print()
        print(
            "=" * 118
        )
        print(
            "--- AFTER CURRENT SAY SANITIZER ---"
        )
        print(
            "=" * 118
        )

        print_records(
            clean
        )

        print()
        print(
            "FINAL SANITIZER STATS:",
            clean.stats,
        )

        print(
            "TOTAL SAY ELAPSED:",
            f"{total_elapsed:.2f}s",
        )


if __name__ == "__main__":
    main()
