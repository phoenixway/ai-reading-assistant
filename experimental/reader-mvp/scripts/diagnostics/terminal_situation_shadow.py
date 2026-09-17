import json
import re
from pathlib import Path

from app.config import settings
from app.db import connect
from app.llama import LlamaClient
from scripts.score_smoke import (
    _latest_fixture_book,
    _match_patterns,
    score_book,
)


ROOT = Path("samples")


SYSTEM = """Derive ONLY the persistent terminal situation at the end of the supplied fiction segment.

OUTPUT
SITUATION: <one concise terminal world-state description>

RULES
- Reply with exactly one SITUATION line. No markdown or commentary.
- This is a TRANSITION STATE, not a summary of the last action.
- Describe concrete facts that remain true after all events in the segment have happened.
- Prefer persistent object state, containment, possession, storage, hiding, placement, retained evidence, unresolved physical condition, or an explicit final observed result.
- If an object was placed, hidden, returned, stored, retained, or left somewhere, preserve that resulting relation when it remains true at the segment boundary.
- If an observation or measurement establishes an explicit final result such as "no change", preserve that result.
- A character merely performing the final action is not by itself the terminal situation.
- Do not convert speech, claims, seeming, guesses, intentions, or hypotheses into world facts.
- Do not invent causal consequences.
- Later source statements override earlier incompatible states.
- Earlier paragraphs may establish an object or condition whose state persists through the final paragraph.
- The final substantive paragraph has highest temporal priority.
- Use only source-explicit facts.
- Keep the result concise, preferably <= 24 words.
"""


def story_paragraphs(text):
    return [
        part.strip()
        for part in re.split(
            r"\n\s*\n",
            text,
        )
        if part.strip()
    ]


def labelled_fragment(text):
    return "\n\n".join(
        f"[P{i:02}] {paragraph}"
        for i, paragraph in enumerate(
            story_paragraphs(text),
            start=1,
        )
    )


def parse_situation(output):
    for line in output.splitlines():
        match = re.match(
            r"^\s*SITUATION\s*:\s*(.+?)\s*$",
            line,
            re.I,
        )

        if match:
            return match.group(1).strip()

    return ""


def discover():
    paths = [
        ROOT / "smoke_gold.json",
    ]

    paths.extend(
        sorted(
            (ROOT / "benchmarks").glob(
                "*_gold.json"
            )
        )
    )

    return paths


llama = LlamaClient()

rows = []

for gold_path in discover():
    gold = json.loads(
        gold_path.read_text(
            encoding="utf-8"
        )
    )

    end_gold = gold.get("end", {})

    situation_patterns = end_gold.get(
        "situation_patterns",
        [],
    )

    if not situation_patterns:
        continue

    story_path = (
        ROOT / gold["story"]
    )

    story = story_path.read_text(
        encoding="utf-8"
    )

    with connect() as con:
        book_id = _latest_fixture_book(
            con,
            gold["fixture"],
        )

    current_score = score_book(
        book_id,
        gold_path,
    )

    current_end = (
        current_score["end"]["value"]
    )

    current_ok = (
        current_score["end"]["checks"]
        .get("situation", True)
    )

    messages = [
        {
            "role": "system",
            "content": SYSTEM,
        },
        {
            "role": "user",
            "content": (
                "CURRENT END CONTEXT\n"
                f"present={current_end.get('present', '')}\n"
                f"loc={current_end.get('loc', '')}\n\n"
                "SOURCE SEGMENT\n"
                + labelled_fragment(story)
            ),
        },
    ]

    output, elapsed = llama.chat(
        messages,
        temperature=settings.extraction_temperature,
        seed=settings.extraction_seed,
        cache_prompt=False,
    )

    situation = parse_situation(
        output
    )

    shadow_ok = (
        bool(situation)
        and _match_patterns(
            situation,
            situation_patterns,
        )
    )

    rows.append(
        {
            "case": gold["case"],
            "current_ok": current_ok,
            "shadow_ok": shadow_ok,
            "current": current_end.get(
                "situation",
                "",
            ),
            "shadow": situation,
            "gold": situation_patterns,
            "raw": output.strip(),
            "elapsed": elapsed,
        }
    )


print(
    f"{'CASE':28} "
    f"{'NOW':4} "
    f"{'SHADOW':6} "
    f"{'SEC':>5}"
)

print("-" * 48)

for row in rows:
    print(
        f"{row['case'][:28]:28} "
        f"{'OK' if row['current_ok'] else 'FAIL':4} "
        f"{'OK' if row['shadow_ok'] else 'FAIL':6} "
        f"{row['elapsed']:5.2f}"
    )


current_green = sum(
    row["current_ok"]
    for row in rows
)

shadow_green = sum(
    row["shadow_ok"]
    for row in rows
)

print()
print(
    "CURRENT SITUATION GREEN:",
    f"{current_green}/{len(rows)}",
)

print(
    "SHADOW SITUATION GREEN:",
    f"{shadow_green}/{len(rows)}",
)


print()
print("=" * 100)
print("DETAILS")
print("=" * 100)

for row in rows:
    print()
    print("=" * 100)
    print(row["case"])
    print("=" * 100)

    print(
        "CURRENT:",
        row["current"],
    )

    print(
        "CURRENT_OK:",
        row["current_ok"],
    )

    print(
        "SHADOW:",
        row["shadow"],
    )

    print(
        "SHADOW_OK:",
        row["shadow_ok"],
    )

    print(
        "GOLD PATTERNS:",
        row["gold"],
    )

    if not row["shadow"]:
        print(
            "RAW:",
            repr(row["raw"]),
        )
