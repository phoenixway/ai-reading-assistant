from __future__ import annotations

import re
import time

from app.db import connect, init_db
from app.llama import LlamaClient
from app.protocol import Parsed, Record, parse_output
from app.reader import (
    _extraction_chat,
    _sanitize_action_coverage,
)
from scripts.benchmark_suite import (
    discover_gold_paths,
    load_fixture,
    run_fixture,
)
from scripts.diagnostics.action_gap_audit_shadow import (
    ACTION_GAP_SYSTEM,
)
from scripts.diagnostics.action_gap_firewall_shadow import (
    gap_keep,
    repair_gap_coordinated_surface_subject,
)


CASES = {
    "b17-baseline",
    "gen-document-map",
    "hedged-perception",
}


EXPECTED = {
    "b17-baseline": [
        re.compile(
            r"\bsava\b.*\barriv",
            re.I,
        ),
    ],
    "gen-document-map": [
        re.compile(
            r"\bfold(?:s|ed|ing)?\b.*\bmap\b",
            re.I,
        ),
    ],
    "hedged-perception": [
        re.compile(
            r"\bwait(?:s|ed|ing)?\b",
            re.I,
        ),
    ],
}


DANGEROUS = [
    re.compile(
        r"\bmara\b.*\bwrit(?:e|es|ing|ten)\b.*\bb17\b",
        re.I,
    ),
]


