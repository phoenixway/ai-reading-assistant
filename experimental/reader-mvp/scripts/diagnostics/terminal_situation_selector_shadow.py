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


SYSTEM = """Select evidence for the persistent terminal situation at the segment boundary.

OUTPUT EXACTLY ONE OF:

KEEP

or

SELECT: E01,E02

RULES
- Never write or paraphrase a situation.
- You may ONLY select supplied evidence IDs.
- KEEP means the CURRENT SITUATION is already the best supported terminal state.
- Prefer KEEP when current situation already preserves concrete persistent state useful for the next segment.
- Otherwise select 1 to 3 evidence records whose explicit effects remain true after the segment ends.
- Prefer:
  * placement / storage / hiding / containment
  * possession
  * object open/closed state
  * retained evidence
  * explicit final measurement/result
  * final location/state when it is itself salient
- Prefer later evidence over earlier incompatible evidence.
- Do not select speech, claims, guesses, seeming, intentions, or hypotheses as world facts.
- Do not infer new facts.
- Do not resolve ambiguous pronouns.
- Do not select a mere transient action if a later persistent result exists.
"""


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


def factual_memory(book_id, seg_id):
    with connect() as con:
        rows = con.execute(
            """
            SELECT
                id,
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
            "db_id": row["id"],
            "tag": row["tag"],
            "payload": row["payload"],
            "pos": row["pos"],
            "spans": row["spans"],
        }
        for row in rows
    ]


def parse_choice(output, valid_ids):
    text = output.strip()

    if re.fullmatch(
        r"KEEP",
        text,
        re.I,
    ):
        return ("KEEP", [])

    match = re.fullmatch(
        r"SELECT\s*:\s*(E\d{2}(?:\s*,\s*E\d{2}){0,2})",
        text,
        re.I,
    )

    if not match:
        return ("INVALID", [])

    ids = [
        token.strip().upper()
        for token in match.group(1).split(",")
    ]

    if (
        len(ids) != len(set(ids))
        or any(
            item not in valid_ids
            for item in ids
        )
    ):
        return ("INVALID", [])

    return ("SELECT", ids)


def render_selection(
    mode,
    selected_ids,
    current,
    indexed,
):
    if mode == "KEEP":
        return current

    if mode != "SELECT":
        return ""

    return "; ".join(
        indexed[item]["payload"]
        for item in selected_ids
    )


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

    current = (
        scored["end"]["value"]
        .get(
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

    indexed = {}

    lines = []

    for idx, item in enumerate(
        memory,
        start=1,
    ):
        evidence_id = f"E{idx:02}"

        indexed[evidence_id] = item

        lines.append(
            f"{evidence_id} "
            f"{item['tag']}: "
            f"{item['payload']}"
        )

    evidence_text = (
        "\n".join(lines)
        if lines
        else "(none)"
    )

    messages = [
        {
            "role": "system",
            "content": SYSTEM,
        },
        {
            "role": "user",
            "content": (
                "CURRENT SITUATION\n"
                f"{current or '(none)'}\n\n"
                "CANONICAL EVIDENCE\n"
                f"{evidence_text}"
            ),
        },
    ]

    output, elapsed = llama.chat(
        messages,
        temperature=settings.extraction_temperature,
        seed=settings.extraction_seed,
        cache_prompt=False,
    )

    mode, selected_ids = parse_choice(
        output,
        set(indexed),
    )

    rendered = render_selection(
        mode,
        selected_ids,
        current,
        indexed,
    )

    shadow_ok = (
        bool(rendered)
        and _match_patterns(
            rendered,
            patterns,
        )
    )

    rows.append(
        {
            "case": gold["case"],
            "current": current,
            "current_ok": current_ok,
            "mode": mode,
            "ids": selected_ids,
            "rendered": rendered,
            "shadow_ok": shadow_ok,
            "gold": patterns,
            "raw": output.strip(),
            "memory": memory,
            "indexed": indexed,
            "elapsed": elapsed,
        }
    )


print(
    f"{'CASE':28} "
    f"{'NOW':4} "
    f"{'SELECT':6} "
    f"{'MODE':7} "
    f"{'SEC':>5}"
)

print("-" * 58)

for row in rows:
    print(
        f"{row['case'][:28]:28} "
        f"{'OK' if row['current_ok'] else 'FAIL':4} "
        f"{'OK' if row['shadow_ok'] else 'FAIL':6} "
        f"{row['mode'][:7]:7} "
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

repairs = [
    row["case"]
    for row in rows
    if (
        not row["current_ok"]
        and row["shadow_ok"]
    )
]

regressions = [
    row["case"]
    for row in rows
    if (
        row["current_ok"]
        and not row["shadow_ok"]
    )
]

invalid = [
    row["case"]
    for row in rows
    if row["mode"] == "INVALID"
]


print()
print(
    "CURRENT GREEN:",
    f"{current_green}/{len(rows)}",
)

print(
    "SELECTOR GREEN:",
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

print(
    "INVALID:",
    invalid,
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
        "CHOICE:",
        row["raw"],
    )

    print(
        "MODE:",
        row["mode"],
    )

    print(
        "IDS:",
        row["ids"],
    )

    if row["ids"]:
        print()
        print("SELECTED EVIDENCE:")

        for evidence_id in row["ids"]:
            item = row["indexed"][
                evidence_id
            ]

            print(
                f"  {evidence_id} "
                f"{item['tag']}: "
                f"{item['payload']}"
            )

    print()
    print(
        "RENDERED:",
        row["rendered"],
    )

    print(
        "SELECTOR_OK:",
        row["shadow_ok"],
    )

    print(
        "GOLD:",
        row["gold"],
    )
