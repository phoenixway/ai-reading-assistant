from __future__ import annotations

from app.llama import LlamaClient
from app.protocol import Parsed, Record, parse_output
from app.reader import (
    ACTION_GAP_SYSTEM as PROD_GAP_SYSTEM,
    _extraction_chat,
    _sanitize_action_coverage,
    _sanitize_action_gap,
)
from scripts.diagnostics.action_gap_audit_shadow import (
    ACTION_GAP_SYSTEM as OLD_SHADOW_GAP_SYSTEM,
)


SOURCE = {
    2: (
        "Priya unfolded a survey map across the truck hood. "
        "Along the northern margin, blue-pencil words said: "
        "“North culvert blocked. Use ridge path.” "
        "Priya traced the ridge path with one finger."
    ),
    3: (
        "Malik asked whether the culvert was safe. "
        "Priya answered, “We take the ridge.” "
        "She circled checkpoint C in red pencil and folded the map."
    ),
}


EXISTING = Parsed(
    records=[
        Record(
            tag="EV",
            payload="Priya unfolded a survey map across the truck hood",
            spans=[2],
            epistemic="EXPLICIT",
            raw="",
        ),
        Record(
            tag="EV",
            payload="Priya traced the ridge path with one finger",
            spans=[2],
            epistemic="EXPLICIT",
            raw="",
        ),
        Record(
            tag="EV",
            payload="She circled checkpoint C in red pencil",
            spans=[3],
            epistemic="EXPLICIT",
            raw="",
        ),
    ],
    ignored=[],
    quarantined=[],
    stats={},
    contract_pass=True,
)


GENERIC_COMPLETENESS_ADDENDUM = """

ADDITIONAL COMPLETENESS RULE

Treat each explicit predicate in a coordinated or sequential clause
as an independent audit candidate.

If one action from a sentence is already represented in EXISTING EV,
inspect the remaining coordinated or sequential predicates separately.

Low narrative salience is not a reason to omit an explicit action.
Physical changes to an object's state, configuration, possession,
position, or location are actions even when they are brief or mundane.

Do not infer missing predicates or actors. This rule only increases
attention to predicates literally present in SOURCE.
"""


GENERIC_GAP_SYSTEM = (
    PROD_GAP_SYSTEM
    + GENERIC_COMPLETENESS_ADDENDUM
)


def build_user():
    return (
        "Audit each SOURCE paragraph against its EXISTING EV records.\n"
        "Return ONLY missing explicit actions. "
        "Do not repeat represented actions.\n\n"
        "SOURCE:\n"
        f"[P02] {SOURCE[2]}\n\n"
        f"[P03] {SOURCE[3]}\n\n"
        "EXISTING EV BY PARAGRAPH:\n"
        "[P02]\n"
        "EV: Priya unfolded a survey map across the truck hood @P02\n"
        "EV: Priya traced the ridge path with one finger @P02\n\n"
        "[P03]\n"
        "EV: She circled checkpoint C in red pencil @P03"
    )


def run_one(
    llama: LlamaClient,
    name: str,
    system_prompt: str,
):
    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": build_user(),
        },
    ]

    raw, elapsed = _extraction_chat(
        llama,
        messages,
    )

    parsed = parse_output(
        raw,
        {2, 3},
        allowed_tags={"EV"},
        required_tags=set(),
        min_content=0,
    )

    ordinary = _sanitize_action_coverage(
        parsed,
        SOURCE,
        existing=EXISTING,
    )

    final = _sanitize_action_gap(
        ordinary,
        SOURCE,
        existing=EXISTING,
    )

    print()
    print("=" * 100)
    print(name, f"{elapsed:.2f}s")
    print("=" * 100)

    print("\nRAW:")
    print(
        raw.strip()
        or "(empty)"
    )

    print("\nAFTER ORDINARY ACTION SANITIZER:")
    if ordinary.records:
        for record in ordinary.records:
            print(
                f"  EV: {record.payload} "
                f"@{record.spans}"
            )
    else:
        print("  (none)")

    print("\nAFTER GAP FIREWALL:")
    if final.records:
        for record in final.records:
            print(
                f"  EV: {record.payload} "
                f"@{record.spans}"
            )
    else:
        print("  (none)")

    has_fold = any(
        "fold" in record.payload.casefold()
        for record in final.records
    )

    print(
        "\nFOLD RECOVERED:",
        has_fold,
    )

    return has_fold


def main():
    llama = LlamaClient()

    health = llama.health()

    if not health.get("ok"):
        raise SystemExit(
            "llama-server is offline"
        )

    print(
        "=== ACTION GAP PROMPT A/B/C ==="
    )

    results = {}

    results["A production"] = run_one(
        llama,
        "A: CURRENT PRODUCTION",
        PROD_GAP_SYSTEM,
    )

    results["B old shadow"] = run_one(
        llama,
        "B: OLD SHADOW WITH VERB EXAMPLES",
        OLD_SHADOW_GAP_SYSTEM,
    )

    results["C generic"] = run_one(
        llama,
        "C: GENERIC CLAUSE-COMPLETENESS",
        GENERIC_GAP_SYSTEM,
    )

    print()
    print("=" * 100)
    print("RESULT")
    print("=" * 100)

    for name, value in results.items():
        print(
            f"{name:20} "
            f"{'PASS' if value else 'FAIL'}"
        )


if __name__ == "__main__":
    main()
