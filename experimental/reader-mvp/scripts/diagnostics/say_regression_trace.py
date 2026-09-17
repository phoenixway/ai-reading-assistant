import runpy
import sys

import app.reader as reader


orig = reader._relocate_say_provenance


def traced(record, source_by_local_no):
    if getattr(record, "tag", None) != "SAY":
        return orig(
            record,
            source_by_local_no,
        )

    declared_evidence = reader._say_source_evidence(
        record,
        source_by_local_no,
    )

    repaired, relocated = orig(
        record,
        source_by_local_no,
    )

    final_evidence = reader._say_source_evidence(
        repaired,
        source_by_local_no,
    )

    print()
    print("### SAY CANDIDATE")
    print("payload:", record.payload)
    print("declared_spans:", record.spans)
    print("declared_evidence:", declared_evidence)
    print("relocated:", relocated)
    print("final_spans:", repaired.spans)
    print("final_evidence:", final_evidence)

    for p in sorted(source_by_local_no):
        print(
            f"source[{p}]:",
            source_by_local_no[p],
        )

    return repaired, relocated


reader._relocate_say_provenance = traced

sys.argv = [
    "scripts/benchmark_suite.py",
    "--case",
    "b17-baseline",
    "--case",
    "coreference-handoff",
    "--case",
    "gen-interrupted-dialogue",
]

runpy.run_path(
    "scripts/benchmark_suite.py",
    run_name="__main__",
)
