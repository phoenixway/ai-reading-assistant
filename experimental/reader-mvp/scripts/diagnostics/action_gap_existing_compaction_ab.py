from __future__ import annotations

import re

from app.llama import LlamaClient
from app.reader import (
    ACTION_GAP_SYSTEM,
    _extraction_chat,
)


SOURCE = (
    "[P02] Priya unfolded a survey map across the truck hood. "
    "Along the northern margin, blue-pencil words said: "
    "“North culvert blocked. Use ridge path.” "
    "Priya traced the ridge path with one finger.\n\n"
    "[P03] Malik asked whether the culvert was safe. "
    "Priya answered, “We take the ridge.” "
    "She circled checkpoint C in red pencil and folded the map."
)


EXACT_PRODUCTION_EXISTING = """[P02]
EV: Priya unfolded a survey map @P02
EV: Priya unfolded a survey map across the truck hood @P02
EV: Priya traced the ridge path with one finger @P02

[P03]
EV: She circled checkpoint C in red pencil @P03"""


COMPACT_EXISTING = """[P02]
EV: Priya unfolded a survey map across the truck hood @P02
EV: Priya traced the ridge path with one finger @P02

[P03]
EV: She circled checkpoint C in red pencil @P03"""


def build_user(existing: str):
    return (
        "Audit each SOURCE paragraph against its EXISTING EV records.\n"
        "Return ONLY missing explicit actions. "
        "Do not repeat represented actions.\n\n"
        "SOURCE:\n"
        + SOURCE
        + "\n\n"
        "EXISTING EV BY PARAGRAPH:\n"
        + existing
    )


def has_exact_fold(raw: str):
    return bool(
        re.search(
            r"\bfold(?:s|ed|ing)?\b",
            raw,
            re.I,
        )
    )


def run(
    llama,
    label,
    existing,
):
    messages = [
        {
            "role": "system",
            "content": ACTION_GAP_SYSTEM,
        },
        {
            "role": "user",
            "content": build_user(
                existing
            ),
        },
    ]

    raw, elapsed = _extraction_chat(
        llama,
        messages,
    )

    print()
    print("=" * 100)
    print(
        label,
        f"{elapsed:.2f}s",
    )
    print("=" * 100)

    print(
        raw.strip()
        or "(empty)"
    )

    recovered = has_exact_fold(
        raw
    )

    print()
    print(
        "EXACT FOLD RECOVERED:",
        recovered,
    )

    return recovered


def main():
    llama = LlamaClient()

    if not llama.health().get("ok"):
        raise SystemExit(
            "llama-server offline"
        )

    print(
        "=== GAP EXISTING-CONTEXT COMPACTION A/B ==="
    )

    a = run(
        llama,
        "A: EXACT PRODUCTION EXISTING",
        EXACT_PRODUCTION_EXISTING,
    )

    b = run(
        llama,
        "B: REDUNDANT EV REMOVED",
        COMPACT_EXISTING,
    )

    print()
    print("=" * 100)
    print("RESULT")
    print("=" * 100)
    print(
        "exact production:",
        "PASS" if a else "FAIL",
    )
    print(
        "compacted:       ",
        "PASS" if b else "FAIL",
    )


if __name__ == "__main__":
    main()
