from __future__ import annotations

import re
import time

import app.reader as reader

from app.db import connect
from scripts.benchmark_suite import (
    discover_gold_paths,
    load_fixture,
    run_fixture,
)


CASE = "gen-document-map"


original_extraction_chat = (
    reader._extraction_chat
)

gap_calls = 0


def wiretap_extraction_chat(
    *args,
    **kwargs,
):
    global gap_calls

    messages = None

    if len(args) >= 2:
        messages = args[1]
    elif "messages" in kwargs:
        messages = kwargs["messages"]

    is_gap = False

    if messages:
        for message in messages:
            content = str(
                message.get(
                    "content",
                    "",
                )
            )

            if (
                "OMISSION AUDITOR"
                in content
            ):
                is_gap = True
                break

    if is_gap:
        gap_calls += 1

        print()
        print(
            "#" * 110
        )
        print(
            f"PRODUCTION GAP CALL {gap_calls}"
        )
        print(
            "#" * 110
        )

        for i, message in enumerate(
            messages,
            1,
        ):
            print()
            print(
                f"--- MESSAGE {i} "
                f"role={message.get('role')} ---"
            )
            print(
                message.get(
                    "content",
                    "",
                )
            )

    result = original_extraction_chat(
        *args,
        **kwargs,
    )

    if is_gap:
        raw = (
            result[0]
            if isinstance(
                result,
                tuple,
            )
            else result
        )

        elapsed = (
            result[1]
            if (
                isinstance(
                    result,
                    tuple,
                )
                and len(result) > 1
            )
            else None
        )

        print()
        print(
            "--- RAW GAP RESPONSE ---"
        )
        print(
            str(raw).strip()
            or "(empty)"
        )

        if elapsed is not None:
            print(
                "elapsed:",
                elapsed,
            )

    return result


def exact_fold(
    payload: str,
):
    # fold / folds / folded / folding,
    # but NOT unfold / unfolded.
    return bool(
        re.search(
            r"\bfold(?:s|ed|ing)?\b",
            payload,
            re.I,
        )
    )


def main():
    reader._extraction_chat = (
        wiretap_extraction_chat
    )

    gold_path = None

    for candidate in (
        discover_gold_paths()
    ):
        gold, _ = load_fixture(
            candidate
        )

        if gold["case"] == CASE:
            gold_path = candidate
            break

    if gold_path is None:
        raise SystemExit(
            f"case not found: {CASE}"
        )

    suite_id = (
        "production-gap-wiretap-"
        + str(time.time_ns())
    )

    print(
        "suite_id:",
        suite_id,
    )

    item = run_fixture(
        gold_path,
        suite_id,
        verbose=False,
    )

    print()
    print(
        "=" * 110
    )
    print(
        "RUN RESULT"
    )
    print(
        "=" * 110
    )

    for key in (
        "case",
        "profile",
        "semantic",
        "grounded",
        "forbidden",
        "end",
        "overall",
        "book_id",
    ):
        if key in item:
            print(
                f"{key}:",
                item[key],
            )

    book_id = item[
        "book_id"
    ]

    with connect() as con:
        rows = con.execute(
            """
            SELECT
                pos,
                tag,
                payload,
                spans,
                raw_line
            FROM observations
            WHERE book_id=?
            ORDER BY pos, id
            """,
            (
                book_id,
            ),
        ).fetchall()

    print()
    print(
        "=== FINAL P03 / FOLD-RELATED LEDGER ==="
    )

    exact = []

    for row in rows:
        payload = row[
            "payload"
        ]

        interesting = (
            "p003" in str(
                row["spans"]
            )
            or exact_fold(
                payload
            )
        )

        if not interesting:
            continue

        print(
            f"{row['tag']:4} "
            f"{payload} "
            f"| {row['spans']} "
            f"| raw={row['raw_line']}"
        )

        if (
            row["tag"] == "EV"
            and exact_fold(
                payload
            )
        ):
            exact.append(
                payload
            )

    print()
    print(
        "EXACT FOLD EV:",
        exact
        or "MISSING",
    )

    print()
    print(
        "GAP CALLS:",
        gap_calls,
    )


if __name__ == "__main__":
    main()
