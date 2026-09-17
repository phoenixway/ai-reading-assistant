import runpy
import sys

import app.reader as reader


# ============================================================
# Trace every LLM extraction call.
# ============================================================

_original_chat = reader._extraction_chat
chat_no = 0


def traced_chat(*args, **kwargs):
    global chat_no

    chat_no += 1

    result = _original_chat(
        *args,
        **kwargs,
    )

    output, elapsed = result

    messages = None

    if len(args) >= 2:
        messages = args[1]
    elif "messages" in kwargs:
        messages = kwargs["messages"]

    system = ""

    if messages:
        for message in messages:
            if message.get("role") == "system":
                system = message.get(
                    "content",
                    "",
                )
                break

    first_line = (
        system.strip().splitlines()[0]
        if system.strip()
        else "<no system>"
    )

    print()
    print("=" * 100)
    print(
        f"LLM CALL {chat_no}: "
        f"{first_line}"
    )
    print("=" * 100)
    print(output)
    print(
        f"--- elapsed={elapsed:.2f}s ---"
    )

    return result


reader._extraction_chat = traced_chat


# ============================================================
# Trace ACTION-COVERAGE before/after sanitizer.
# ============================================================

_original_action_sanitize = (
    reader._sanitize_action_coverage
)


def dump_records(label, parsed):
    print()
    print(label)

    for record in parsed.records:
        print(
            f"{record.tag}: "
            f"{record.payload} "
            f"@{record.spans} "
            f"[{record.epistemic}]"
        )


def traced_action_sanitize(
    parsed,
    source_by_local_no,
    existing=None,
):
    print()
    print("=" * 100)
    print("ACTION COVERAGE SOURCE")
    print("=" * 100)

    for p in sorted(source_by_local_no):
        print(
            f"[P{p:02}] "
            f"{source_by_local_no[p]}"
        )

    dump_records(
        "ACTION RAW:",
        parsed,
    )

    result = _original_action_sanitize(
        parsed,
        source_by_local_no,
        existing=existing,
    )

    dump_records(
        "ACTION SANITIZED:",
        result,
    )

    print()
    print(
        "ACTION SANITIZER STATS:",
        result.stats,
    )

    return result


reader._sanitize_action_coverage = (
    traced_action_sanitize
)


# ============================================================
# Trace final canonical Parsed before DB application.
# ============================================================

_original_apply = reader.apply_parsed


def traced_apply(
    con,
    book_id,
    seg,
    parsed,
    mapping,
):
    print()
    print("=" * 100)
    print("FINAL PARSED BEFORE LEDGER")
    print("=" * 100)

    dump_records(
        "FINAL RECORDS:",
        parsed,
    )

    return _original_apply(
        con,
        book_id,
        seg,
        parsed,
        mapping,
    )


reader.apply_parsed = traced_apply


sys.argv = [
    "scripts/benchmark_suite.py",
    "--case",
    "gen-epistemic-claim",
]

runpy.run_path(
    "scripts/benchmark_suite.py",
    run_name="__main__",
)
