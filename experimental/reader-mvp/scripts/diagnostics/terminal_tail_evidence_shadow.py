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

STRUCTURAL_RE = re.compile(
    r"^(?:chapter\s+\d+|\*{3,}|-{3,}|_{3,}|#{3,})$",
    re.I,
)


def discover():
    paths = [
        ROOT / "smoke_gold.json",
    ]

    paths.extend(
        sorted(
            (ROOT / "benchmarks").glob(
                "*_gold.json"
            )
        )
    )

    return paths


def final_substantive_local_no(
    book_id,
    seg_id,
):
    with connect() as con:
        rows = con.execute(
            """
            SELECT
                ss.local_no,
                s.text
            FROM segment_spans ss
            JOIN spans s
              ON s.id = ss.span_id
            WHERE ss.seg_id=?
            ORDER BY ss.local_no
            """,
            (seg_id,),
        ).fetchall()

    candidates = []

    for row in rows:
        text = (
            row["text"]
            or ""
        ).strip()

        if not text:
            continue

        if STRUCTURAL_RE.fullmatch(
            text
        ):
            continue

        candidates.append(
            int(row["local_no"])
        )

    if not candidates:
        return None

    return candidates[-1]


def final_explicit_evs(
    book_id,
    seg_id,
    final_local_no,
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
                spans,
                pos
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

    out = []
    seen = set()

    for row in rows:
        raw_spans = (
            row["spans"]
            or ""
        )

        span_ids = [
            part.strip()
            for part in raw_spans.split(",")
            if part.strip()
        ]

        local_nos = {
            span_to_local.get(
                span_id
            )
            for span_id in span_ids
        }

        if (
            final_local_no
            not in local_nos
        ):
            continue

        payload = (
            row["payload"]
            or ""
        ).strip()

        if (
            not payload
            or payload in seen
        ):
            continue

        seen.add(payload)
        out.append(payload)

    return out


def augment(
    current,
    tail,
):
    parts = []

    if current.strip():
        parts.append(
            current.strip()
        )

    parts.extend(
        item.strip()
        for item in tail
        if item.strip()
    )

    return "; ".join(parts)


rows = []

for gold_path in discover():
    gold = json.loads(
        gold_path.read_text(
            encoding="utf-8"
        )
    )

    patterns = (
        gold.get("end", {})
        .get(
            "situation_patterns",
            [],
        )
    )

    if not patterns:
        continue

    with connect() as con:
        book_id = _latest_fixture_book(
            con,
            gold["fixture"],
        )

    scored = score_book(
        book_id,
        gold_path,
    )

    seg_id = scored["segment"]

    current = (
        scored["end"]["value"]
        .get(
            "situation",
            "",
        )
        or ""
    )

    current_ok = (
        scored["end"]["checks"]
        .get(
            "situation",
            True,
        )
    )

    final_p = (
        final_substantive_local_no(
            book_id,
            seg_id,
        )
    )

    tail = final_explicit_evs(
        book_id,
        seg_id,
        final_p,
    )

    all_value = augment(
        current,
        tail,
    )

    last3_value = augment(
        current,
        tail[-3:],
    )

    all_ok = _match_patterns(
        all_value,
        patterns,
    )

    last3_ok = _match_patterns(
        last3_value,
        patterns,
    )

    rows.append(
        {
            "case": gold["case"],
            "current": current,
            "current_ok": current_ok,
            "final_p": final_p,
            "tail": tail,
            "all": all_value,
            "all_ok": all_ok,
            "last3": last3_value,
            "last3_ok": last3_ok,
            "gold": patterns,
        }
    )


print(
    f"{'CASE':28} "
    f"{'NOW':4} "
    f"{'ALL':4} "
    f"{'LAST3':5} "
    f"{'N':>2}"
)

print("-" * 52)

for row in rows:
    print(
        f"{row['case'][:28]:28} "
        f"{'OK' if row['current_ok'] else 'FAIL':4} "
        f"{'OK' if row['all_ok'] else 'FAIL':4} "
        f"{'OK' if row['last3_ok'] else 'FAIL':5} "
        f"{len(row['tail']):2d}"
    )


def score(field):
    return sum(
        bool(row[field])
        for row in rows
    )


print()
print(
    "CURRENT GREEN:",
    f"{score('current_ok')}/{len(rows)}",
)

print(
    "ALL FINAL EV GREEN:",
    f"{score('all_ok')}/{len(rows)}",
)

print(
    "LAST3 FINAL EV GREEN:",
    f"{score('last3_ok')}/{len(rows)}",
)


for mode in (
    "all_ok",
    "last3_ok",
):
    regressions = [
        row["case"]
        for row in rows
        if (
            row["current_ok"]
            and not row[mode]
        )
    ]

    repairs = [
        row["case"]
        for row in rows
        if (
            not row["current_ok"]
            and row[mode]
        )
    ]

    print()
    print(mode)
    print(
        "  repairs:",
        repairs,
    )
    print(
        "  regressions:",
        regressions,
    )


print()
print("=" * 100)
print("DETAILS")
print("=" * 100)

for row in rows:
    print()
    print("=" * 100)
    print(row["case"])
    print("=" * 100)

    print(
        "FINAL P:",
        row["final_p"],
    )

    print(
        "CURRENT:",
        row["current"],
    )

    print(
        "CURRENT_OK:",
        row["current_ok"],
    )

    print()
    print("FINAL EXPLICIT EVS:")

    for item in row["tail"]:
        print(
            "  EV:",
            item,
        )

    print()
    print(
        "ALL_OK:",
        row["all_ok"],
    )

    print(
        "ALL:",
        row["all"],
    )

    print()
    print(
        "LAST3_OK:",
        row["last3_ok"],
    )

    print(
        "LAST3:",
        row["last3"],
    )

    print()
    print(
        "GOLD:",
        row["gold"],
    )
