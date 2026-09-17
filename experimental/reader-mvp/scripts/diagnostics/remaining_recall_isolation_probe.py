from __future__ import annotations

import re

from app.llama import LlamaClient
from app.protocol import (
    Parsed,
    Record,
    parse_output,
)
from app.reader import (
    _build_action_coverage_messages,
    _build_document_content_messages,
    _extraction_chat,
    _sanitize_action_coverage,
    _sanitize_say_coverage,
    _say_source_evidence,
)
from scripts.benchmark_suite import (
    discover_gold_paths,
    load_fixture,
)


PROBES = {
    "b17-baseline": {
        "action": [3],
        "document": [6],
    },
    "gen-document-map": {
        "action": [3],
    },
    "hedged-perception": {
        "action": [3],
    },
}


def paragraphs(text):
    return [
        p.strip()
        for p in re.split(
            r"\n\s*\n",
            text,
        )
        if p.strip()
    ]


def fixture_source():
    out = {}

    for gold_path in discover_gold_paths():
        gold, story_path = load_fixture(
            gold_path
        )

        if gold["case"] not in PROBES:
            continue

        out[gold["case"]] = {
            "gold": gold,
            "paragraphs": paragraphs(
                story_path.read_text(
                    encoding="utf-8"
                )
            ),
        }

    return out


def show_records(parsed):
    if not parsed.records:
        print("  (none)")
        return

    for record in parsed.records:
        print(
            f"  {record.tag}: "
            f"{record.payload} "
            f"@{record.spans}"
        )


def action_probe(
    llama,
    case,
    p,
    source,
):
    print()
    print("=" * 100)
    print(
        f"ACTION ISOLATED | {case} | P{p:02}"
    )
    print("=" * 100)
    print(source)
    print()

    target = {
        "local_no": p,
        "tok_len": len(
            source.split()
        ),
        "text": source,
    }

    messages = (
        _build_action_coverage_messages(
            [target]
        )
    )

    raw, elapsed = _extraction_chat(
        llama,
        messages,
    )

    print(
        f"RAW ({elapsed:.2f}s):"
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

    print()
    print("PARSED:")
    show_records(parsed)

    clean = _sanitize_action_coverage(
        parsed,
        {
            p: source,
        },
        existing=None,
    )

    print()
    print("SANITIZED:")
    show_records(clean)

    print()
    print(
        "SANITIZER STATS:",
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


def document_probe(
    llama,
    case,
    p,
    source,
):
    print()
    print("=" * 100)
    print(
        f"DOCUMENT ISOLATED | {case} | P{p:02}"
    )
    print("=" * 100)
    print(source)
    print()

    target = {
        "local_no": p,
        "tok_len": len(
            source.split()
        ),
        "text": source,
    }

    messages = (
        _build_document_content_messages(
            [target]
        )
    )

    raw, elapsed = _extraction_chat(
        llama,
        messages,
    )

    print(
        f"RAW ({elapsed:.2f}s):"
    )
    print(
        raw.strip()
        or "(empty)"
    )

    parsed = parse_output(
        raw,
        {p},
        allowed_tags={"DET"},
        required_tags=set(),
        min_content=0,
    )

    print()
    print("PARSED:")
    show_records(parsed)


def say_probe():
    print()
    print("=" * 100)
    print("SAY VERIFIER PROBE")
    print("=" * 100)

    probes = [
        (
            "father-welded FAIL",
            2,
            (
                "Mara had told Levin twice that the eastern stair "
                "was sealed. On the third evening she found him "
                "testing the brass handle anyway. "
                "“My father welded it shut before he died,” she said. "
                "Levin stepped back, embarrassed, and apologized."
            ),
            (
                "Mara | "
                "“My father welded it shut before he died”"
            ),
        ),
        (
            "Rian direct-speech PASS",
            3,
            (
                "Keva tilted her head as if she had heard a sound "
                "behind the door. She waited a few seconds, then "
                "walked to the platform. Rian later said, "
                "“She looked frightened to me,” but Keva said nothing."
            ),
            (
                "Rian | "
                "“She looked frightened to me,”"
            ),
        ),
        (
            "Mira postquote PASS",
            3,
            (
                "Mira read the warning silently, copied 02:10 into "
                "her notebook, and folded the report in half. "
                "Jonas asked what it said. "
                "“It says we wait for the mechanic,” Mira replied."
            ),
            (
                "Mira | "
                "It says we wait for the mechanic"
            ),
        ),
    ]

    for name, p, source, payload in probes:
        record = Record(
            tag="SAY",
            payload=payload,
            spans=[p],
            epistemic="EXPLICIT",
            raw="",
        )

        evidence = _say_source_evidence(
            record,
            {
                p: source,
            },
        )

        parsed = Parsed(
            records=[record],
            ignored=[],
            quarantined=[],
            stats={},
            contract_pass=True,
        )

        clean = _sanitize_say_coverage(
            parsed,
            {
                p: source,
            },
        )

        print()
        print(name)
        print(
            "  payload: ",
            payload,
        )
        print(
            "  evidence:",
            evidence,
        )
        print(
            "  kept:    ",
            bool(clean.records),
        )
        print(
            "  stats:   ",
            {
                key: value
                for key, value
                in clean.stats.items()
                if key.startswith(
                    "say_"
                )
            },
        )


def main():
    llama = LlamaClient()

    health = llama.health()

    if not health.get("ok"):
        raise SystemExit(
            "llama-server is offline"
        )

    fixtures = fixture_source()

    # --------------------------------------------------------
    # Offline precision diagnosis first.
    # --------------------------------------------------------
    say_probe()

    # --------------------------------------------------------
    # Isolated coverage calls.
    # --------------------------------------------------------
    for case, config in PROBES.items():
        fixture = fixtures[case]
        ps = fixture["paragraphs"]

        for p in config.get(
            "action",
            [],
        ):
            action_probe(
                llama,
                case,
                p,
                ps[p - 1],
            )

        for p in config.get(
            "document",
            [],
        ):
            document_probe(
                llama,
                case,
                p,
                ps[p - 1],
            )


if __name__ == "__main__":
    main()
