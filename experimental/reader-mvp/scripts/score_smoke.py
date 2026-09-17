"""Score the latest B17 smoke run against semantic gold assertions.

This is deliberately a coverage/grounding scorer, not an exhaustive precision
metric. Extra observations may be legitimate and are therefore not counted as
false positives yet.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import connect


DEFAULT_GOLD = ROOT / "samples" / "smoke_gold.json"


def _match_patterns(text: str, patterns: list[str]) -> bool:
    return all(re.search(p, text, re.I) is not None for p in patterns)


def _obs_matches(obs: dict, rule: dict) -> bool:
    if rule.get("tags") and obs["tag"] not in rule["tags"]:
        return False
    if rule.get("epistemic") and obs["epistemic"] != rule["epistemic"]:
        return False
    return _match_patterns(obs["payload"], rule.get("patterns", []))


def _local_refs(con, seg_id: str, spans_csv: str) -> list[int]:
    span_ids = [x for x in (spans_csv or "").split(",") if x]
    if not span_ids:
        return []

    rows = con.execute(
        """
        SELECT span_id, local_no
        FROM segment_spans
        WHERE seg_id=?
        """,
        (seg_id,),
    ).fetchall()
    by_span = {r["span_id"]: r["local_no"] for r in rows}
    return sorted({by_span[s] for s in span_ids if s in by_span})


def _latest_fixture_book(con, title: str) -> int:
    row = con.execute(
        "SELECT id FROM books WHERE title=? ORDER BY id DESC LIMIT 1",
        (title,),
    ).fetchone()
    if not row:
        raise SystemExit(f"No ingested fixture book found: {title!r}")
    return int(row["id"])


def score_book(book_id: int, gold_path: Path = DEFAULT_GOLD) -> dict:
    gold = json.loads(gold_path.read_text(encoding="utf-8"))

    with connect() as con:
        seg = con.execute(
            """
            SELECT *
            FROM segments
            WHERE book_id=? AND idx=?
            """,
            (book_id, gold.get("segment_idx", 1)),
        ).fetchone()
        if not seg:
            raise SystemExit(
                f"No segment idx={gold.get('segment_idx', 1)} for book {book_id}"
            )

        rows = con.execute(
            """
            SELECT id, tag, payload, spans, epistemic
            FROM observations
            WHERE book_id=? AND seg_id=?
            ORDER BY id
            """,
            (book_id, seg["id"]),
        ).fetchall()

        observations = []
        for r in rows:
            observations.append(
                {
                    "id": r["id"],
                    "tag": r["tag"],
                    "payload": r["payload"],
                    "epistemic": r["epistemic"],
                    "p": _local_refs(con, seg["id"], r["spans"]),
                }
            )

        transition_row = con.execute(
            """
            SELECT present, loc, situation
            FROM transitions
            WHERE book_id=? AND seg_id=?
            """,
            (book_id, seg["id"]),
        ).fetchone()

        paragraph_rows = con.execute(
            """
            SELECT ss.local_no, s.tok_len, s.text
            FROM segment_spans ss
            JOIN spans s ON s.id=ss.span_id
            WHERE ss.seg_id=?
            ORDER BY ss.local_no
            """,
            (seg["id"],),
        ).fetchall()

    required_results = []
    total_weight = 0.0
    semantic_weight = 0.0
    grounded_weight = 0.0

    for rule in gold["required"]:
        weight = float(rule.get("weight", 1))
        total_weight += weight

        candidates = [o for o in observations if _obs_matches(o, rule)]
        semantic_hit = bool(candidates)

        expected_p = rule.get("p")
        grounded = [
            o for o in candidates
            if expected_p is None or expected_p in o["p"]
        ]
        provenance_hit = bool(grounded)

        if semantic_hit:
            semantic_weight += weight
        if provenance_hit:
            grounded_weight += weight

        required_results.append(
            {
                "id": rule["id"],
                "weight": weight,
                "semantic": semantic_hit,
                "provenance": provenance_hit,
                "expected_p": expected_p,
                "matches": grounded or candidates,
            }
        )

    forbidden_results = []
    for rule in gold.get("forbidden", []):
        matches = [o for o in observations if _obs_matches(o, rule)]
        forbidden_results.append(
            {
                "id": rule["id"],
                "passed": not matches,
                "matches": matches,
            }
        )

    end_rule = gold.get("end", {})
    end = dict(transition_row) if transition_row else {
        "present": "",
        "loc": "",
        "situation": "",
    }

    end_checks = {
        "present": _match_patterns(
            end.get("present") or "",
            end_rule.get("present_patterns", []),
        ),
        "situation": _match_patterns(
            end.get("situation") or "",
            end_rule.get("situation_patterns", []),
        ),
        "loc_not_object": not any(
            re.search(p, end.get("loc") or "", re.I)
            for p in end_rule.get("forbidden_loc_patterns", [])
        ),
    }

    if "loc_patterns" in end_rule:
        end_checks["loc"] = _match_patterns(
            end.get("loc") or "",
            end_rule.get("loc_patterns", []),
        )

    semantic_coverage = semantic_weight / total_weight if total_weight else 1.0
    grounded_coverage = grounded_weight / total_weight if total_weight else 1.0
    forbidden_pass = (
        sum(1 for x in forbidden_results if x["passed"]) / len(forbidden_results)
        if forbidden_results else 1.0
    )
    end_pass = sum(end_checks.values()) / len(end_checks) if end_checks else 1.0

    # This aggregate is useful for quick regression comparisons, while the
    # component scores remain the authoritative diagnostics.
    overall = (
        0.45 * grounded_coverage
        + 0.25 * semantic_coverage
        + 0.20 * forbidden_pass
        + 0.10 * end_pass
    )

    paragraph_coverage = []

    structural_re = re.compile(r"^(?:chapter\s+\d+|\*{3,}|-{3,}|_{3,}|#{3,})$", re.I)

    for row in paragraph_rows:
        local_no = int(row["local_no"])
        text = (row["text"] or "").strip()

        if not text or structural_re.fullmatch(text):
            continue

        hits = [
            o for o in observations
            if local_no in o["p"]
        ]

        paragraph_coverage.append({
            "p": local_no,
            "tokens": int(row["tok_len"]),
            "observations": len(hits),
            "event_count": sum(1 for o in hits if o["tag"] == "EV"),
            "tags": [o["tag"] for o in hits],
        })

    return {
        "book_id": book_id,
        "segment": seg["id"],
        "observations": len(observations),
        "paragraph_coverage": paragraph_coverage,
        "scores": {
            "semantic_coverage": semantic_coverage,
            "grounded_coverage": grounded_coverage,
            "forbidden_pass": forbidden_pass,
            "end_pass": end_pass,
            "overall": overall,
        },
        "required": required_results,
        "forbidden": forbidden_results,
        "end": {
            "value": end,
            "checks": end_checks,
        },
    }


def _print_report(result: dict) -> None:
    s = result["scores"]

    print("=== GOLD SCORE ===")
    print(f"book_id: {result['book_id']}")
    print(f"segment: {result['segment']}")
    print(f"observations: {result['observations']}")
    print(f"semantic_coverage: {s['semantic_coverage']:.3f}")
    print(f"grounded_coverage: {s['grounded_coverage']:.3f}")
    print(f"forbidden_pass: {s['forbidden_pass']:.3f}")
    print(f"end_pass: {s['end_pass']:.3f}")
    print(f"overall: {s['overall']:.3f}")

    print("\n--- PARAGRAPH COVERAGE ---")
    for p in result["paragraph_coverage"]:
        tags = ",".join(p["tags"]) or "-"
        print(
            f"P{p['p']:02} tok={p['tokens']:3} "
            f"obs={p['observations']:2} "
            f"EV={p['event_count']:2} "
            f"tags={tags}"
        )

    print("\n--- REQUIRED ---")
    for x in result["required"]:
        mark = "OK" if x["provenance"] else ("SEM" if x["semantic"] else "MISS")
        suffix = ""
        if x["semantic"] and not x["provenance"]:
            suffix = f" expected @P{x['expected_p']}"
        print(f"{mark:4} {x['id']}{suffix}")
        for m in x["matches"][:2]:
            print(
                f"     {m['tag']} P{m['p']} {m['epistemic']}: "
                f"{m['payload']}"
            )

    print("\n--- FORBIDDEN ---")
    for x in result["forbidden"]:
        print(f"{'OK' if x['passed'] else 'FAIL':4} {x['id']}")
        for m in x["matches"][:2]:
            print(
                f"     {m['tag']} P{m['p']} {m['epistemic']}: "
                f"{m['payload']}"
            )

    print("\n--- END ---")
    print(json.dumps(result["end"], indent=2, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book-id", type=int)
    ap.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    gold = json.loads(args.gold.read_text(encoding="utf-8"))

    with connect() as con:
        book_id = args.book_id or _latest_fixture_book(con, gold["fixture"])

    result = score_book(book_id, args.gold)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        _print_report(result)


if __name__ == "__main__":
    main()
