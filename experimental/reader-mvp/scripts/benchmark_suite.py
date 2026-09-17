"""Run the synthetic narrative-memory benchmark suite."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings
from app.db import init_db
from app.ingest import ingest_text
from app.llama import LlamaClient
from app.protocol import DEVELOPER_FAST
from app.reader import analyze_next
from scripts.score_smoke import score_book


SAMPLES = ROOT / "samples"


def discover_gold_paths() -> list[Path]:
    paths = [SAMPLES / "smoke_gold.json"]
    paths.extend(sorted((SAMPLES / "benchmarks").glob("*_gold.json")))
    return paths


def load_fixture(gold_path: Path) -> tuple[dict, Path]:
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    story = gold.get("story")

    if not story:
        raise ValueError(f"{gold_path}: missing 'story'")

    story_path = SAMPLES / story

    if not story_path.exists():
        raise FileNotFoundError(story_path)

    return gold, story_path


def run_fixture(
    gold_path: Path,
    suite_id: str,
    *,
    verbose: bool = False,
) -> dict:
    gold, story_path = load_fixture(gold_path)

    text = story_path.read_text(encoding="utf-8")
    source_ref = f"{suite_id}:{gold['case']}"

    book_id = ingest_text(
        gold["fixture"],
        text,
        author="OpenAI synthetic benchmark fixture",
        source_type="benchmark",
        source_ref=source_ref,
    )

    result = analyze_next(book_id)
    score = score_book(book_id, gold_path)

    item = {
        "case": gold["case"],
        "fixture": gold["fixture"],
        "focus": gold.get("focus", []),
        "gold": str(gold_path.relative_to(ROOT)),
        "story": str(story_path.relative_to(ROOT)),
        "book_id": book_id,
        "profile": result.get("profile"),
        "contract_pass": result.get("contract_pass"),
        "elapsed": result.get("elapsed"),
        "attempts": result.get("attempts", []),
        "scores": score["scores"],
        "required": score["required"],
        "forbidden": score["forbidden"],
        "end": score["end"],
        "paragraph_coverage": score["paragraph_coverage"],
    }

    if verbose:
        item["raw_output"] = result.get("output", "")

    return item


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--case",
        action="append",
        help="Run only this case id. May be repeated.",
    )
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    init_db()

    health = LlamaClient().health()
    if not health.get("ok"):
        raise SystemExit(
            "llama-server is offline; start it first"
        )

    suite_id = f"suite-{time.time_ns()}"
    prompt_sha = hashlib.sha256(
        DEVELOPER_FAST.encode("utf-8")
    ).hexdigest()

    fixtures = []
    selected = set(args.case or [])

    for gold_path in discover_gold_paths():
        gold, _ = load_fixture(gold_path)

        if selected and gold["case"] not in selected:
            continue

        fixtures.append(
            run_fixture(
                gold_path,
                suite_id,
                verbose=args.verbose,
            )
        )

    if not fixtures:
        raise SystemExit("No benchmark fixtures selected")

    metric_names = [
        "semantic_coverage",
        "grounded_coverage",
        "forbidden_pass",
        "end_pass",
        "overall",
    ]

    macro = {
        name: statistics.fmean(
            x["scores"][name]
            for x in fixtures
        )
        for name in metric_names
    }

    elapsed_total = sum(
        float(x["elapsed"] or 0)
        for x in fixtures
    )

    report = {
        "suite_id": suite_id,
        "prompt_sha256": prompt_sha,
        "sampling": {
            "extraction_temperature": settings.extraction_temperature,
            "extraction_seed": settings.extraction_seed,
            "cache_prompt": False,
        },
        "llama": health,
        "fixtures": fixtures,
        "macro": macro,
        "elapsed_total": elapsed_total,
    }

    if args.json:
        print(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    print("=== NARRATIVE MEMORY BENCHMARK ===")
    print("suite_id:", suite_id)
    print("prompt_sha256:", prompt_sha)
    print(
        "extraction_sampling:",
        f"temperature={settings.extraction_temperature}",
        f"seed={settings.extraction_seed}",
        "cache_prompt=False",
    )
    print("fixtures:", len(fixtures))
    print()

    print(
        "CASE".ljust(25),
        "PROFILE".ljust(26),
        "SEM",
        "GRD",
        "FORB",
        "END",
        "ALL",
        "SEC",
    )

    for item in fixtures:
        s = item["scores"]

        print(
            item["case"].ljust(25),
            str(item["profile"]).ljust(26),
            f"{s['semantic_coverage']:.3f}",
            f"{s['grounded_coverage']:.3f}",
            f"{s['forbidden_pass']:.3f}",
            f"{s['end_pass']:.3f}",
            f"{s['overall']:.3f}",
            f"{float(item['elapsed'] or 0):.2f}",
        )

    print()
    print("=== MACRO ===")

    for name in metric_names:
        print(f"{name}: {macro[name]:.3f}")

    print(f"elapsed_total: {elapsed_total:.2f}s")

    print()
    print("=== FAILURES ===")

    any_failure = False

    for item in fixtures:
        misses = [
            x["id"]
            for x in item["required"]
            if not x["provenance"]
        ]

        forbidden = [
            x["id"]
            for x in item["forbidden"]
            if not x["passed"]
        ]

        bad_end = [
            name
            for name, ok in item["end"]["checks"].items()
            if not ok
        ]

        if not misses and not forbidden and not bad_end:
            continue

        any_failure = True
        print(f"[{item['case']}]")

        if misses:
            print("  required:", ", ".join(misses))

        if forbidden:
            print("  forbidden:", ", ".join(forbidden))

        if bad_end:
            print("  end:", ", ".join(bad_end))

    if not any_failure:
        print("none")


if __name__ == "__main__":
    main()
