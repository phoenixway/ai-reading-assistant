from __future__ import annotations

import re
import time

from app.db import init_db
from app.llama import LlamaClient
from app.protocol import (
    Parsed,
    merge_parsed,
    parse_output,
)
from app.reader import (
    _extraction_chat,
    _is_structural_paragraph,
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
from scripts.diagnostics.action_gap_segment_shadow import (
    existing_by_local,
    firewall_gap,
    load_segment_state,
)


CASES = {
    "b17-baseline",
    "gen-document-map",
    "hedged-perception",
}

BATCH_SIZE = 2


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
    (
        "Mara steals B17 writing",
        re.compile(
            r"\bmara\b.*\bwrit(?:e|es|ing|ten)\b.*\bb17\b",
            re.I,
        ),
    ),
]


def substantive_batches(
    source_by_local,
):
    local_nos = [
        p
        for p in sorted(
            source_by_local
        )
        if (
            source_by_local[p].strip()
            and not _is_structural_paragraph(
                source_by_local[p]
            )
        )
    ]

    return [
        local_nos[
            i:i + BATCH_SIZE
        ]
        for i in range(
            0,
            len(local_nos),
            BATCH_SIZE,
        )
    ]


def build_batch_messages(
    source_by_local,
    existing: Parsed,
    batch,
):
    existing_map = existing_by_local(
        existing
    )

    source_fragment = "\n\n".join(
        (
            f"[P{p:02}] "
            f"{source_by_local[p]}"
        )
        for p in batch
    )

    existing_blocks = []

    for p in batch:
        payloads = existing_map.get(
            p,
            [],
        )

        if payloads:
            body = "\n".join(
                f"EV: {payload} @P{p:02}"
                for payload in payloads
            )
        else:
            body = "(none)"

        existing_blocks.append(
            f"[P{p:02}]\n{body}"
        )

    return [
        {
            "role": "system",
            "content": ACTION_GAP_SYSTEM,
        },
        {
            "role": "user",
            "content": (
                "Audit each SOURCE paragraph against "
                "its EXISTING EV records.\n"
                "Return ONLY missing explicit actions. "
                "Do not repeat represented actions.\n\n"
                "SOURCE:\n"
                + source_fragment
                + "\n\n"
                "EXISTING EV BY PARAGRAPH:\n"
                + "\n\n".join(
                    existing_blocks
                )
            ),
        },
    ]


def main():
    init_db()

    llama = LlamaClient()

    health = llama.health()

    if not health.get("ok"):
        raise SystemExit(
            "llama-server is offline"
        )

    suite_id = (
        "gap-small-batch-shadow-"
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
        "=== ACTION GAP SMALL-BATCH SHADOW ==="
    )
    print(
        "suite_id:",
        suite_id,
    )
    print(
        "batch_size:",
        BATCH_SIZE,
    )

    for gold_path in paths:
        gold, _ = load_fixture(
            gold_path
        )

        case = gold["case"]

        # Current production state first.
        item = run_fixture(
            gold_path,
            suite_id,
            verbose=False,
        )

        (
            source_by_local,
            _tok_by_local,
            production_existing,
        ) = load_segment_state(
            item["book_id"],
            gold.get(
                "segment_idx",
                1,
            ),
        )

        working_existing = (
            production_existing
        )

        accepted_all = []

        print()
        print(
            "=" * 110
        )
        print(
            case,
            "| current:",
            item["profile"],
        )
        print(
            "=" * 110
        )

        batches = substantive_batches(
            source_by_local
        )

        print(
            "batches:",
            batches,
        )

        for batch_no, batch in enumerate(
            batches,
            1,
        ):
            batch_source = {
                p: source_by_local[p]
                for p in batch
            }

            messages = build_batch_messages(
                source_by_local,
                working_existing,
                batch,
            )

            raw, elapsed = (
                _extraction_chat(
                    llama,
                    messages,
                )
            )

            parsed = parse_output(
                raw,
                set(batch),
                allowed_tags={"EV"},
                required_tags=set(),
                min_content=0,
            )

            sanitized = (
                _sanitize_action_coverage(
                    parsed,
                    batch_source,
                    existing=working_existing,
                )
            )

            (
                accepted,
                decisions,
            ) = firewall_gap(
                sanitized,
                batch_source,
                working_existing,
            )

            print()
            print(
                "-" * 110
            )
            print(
                f"BATCH {batch_no}:",
                batch,
                f"{elapsed:.2f}s",
            )

            print()
            print(
                "RAW:"
            )
            print(
                raw.strip()
                or "(empty)"
            )

            print()
            print(
                "DECISIONS:"
            )

            if not decisions:
                print(
                    "  (none)"
                )

            for (
                record,
                keep,
                reason,
            ) in decisions:
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
                    f"{spans:8} "
                    f"{reason:28} "
                    f"{record.payload}"
                )

            if accepted.records:
                accepted_all.extend(
                    accepted.records
                )

                working_existing = (
                    merge_parsed(
                        [
                            working_existing,
                            accepted,
                        ],
                        True,
                    )
                )

        print()
        print(
            "ACCEPTED GAP FOR CASE:"
        )

        if not accepted_all:
            print(
                "  (none)"
            )

        for record in accepted_all:
            print(
                "  EV:",
                record.payload,
                "@",
                record.spans,
            )

        accepted_text = "\n".join(
            record.payload
            for record in accepted_all
        )

        expected_patterns = (
            EXPECTED.get(
                case,
                [],
            )
        )

        hits = [
            bool(
                pattern.search(
                    accepted_text
                )
            )
            for pattern
            in expected_patterns
        ]

        case_ok = all(
            hits
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
            hits,
        ):
            print(
                " ",
                "PASS" if hit else "FAIL",
                pattern.pattern,
            )

        for name, pattern in DANGEROUS:
            if pattern.search(
                accepted_text
            ):
                dangerous_survived = True

                print(
                    "DANGER SURVIVED:",
                    name,
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
