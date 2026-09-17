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


SYSTEM = """Derive ONLY the persistent terminal situation at the segment boundary.

OUTPUT
SITUATION: <one concise terminal world-state description>

EVIDENCE CONTRACT
- Use ONLY CURRENT SITUATION and CANONICAL FACTUAL MEMORY supplied below.
- The raw story is intentionally unavailable.
- Do not invent facts beyond that evidence.
- Do not reconstruct speech, claims, guesses, seeming, intentions, or hypotheses.
- CANONICAL FACTUAL MEMORY has already passed extraction and epistemic filtering.

SEMANTICS
- This is a terminal WORLD STATE, not a summary of the final action.
- Prefer facts that remain true after the listed actions have completed.
- Convert explicit placement/storage actions into their resulting persistent relation:
    "X placed map in pack" -> map is in pack
    "X returned ledger to cabinet" -> ledger is in cabinet
    "X hid key in boot" -> key is in boot
- Preserve explicit terminal measurement/result facts:
    "found no change" -> no change remains the observed result
- Preserve persistent possession, containment, storage, hiding, retained evidence,
  open/closed state, or unresolved physical condition.
- Later canonical facts override earlier incompatible facts.
- Do not drop a concrete persistent fact already present in CURRENT SITUATION
  merely to make the answer shorter, unless later canonical evidence contradicts it.
- CURRENT SITUATION may be phrased as actions. Preserve its concrete resulting facts
  while rewriting them as terminal state.
- A departure, arrival, phone call, measurement, or other action is not by itself
  the terminal situation unless it establishes a persistent state.
- Do not add character identity/coreference that is not already explicit in evidence.
- Keep enough object/container/result detail to make the state useful for the next segment.
- Prefer <= 30 words.
"""


def parse_situation(output):
    for line in output.splitlines():
        m = re.match(
            r"^\s*SITUATION\s*:\s*(.+?)\s*$",
            line,
            re.I,
        )

        if m:
            return m.group(1).strip()

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


def factual_memory(
    book_id,
    seg_id,
):
    with connect() as con:
        rows = con.execute(
            """
            SELECT
                tag,
                payload,
                epistemic,
                pos,
                spans
            FROM observations
            WHERE book_id=?
              AND seg_id=?
              AND tag IN ('EV', 'DET', 'ST')
              AND epistemic='EXPLICIT'
            ORDER BY pos, id
            """,
            (
                book_id,
                seg_id,
            ),
        ).fetchall()

    return [
        {
            "tag": row["tag"],
            "payload": row["payload"],
            "pos": row["pos"],
            "spans": row["spans"],
        }
        for row in rows
    ]


llama = LlamaClient()
rows = []


for gold_path in discover():
    gold = json.loads(
        gold_path.read_text(
            encoding="utf-8"
        )
    )

    patterns = (
        gold.get("end", {})
        .get(
            "situation_patterns",
            [],
        )
    )

    if not patterns:
        continue

    with connect() as con:
        book_id = _latest_fixture_book(
            con,
            gold["fixture"],
        )

    scored = score_book(
        book_id,
        gold_path,
    )

    seg_id = scored["segment"]

    current_end = (
        scored["end"]["value"]
    )

    current = (
        current_end.get(
            "situation",
            "",
        )
        or ""
    )

    current_ok = (
        scored["end"]["checks"]
        .get(
            "situation",
            True,
        )
    )

    memory = factual_memory(
        book_id,
        seg_id,
    )

    memory_text = "\n".join(
        (
            f"{item['tag']}: "
            f"{item['payload']}"
            + (
                f" [{item['spans']}]"
                if item["spans"]
                else ""
            )
        )
        for item in memory
    )

    if not memory_text:
        memory_text = "(none)"

    messages = [
        {
            "role": "system",
            "content": SYSTEM,
        },
        {
            "role": "user",
            "content": (
                "CURRENT SITUATION\n"
                + (
                    current
                    if current
                    else "(none)"
                )
                + "\n\n"
                "CANONICAL FACTUAL MEMORY\n"
                + memory_text
            ),
        },
    ]

    output, elapsed = llama.chat(
        messages,
        temperature=settings.extraction_temperature,
        seed=settings.extraction_seed,
        cache_prompt=False,
    )

    shadow = parse_situation(
        output
    )

    shadow_ok = (
        bool(shadow)
        and _match_patterns(
            shadow,
            patterns,
        )
    )

    rows.append(
        {
            "case": gold["case"],
            "current": current,
            "current_ok": current_ok,
            "shadow": shadow,
            "shadow_ok": shadow_ok,
            "gold": patterns,
            "memory": memory,
            "raw": output.strip(),
            "elapsed": elapsed,
        }
    )


print(
    f"{'CASE':28} "
    f"{'NOW':4} "
    f"{'LEDGER':6} "
    f"{'SEC':>5}"
)

print("-" * 49)

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

regressions = [
    row["case"]
    for row in rows
    if (
        row["current_ok"]
        and not row["shadow_ok"]
    )
]

repairs = [
    row["case"]
    for row in rows
    if (
        not row["current_ok"]
        and row["shadow_ok"]
    )
]


print()
print(
    "CURRENT SITUATION GREEN:",
    f"{current_green}/{len(rows)}",
)

print(
    "LEDGER SHADOW GREEN:",
    f"{shadow_green}/{len(rows)}",
)

print(
    "REPAIRS:",
    repairs,
)

print(
    "REGRESSIONS:",
    regressions,
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

    print()
    print("CANONICAL FACTUAL MEMORY:")

    for item in row["memory"]:
        print(
            f"  {item['tag']}: "
            f"{item['payload']}"
        )

    print()
    print(
        "LEDGER SHADOW:",
        row["shadow"],
    )

    print(
        "LEDGER_OK:",
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
