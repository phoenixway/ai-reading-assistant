from __future__ import annotations

import re

from app.db import connect
from app.llama import LlamaClient
from app.protocol import parse_output
from app.reader import (
    _build_say_coverage_messages,
    _extraction_chat,
    _sanitize_say_coverage,
    _say_coverage_targets,
)


BOOK_ID = 364

# Real-book segments with substantial dialogue.
SEGMENT_IDXS = [
    5,   # chapter 5
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

    return text[:n] + " ...[clip]"


def main():
    llama = LlamaClient()

    if not llama.health().get("ok"):
        raise SystemExit(
            "llama-server offline"
        )

    with connect() as con:
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
                print(
                    f"SEG {idx}: missing"
                )
                continue

            print()
            print(
                "=" * 110
            )
            print(
                f"SEG {idx} "
                f"chapter={seg['chapter']} "
                f"tokens={seg['tok_len']}"
            )
            print(
                "=" * 110
            )

            targets = (
                _say_coverage_targets(
                    con,
                    seg["id"],
                )
            )

            print()
            print(
                "TARGET COUNT:",
                len(targets),
            )

            for target in targets:
                local_no = target[
                    "local_no"
                ]

                text = target[
                    "text"
                ]

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
                        1200,
                    )
                )

            if not targets:
                print(
                    "\nNO SAY TARGETS"
                )
                continue

            messages = (
                _build_say_coverage_messages(
                    targets
                )
            )

            print()
            print(
                "--- SAY USER MESSAGE ---"
            )

            print(
                clip(
                    messages[-1][
                        "content"
                    ],
                    5000,
                )
            )

            raw, elapsed = (
                _extraction_chat(
                    llama,
                    messages,
                )
            )

            print()
            print(
                "--- RAW SAY ---"
            )

            print(
                raw.strip()
                or "(empty)"
            )

            print(
                "elapsed:",
                f"{elapsed:.2f}s",
            )

            target_nos = {
                target["local_no"]
                for target in targets
            }

            parsed = parse_output(
                raw,
                target_nos,
                allowed_tags={
                    "SAY",
                },
                required_tags=set(),
                min_content=0,
            )

            print()
            print(
                "--- PARSED BEFORE SANITIZER ---"
            )

            if not parsed.records:
                print(
                    "(none)"
                )

            for record in parsed.records:
                print(
                    "SAY:",
                    record.payload,
                    "@",
                    record.spans,
                )

            source_by_local = {
                target["local_no"]:
                    target["text"]
                for target in targets
            }

            clean = (
                _sanitize_say_coverage(
                    parsed,
                    source_by_local,
                )
            )

            print()
            print(
                "--- AFTER SAY SANITIZER ---"
            )

            if not clean.records:
                print(
                    "(none)"
                )

            for record in clean.records:
                print(
                    "SAY:",
                    record.payload,
                    "@",
                    record.spans,
                )

            print()
            print(
                "SANITIZER STATS:",
                clean.stats,
            )


if __name__ == "__main__":
    main()
