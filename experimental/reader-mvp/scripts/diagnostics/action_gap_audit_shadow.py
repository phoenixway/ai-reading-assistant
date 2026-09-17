from __future__ import annotations

from app.llama import LlamaClient
from app.protocol import Parsed, Record, parse_output
from app.reader import (
    ACTION_COVERAGE_SYSTEM,
    _extraction_chat,
    _sanitize_action_coverage,
)


ACTION_GAP_SYSTEM = (
    ACTION_COVERAGE_SYSTEM
    + """

ADDITIONAL ROLE: OMISSION AUDITOR

You are given SOURCE paragraphs plus EXISTING EV records that have
already been extracted from those paragraphs.

Output ONLY explicit narratively useful actions that are present in
SOURCE but are NOT already represented by the EXISTING EV records.

Audit exhaustively:
- sentence by sentence;
- clause by clause;
- including low-salience actions before, between, or after more
  important actions;
- including explicit waiting, arriving, leaving, opening, folding,
  taking, placing, moving, or similar physical actions when present.

Do NOT repeat an action merely because wording differs.
Do NOT enrich or rewrite an existing action.
Do NOT infer an action that is absent from SOURCE.
If every explicit useful action is already represented, emit nothing.

The normal EV formatting and grounding rules still apply.
"""
)


PROBES = [
    {
        "name": "sava-arrival",
        "p": 3,
        "source": (
            "The rain began after midnight. "
            "A courier named Sava arrived soaked through and handed "
            "Mara a narrow grey envelope. "
            "On the front someone had written B17 in blue pencil. "
            "Mara slipped it into her coat without opening it."
        ),
        "existing": [
            "Sava handed Mara a grey envelope",
            "Mara slipped the envelope into her coat",
        ],
    },
    {
        "name": "priya-fold-map",
        "p": 3,
        "source": (
            "Malik asked whether the culvert was safe. "
            "Priya answered, “We take the ridge.” "
            "She circled checkpoint C in red pencil and folded the map."
        ),
        "existing": [
            "She circled checkpoint C in red pencil",
        ],
    },
    {
        "name": "keva-waits",
        "p": 3,
        "source": (
            "Keva tilted her head as if she had heard a sound behind "
            "the door. "
            "She waited a few seconds, then walked to the platform. "
            "Rian later said, “She looked frightened to me,” "
            "but Keva said nothing."
        ),
        "existing": [
            "Keva tilted her head",
            "Keva walked to the platform",
        ],
    },
]


def existing_parsed(
    p: int,
    payloads: list[str],
) -> Parsed:
    return Parsed(
        records=[
            Record(
                tag="EV",
                payload=payload,
                spans=[p],
                epistemic="EXPLICIT",
                raw="",
            )
            for payload in payloads
        ],
        ignored=[],
        quarantined=[],
        stats={},
        contract_pass=True,
    )


def build_messages(
    p: int,
    source: str,
    existing: list[str],
):
    existing_text = "\n".join(
        f"EV: {payload} @P{p:02}"
        for payload in existing
    )

    return [
        {
            "role": "system",
            "content": ACTION_GAP_SYSTEM,
        },
        {
            "role": "user",
            "content": (
                "Audit SOURCE against EXISTING EV records. "
                "Return only missing explicit actions.\n\n"
                f"SOURCE:\n[P{p:02}] {source}\n\n"
                "EXISTING EV:\n"
                f"{existing_text}"
            ),
        },
    ]


def show_records(
    label: str,
    parsed: Parsed,
):
    print(label)

    if not parsed.records:
        print("  (none)")
        return

    for record in parsed.records:
        print(
            f"  {record.tag}: "
            f"{record.payload} "
            f"@{record.spans}"
        )


def main():
    llama = LlamaClient()

    health = llama.health()

    if not health.get("ok"):
        raise SystemExit(
            "llama-server is offline"
        )

    print(
        "=== ACTION GAP AUDIT SHADOW ==="
    )

    for probe in PROBES:
        name = probe["name"]
        p = probe["p"]
        source = probe["source"]
        existing = probe["existing"]

        print()
        print("=" * 100)
        print(name)
        print("=" * 100)

        print("SOURCE:")
        print(source)

        print()
        print("EXISTING:")
        for payload in existing:
            print(" ", payload)

        messages = build_messages(
            p,
            source,
            existing,
        )

        raw, elapsed = _extraction_chat(
            llama,
            messages,
        )

        print()
        print(
            f"RAW GAP ({elapsed:.2f}s):"
        )
        print(
            raw.strip()
            or "(empty)"
        )

        parsed = parse_output(
            raw,
            {p},
            allowed_tags={"EV"},
            required_tags=set(),
            min_content=0,
        )

        show_records(
            "\nPARSED GAP:",
            parsed,
        )

        existing_obj = existing_parsed(
            p,
            existing,
        )

        clean = _sanitize_action_coverage(
            parsed,
            {
                p: source,
            },
            existing=existing_obj,
        )

        show_records(
            "\nSANITIZED GAP:",
            clean,
        )

        print()
        print(
            "STATS:",
            {
                key: value
                for key, value
                in clean.stats.items()
                if (
                    "dropped" in key
                    or "repaired" in key
                    or "bridged" in key
                    or "extended" in key
                    or "trimmed" in key
                )
            },
        )


if __name__ == "__main__":
    main()
