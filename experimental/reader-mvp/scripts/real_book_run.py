from __future__ import annotations

import argparse
from pathlib import Path

from app.db import connect, init_db
from app.ingest import (
    ingest_text,
    read_epub,
)
from app.llama import LlamaClient
from app.reader import analyze_next


def load_text(path: Path) -> str:
    suffix = path.suffix.casefold()

    if suffix == ".epub":
        return read_epub(path)

    if suffix in {
        ".txt",
        ".md",
        ".markdown",
    }:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    raise SystemExit(
        "Supported formats for first real-book run: "
        ".txt, .md, .markdown, .epub"
    )


def get_book(book_id: int):
    with connect() as con:
        return con.execute(
            """
            SELECT *
            FROM books
            WHERE id=?
            """,
            (book_id,),
        ).fetchone()


def selected_chapters(
    book_id: int,
    count: int,
):
    with connect() as con:
        rows = con.execute(
            """
            SELECT DISTINCT chapter
            FROM segments
            WHERE book_id=?
            ORDER BY chapter
            """,
            (book_id,),
        ).fetchall()

    chapters = [
        int(row["chapter"])
        for row in rows
    ]

    return chapters[:count]


def segment_stats(
    book_id: int,
    chapters: list[int],
):
    if not chapters:
        return {
            "total": 0,
            "pending": 0,
            "done": 0,
            "other": 0,
        }

    marks = ",".join(
        "?"
        for _ in chapters
    )

    with connect() as con:
        rows = con.execute(
            f"""
            SELECT status, COUNT(*) AS n
            FROM segments
            WHERE book_id=?
              AND chapter IN ({marks})
            GROUP BY status
            """,
            (
                book_id,
                *chapters,
            ),
        ).fetchall()

    by_status = {
        row["status"]:
            int(row["n"])
        for row in rows
    }

    total = sum(
        by_status.values()
    )

    pending = by_status.get(
        "pending",
        0,
    )

    # Do not assume the exact terminal status name.
    done = sum(
        n
        for status, n in by_status.items()
        if status != "pending"
    )

    return {
        "total": total,
        "pending": pending,
        "done": done,
        "statuses": by_status,
    }


def next_pending(
    book_id: int,
):
    with connect() as con:
        return con.execute(
            """
            SELECT *
            FROM segments
            WHERE book_id=?
              AND status='pending'
            ORDER BY idx
            LIMIT 1
            """,
            (book_id,),
        ).fetchone()


def report(
    book_id: int,
    chapters: list[int],
):
    marks = ",".join(
        "?"
        for _ in chapters
    )

    params = (
        book_id,
        *chapters,
    )

    with connect() as con:
        segment_rows = con.execute(
            f"""
            SELECT
                idx,
                chapter,
                tok_len,
                status
            FROM segments
            WHERE book_id=?
              AND chapter IN ({marks})
            ORDER BY idx
            """,
            params,
        ).fetchall()

        obs = con.execute(
            f"""
            SELECT
                o.tag,
                COUNT(*) AS n
            FROM observations o
            JOIN segments s
              ON s.id=o.seg_id
            WHERE o.book_id=?
              AND s.chapter IN ({marks})
            GROUP BY o.tag
            ORDER BY o.tag
            """,
            params,
        ).fetchall()

        summaries = con.execute(
            f"""
            SELECT COUNT(*) AS n
            FROM summaries sm
            JOIN segments s
              ON s.id=sm.seg_id
            WHERE sm.book_id=?
              AND s.chapter IN ({marks})
            """,
            params,
        ).fetchone()

        transitions = con.execute(
            f"""
            SELECT COUNT(*) AS n
            FROM transitions t
            JOIN segments s
              ON s.id=t.seg_id
            WHERE t.book_id=?
              AND s.chapter IN ({marks})
            """,
            params,
        ).fetchone()

    print()
    print("=" * 90)
    print("REAL BOOK REPORT")
    print("=" * 90)

    print(
        "chapters:",
        chapters,
    )

    print(
        "segments:",
        len(segment_rows),
    )

    status_counts = {}

    total_tokens = 0

    for row in segment_rows:
        status_counts[
            row["status"]
        ] = (
            status_counts.get(
                row["status"],
                0,
            )
            + 1
        )

        total_tokens += int(
            row["tok_len"]
            or 0
        )

    print(
        "segment statuses:",
        status_counts,
    )

    print(
        "source tokens:",
        total_tokens,
    )

    print()
    print("observations:")

    for row in obs:
        print(
            f"  {row['tag']:4} "
            f"{int(row['n']):5}"
        )

    print()
    print(
        "summaries:",
        int(
            summaries["n"]
            if summaries
            else 0
        ),
    )

    print(
        "transitions:",
        int(
            transitions["n"]
            if transitions
            else 0
        ),
    )