def load_segment_state(
    book_id: int,
    seg_idx: int,
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
                s.tok_len,
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

        span_to_local = {
            row["span_id"]:
                int(row["local_no"])
            for row in span_rows
        }

        source_by_local = {
            int(row["local_no"]):
                row["text"]
            for row in span_rows
        }

        tok_by_local = {
            int(row["local_no"]):
                int(row["tok_len"])
            for row in span_rows
        }

        observation_rows = con.execute(
            """
            SELECT
                tag,
                payload,
                epistemic,
                spans,
                raw_line
            FROM observations
            WHERE book_id=?
              AND seg_id=?
              AND tag='EV'
            ORDER BY pos, id
            """,
            (
                book_id,
                seg["id"],
            ),
        ).fetchall()

    records = []

    for row in observation_rows:
        local_refs = []

        for span_id in (
            part.strip()
            for part in (
                row["spans"]
                or ""
            ).split(",")
            if part.strip()
        ):
            local_no = span_to_local.get(
                span_id
            )

            if local_no is not None:
                local_refs.append(
                    local_no
                )

        if not local_refs:
            continue

        records.append(
            Record(
                tag="EV",
                payload=row["payload"],
                spans=sorted(
                    set(local_refs)
                ),
                epistemic=(
                    row["epistemic"]
                    or "EXPLICIT"
                ),
                raw=(
                    row["raw_line"]
                    or ""
                ),
            )
        )

    parsed = Parsed(
        records=records,
        ignored=[],
        quarantined=[],
        stats={},
        contract_pass=True,
    )

    return (
        source_by_local,
        tok_by_local,
        parsed,
    )


def existing_by_local(
    parsed: Parsed,
):
    out = {}

    for record in parsed.records:
        if record.tag != "EV":
            continue

        for p in record.spans:
            out.setdefault(
                p,
                [],
            ).append(
                record.payload
            )

    return out


def build_segment_gap_messages(
    source_by_local,
    existing: Parsed,
):
    source_fragment = "\n\n".join(
        (
            f"[P{p:02}] "
            f"{source_by_local[p]}"
        )
        for p in sorted(
            source_by_local
        )
    )

    existing_map = existing_by_local(
        existing
    )

    existing_blocks = []

    for p in sorted(
        source_by_local
    ):
        payloads = existing_map.get(
            p,
            [],
        )

        lines = (
            "\n".join(
                f"EV: {payload} @P{p:02}"
                for payload in payloads
            )
            if payloads
            else "(none)"
        )

        existing_blocks.append(
            f"[P{p:02}]\n{lines}"
        )

    existing_fragment = (
        "\n\n".join(
            existing_blocks
        )
    )

    return [
        {
            "role": "system",
            "content": ACTION_GAP_SYSTEM,
        },
        {
            "role": "user",
            "content": (
                "Audit every SOURCE paragraph against "
                "its EXISTING EV records.\n"
                "Return ONLY missing explicit actions. "
                "Do not repeat represented actions.\n\n"
                "SOURCE:\n"
                + source_fragment
                + "\n\nEXISTING EV BY PARAGRAPH:\n"
                + existing_fragment
            ),
        },
    ]


def firewall_gap(
    parsed: Parsed,
    source_by_local,
    existing: Parsed,
):
    existing_map = existing_by_local(
        existing
    )

    kept = []
    decisions = []

    for record in parsed.records:
        if record.tag != "EV":
            decisions.append(
                (
                    record,
                    False,
                    "not-ev",
                )
            )
            continue

        if len(record.spans) != 1:
            decisions.append(
                (
                    record,
                    False,
                    "multi-span-abstain",
                )
            )
            continue

        p = record.spans[0]

        source = source_by_local.get(
            p,
            "",
        )

        existing_payloads = (
            existing_map.get(
                p,
                [],
            )
        )

        (
            repaired_payload,
            coordinated_surface_changed,
        ) = repair_gap_coordinated_surface_subject(
            record.payload,
            source,
        )

        if coordinated_surface_changed:
            record = Record(
                tag=record.tag,
                payload=repaired_payload,
                spans=list(record.spans),
                epistemic=record.epistemic,
                raw=record.raw,
            )

        keep, reason = gap_keep(
            record.payload,
            source,
            existing_payloads,
        )

        if coordinated_surface_changed:
            reason = (
                "surface-repaired+"
                + reason
            )

        decisions.append(
            (
                record,
                keep,
                reason,
            )
        )

        if keep:
            kept.append(
                record
            )

    stats = dict(
        parsed.stats
    )

    stats[
        "gap_firewall_kept"
    ] = len(kept)

    stats[
        "gap_firewall_dropped"
    ] = (
        len(parsed.records)
        - len(kept)
    )

    return (
        Parsed(
            records=kept,
            ignored=list(
                parsed.ignored
            ),
            quarantined=list(
                parsed.quarantined
            ),
            stats=stats,
            contract_pass=(
                parsed.contract_pass
            ),
        ),
        decisions,
    )


def main():
    init_db()

    llama = LlamaClient()

    health = llama.health()

    if not health.get("ok"):
        raise SystemExit(
            "llama-server is offline"
        )

    suite_id = (
        "gap-segment-shadow-"
        + str(time.time_ns())
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

    all_expected = True
    dangerous_survived = False

    print(
        "=== ACTION GAP SEGMENT SHADOW ==="
    )
    print(
        "suite_id:",
        suite_id,
    )

    for gold_path in paths:
        gold, _ = load_fixture(
            gold_path
        )

        case = gold["case"]

        # Run the current production pipeline first.
        item = run_fixture(
            gold_path,
            suite_id,
            verbose=False,
        )

        (
            source_by_local,
            _tok_by_local,
            existing,
        ) = load_segment_state(
            item["book_id"],
            gold.get(
                "segment_idx",
                1,
            ),
        )

        messages = (
            build_segment_gap_messages(
                source_by_local,
                existing,
            )
        )

        raw, elapsed = _extraction_chat(
            llama,
            messages,
        )

        parsed = parse_output(
            raw,
            set(
                source_by_local
            ),
            allowed_tags={"EV"},
            required_tags=set(),
            min_content=0,
        )

        # First reuse every ordinary ACTION precision guard.
        sanitized = (
            _sanitize_action_coverage(
                parsed,
                source_by_local,
                existing=existing,
            )
        )

        # Then apply stricter GAP-only novelty + role grounding.
        (
            accepted,
            decisions,
        ) = firewall_gap(
            sanitized,
            source_by_local,
            existing,
        )

        print()
        print(
            "=" * 110
        )
        print(
            case,
            "| current:",
            item["profile"],
            "| gap:",
            f"{elapsed:.2f}s",
        )
        print(
            "=" * 110
        )

        print()
        print(
            "RAW GAP:"
        )
        print(
            raw.strip()
            or "(empty)"
        )

        print()
        print(
            "SANITIZED + FIREWALL DECISIONS:"
        )

        if not decisions:
            print(
                "  (none)"
            )

        for record, keep, reason in decisions:
            flag = (
                "KEEP"
                if keep
                else "DROP"
            )

            spans = ",".join(
                f"P{x:02}"
                for x in record.spans
            )

            print(
                f"  {flag:4} "
                f"{spans:6} "
                f"{reason:28} "
                f"{record.payload}"
            )

        print()
        print(
            "ACCEPTED GAP:"
        )

        if not accepted.records:
            print(
                "  (none)"
            )

        for record in accepted.records:
            print(
                "  EV:",
                record.payload,
                "@",
                record.spans,
            )

        accepted_text = "\n".join(
            record.payload
            for record in accepted.records
        )

        expected_patterns = (
            EXPECTED.get(
                case,
                [],
            )
        )

        expected_hits = [
            bool(
                pattern.search(
                    accepted_text
                )
            )
            for pattern
            in expected_patterns
        ]

        case_ok = all(
            expected_hits
        )

        all_expected = (
            all_expected
            and case_ok
        )

        print()
        print(
            "EXPECTED RECOVERY:",
            (
                "PASS"
                if case_ok
                else "FAIL"
            ),
        )

        for pattern, hit in zip(
            expected_patterns,
            expected_hits,
        ):
            print(
                " ",
                "PASS" if hit else "FAIL",
                pattern.pattern,
            )

        for pattern in DANGEROUS:
            if pattern.search(
                accepted_text
            ):
                dangerous_survived = True

                print(
                    "  DANGER SURVIVED:",
                    pattern.pattern,
                )

    print()
    print(
        "=" * 110
    )
    print(
        "ALL EXPECTED RECOVERED:",
        all_expected,
    )
    print(
        "DANGEROUS SURVIVED:",
        dangerous_survived,
    )

    if (
        not all_expected
        or dangerous_survived
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
