from __future__ import annotations

import argparse
import json
import re
from collections import Counter

from app.db import connect
from app.reader import build_prompt


QUOTE_RE = re.compile(
    r'["“”]'
)


def short(
    text: str | None,
    limit: int = 700,
):
    if not text:
        return "(none)"

    text = re.sub(
        r"\s+",
        " ",
        str(text),
    ).strip()

    if len(text) > limit:
        return (
            text[:limit - 3]
            + "..."
        )

    return text


def transition_repr(
    row,
):
    if row is None:
        return "(none)"

    data = dict(row)

    useful = {
        key: value
        for key, value in data.items()
        if value not in (
            None,
            "",
        )
        and key not in {
            "id",
            "book_id",
            "seg_id",
        }
    }

    return json.dumps(
        useful,
        ensure_ascii=False,
        default=str,
    )


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--book-id",
        type=int,
        required=True,
    )

    ap.add_argument(
        "--through-chapter",
        type=int,
        default=10,
    )

    args = ap.parse_args()

    with connect() as con:
        book = con.execute(
            """
            SELECT *
            FROM books
            WHERE id=?
            """,
            (args.book_id,),
        ).fetchone()

        if book is None:
            raise SystemExit(
                "book not found"
            )

        segments = con.execute(
            """
            SELECT *
            FROM segments
            WHERE book_id=?
              AND chapter <= ?
            ORDER BY idx
            """,
            (
                args.book_id,
                args.through_chapter,
            ),
        ).fetchall()

        print(
            "=== REAL BOOK AUDIT ==="
        )
        print(
            "book:",
            book["id"],
            book["title"],
        )
        print(
            "segments:",
            len(segments),
        )

        total_obs = Counter()
        suspicious_speech = []

        for seg in segments:
            span_rows = con.execute(
                """
                SELECT
                    s.pos,
                    s.text,
                    s.tok_len
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

            source = "\n\n".join(
                row["text"]
                for row in span_rows
            )

            quote_spans = [
                row
                for row in span_rows
                if QUOTE_RE.search(
                    row["text"]
                )
            ]

            obs_rows = con.execute(
                """
                SELECT
                    tag,
                    payload,
                    spans
                FROM observations
                WHERE book_id=?
                  AND seg_id=?
                ORDER BY pos, id
                """,
                (
                    args.book_id,
                    seg["id"],
                ),
            ).fetchall()

            counts = Counter(
                row["tag"]
                for row in obs_rows
            )

            total_obs.update(
                counts
            )

            summary = con.execute(
                """
                SELECT text
                FROM summaries
                WHERE book_id=?
                  AND seg_id=?
                  AND level='segment'
                ORDER BY rowid DESC
                LIMIT 1
                """,
                (
                    args.book_id,
                    seg["id"],
                ),
            ).fetchone()

            transition = con.execute(
                """
                SELECT *
                FROM transitions
                WHERE book_id=?
                  AND seg_id=?
                ORDER BY rowid DESC
                LIMIT 1
                """,
                (
                    args.book_id,
                    seg["id"],
                ),
            ).fetchone()

            if (
                quote_spans
                and counts.get(
                    "SAY",
                    0,
                ) == 0
            ):
                suspicious_speech.append(
                    (
                        int(seg["idx"]),
                        int(seg["chapter"]),
                        len(quote_spans),
                    )
                )

            print()
            print(
                "=" * 100
            )

            print(
                f"SEG {seg['idx']:02} "
                f"chapter={seg['chapter']} "
                f"tokens={seg['tok_len']} "
                f"status={seg['status']}"
            )

            print(
                "obs:",
                " ".join(
                    f"{tag}={counts[tag]}"
                    for tag in sorted(
                        counts
                    )
                )
                or "(none)",
            )

            print(
                "quote-bearing spans:",
                len(quote_spans),
            )

            if quote_spans:
                print(
                    "quote sample:",
                    short(
                        quote_spans[0][
                            "text"
                        ],
                        320,
                    ),
                )

            print(
                "summary:",
                short(
                    summary["text"]
                    if summary
                    else None
                ),
            )

            print(
                "transition:",
                short(
                    transition_repr(
                        transition
                    ),
                    1000,
                ),
            )

        print()
        print(
            "=" * 100
        )
        print(
            "GLOBAL"
        )
        print(
            "=" * 100
        )

        print(
            "observations:",
            dict(
                sorted(
                    total_obs.items()
                )
            ),
        )

        print(
            "segments with quotation marks "
            "but zero SAY:",
            suspicious_speech
            or "(none)",
        )

        print()
        print(
            "=== SAY LEDGER ==="
        )

        says = con.execute(
            """
            SELECT
                s.chapter,
                s.idx AS segment_idx,
                o.payload,
                o.spans
            FROM observations o
            JOIN segments s
              ON s.id=o.seg_id
            WHERE o.book_id=?
              AND o.tag='SAY'
              AND s.chapter <= ?
            ORDER BY s.idx, o.pos, o.id
            """,
            (
                args.book_id,
                args.through_chapter,
            ),
        ).fetchall()

        if not says:
            print(
                "(none)"
            )

        for row in says:
            print(
                f"ch={row['chapter']} "
                f"seg={row['segment_idx']} "
                f"{row['payload']} "
                f"| {row['spans']}"
            )

        # ----------------------------------------------------
        # What will the NEXT unread segment actually receive?
        # ----------------------------------------------------

        next_seg = con.execute(
            """
            SELECT *
            FROM segments
            WHERE book_id=?
              AND status='pending'
            ORDER BY idx
            LIMIT 1
            """,
            (
                args.book_id,
            ),
        ).fetchone()

        print()
        print(
            "=" * 100
        )
        print(
            "NEXT-SEGMENT COMPILED CONTEXT"
        )
        print(
            "=" * 100
        )

        if next_seg is None:
            print(
                "(no pending segment)"
            )
        else:
            print(
                f"next seg={next_seg['idx']} "
                f"chapter={next_seg['chapter']} "
                f"tokens={next_seg['tok_len']}"
            )

            messages, meta = build_prompt(
                con,
                args.book_id,
                next_seg,
            )

            print()
            print(
                "meta:",
                json.dumps(
                    meta,
                    ensure_ascii=False,
                    default=str,
                ),
            )

            for i, message in enumerate(
                messages,
                1,
            ):
                content = str(
                    message.get(
                        "content",
                        "",
                    )
                )

                print()
                print(
                    f"--- MESSAGE {i} "
                    f"role={message.get('role')} "
                    f"chars={len(content)} ---"
                )

                # Enough to inspect memory composition without
                # dumping another novel into the terminal.
                print(
                    content[:7000]
                )

                if len(content) > 7000:
                    print(
                        "\n...[TRUNCATED]..."
                    )


if __name__ == "__main__":
    main()
