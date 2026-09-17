import runpy
import sys

import app.reader as reader


orig = reader._sanitize_action_coverage


def dump_records(label, parsed):
    print()
    print(label)

    for record in parsed.records:
        print(
            record.tag,
            "|",
            record.payload,
            "| spans=",
            record.spans,
            "| epistemic=",
            record.epistemic,
        )


def traced(
    parsed,
    source_by_local_no,
    existing=None,
):
    print()
    print("=" * 88)
    print("ACTION COVERAGE TRACE")
    print("=" * 88)

    print()
    print("SOURCE:")

    for p in sorted(source_by_local_no):
        print(
            f"[P{p:02}]",
            source_by_local_no[p],
        )

    dump_records(
        "RAW COVERAGE RECORDS:",
        parsed,
    )

    clean = orig(
        parsed,
        source_by_local_no,
        existing=existing,
    )

    dump_records(
        "SANITIZED COVERAGE RECORDS:",
        clean,
    )

    print()
    print("SANITIZER STATS:")
    print(clean.stats)

    print("=" * 88)

    return clean


reader._sanitize_action_coverage = traced

sys.argv = [
    "scripts/benchmark_suite.py",
    "--case",
    "gen-ambiguous-pronoun",
]

runpy.run_path(
    "scripts/benchmark_suite.py",
    run_name="__main__",
)