def main():
    ap = argparse.ArgumentParser(
        description=(
            "Run the normal production reader pipeline "
            "on the first N chapters of a real book."
        )
    )

    source = ap.add_mutually_exclusive_group(
        required=True,
    )

    source.add_argument(
        "--file",
        type=Path,
        help="TXT/Markdown/EPUB file to ingest",
    )

    source.add_argument(
        "--book-id",
        type=int,
        help="Resume an already ingested book",
    )

    ap.add_argument(
        "--title",
        default=None,
    )

    ap.add_argument(
        "--author",
        default="",
    )

    ap.add_argument(
        "--chapters",
        type=int,
        default=10,
        help=(
            "Analyze first N distinct chapters "
            "(default: 10)"
        ),
    )

    args = ap.parse_args()

    if args.chapters < 1:
        raise SystemExit(
            "--chapters must be >= 1"
        )

    init_db()

    llama = LlamaClient()

    health = llama.health()

    if not health.get("ok"):
        raise SystemExit(
            "llama-server is offline"
        )

    if args.file is not None:
        path = args.file.expanduser().resolve()

        if not path.is_file():
            raise SystemExit(
                f"file not found: {path}"
            )

        text = load_text(
            path
        )

        if not text.strip():
            raise SystemExit(
                "book text is empty"
            )

        title = (
            args.title
            or path.stem
        )

        print(
            "ingesting:",
            path,
        )
        print(
            "title:",
            title,
        )

        book_id = ingest_text(
            title,
            text,
            author=args.author,
            source_type=(
                "epub"
                if path.suffix.casefold()
                == ".epub"
                else "file"
            ),
            source_ref=str(path),
        )

        print(
            "book_id:",
            book_id,
        )

    else:
        book_id = args.book_id

        book = get_book(
            book_id
        )

        if book is None:
            raise SystemExit(
                f"book_id not found: {book_id}"
            )

        print(
            "resuming book:",
            book_id,
            book["title"],
        )

    chapters = selected_chapters(
        book_id,
        args.chapters,
    )

    if not chapters:
        raise SystemExit(
            "no segments were created"
        )

    print()
    print(
        "selected chapters:",
        chapters,
    )

    stats = segment_stats(
        book_id,
        chapters,
    )

    print(
        "selected segments:",
        stats,
    )

    selected_set = set(
        chapters
    )

    completed_now = 0

    while True:
        seg = next_pending(
            book_id
        )

        if seg is None:
            print(
                "\nNo pending segments remain."
            )
            break

        chapter = int(
            seg["chapter"]
        )

        if chapter not in selected_set:
            print()
            print(
                "Reached first chapter outside "
                "the selected real-book window:",
                chapter,
            )
            break

        print()
        print(
            "-" * 90
        )

        print(
            f"segment {seg['idx']} "
            f"| chapter {chapter} "
            f"| tokens {seg['tok_len']}"
        )

        result = analyze_next(
            book_id
        )

        completed_now += 1

        profile = (
            result.get("profile")
            if isinstance(
                result,
                dict,
            )
            else None
        )

        elapsed = (
            result.get("elapsed")
            if isinstance(
                result,
                dict,
            )
            else None
        )

        contract = (
            result.get(
                "contract_pass"
            )
            if isinstance(
                result,
                dict,
            )
            else None
        )

        print(
            "profile:",
            profile,
        )

        print(
            "contract:",
            contract,
        )

        if elapsed is not None:
            print(
                "elapsed:",
                f"{elapsed:.2f}s",
            )

        stats = segment_stats(
            book_id,
            chapters,
        )

        print(
            "progress:",
            (
                f"{stats['done']}/"
                f"{stats['total']}"
            ),
            stats["statuses"],
        )

    print()
    print(
        "segments analyzed this run:",
        completed_now,
    )

    report(
        book_id,
        chapters,
    )

    print()
    print(
        "BOOK_ID=",
        book_id,
        sep="",
    )


if __name__ == "__main__":
    main()
