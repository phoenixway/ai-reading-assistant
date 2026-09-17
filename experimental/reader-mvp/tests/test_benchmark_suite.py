import json
from pathlib import Path

from scripts.benchmark_suite import (
    discover_gold_paths,
    load_fixture,
)


ROOT = Path(__file__).resolve().parents[1]


def test_suite_contains_original_baseline_fixtures():
    paths = discover_gold_paths()

    cases = set()

    for path in paths:
        gold, _ = load_fixture(path)
        cases.add(gold["case"])

    assert {
        "b17-baseline",
        "coreference-handoff",
        "document-vs-speech",
        "end-location",
        "hedged-perception",
    } <= cases

    cases = []

    for path in paths:
        gold, story = load_fixture(path)

        assert story.exists()
        assert gold["required"]
        assert "fixture" in gold
        assert "case" in gold
        assert "story" in gold

        cases.append(gold["case"])

    assert len(cases) == len(set(cases))


def test_every_fixture_has_forbidden_checks():
    for path in discover_gold_paths():
        gold = json.loads(
            path.read_text(encoding="utf-8")
        )

        assert gold.get("forbidden")


def test_new_fixtures_have_positive_end_location():
    paths = [
        p
        for p in discover_gold_paths()
        if "benchmarks" in p.parts
    ]

    assert paths

    for path in paths:
        gold = json.loads(
            path.read_text(encoding="utf-8")
        )

        assert gold["end"].get("loc_patterns")


def test_benchmark_story_paths_are_inside_samples():
    for path in discover_gold_paths():
        gold, story = load_fixture(path)

        assert story.is_relative_to(ROOT / "samples")
