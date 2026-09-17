import json
from pathlib import Path

from scripts.benchmark_suite import (
    discover_gold_paths,
    load_fixture,
)


ROOT = Path(__file__).resolve().parents[1]

GENERALIZATION_CASES = {
    "gen-shared-subject-chain",
    "gen-pronoun-transfer",
    "gen-negative-intent",
    "gen-document-map",
    "gen-terminal-message",
    "gen-interrupted-dialogue",
    "gen-epistemic-claim",
    "gen-multi-location-end",
    "gen-ambiguous-pronoun",
}


def test_generalization_cases_are_discoverable():
    discovered = {}

    for path in discover_gold_paths():
        gold, story = load_fixture(path)
        discovered[gold["case"]] = (
            path,
            story,
        )

    assert GENERALIZATION_CASES <= set(discovered)


def test_generalization_gold_has_required_shape():
    by_case = {}

    for path in discover_gold_paths():
        gold = json.loads(
            path.read_text(encoding="utf-8")
        )
        by_case[gold["case"]] = gold

    for case in GENERALIZATION_CASES:
        gold = by_case[case]

        assert gold["fixture"]
        assert gold["story"]
        assert gold["focus"]
        assert gold["required"]
        assert "forbidden" in gold
        assert gold["end"]

        for rule in gold["required"]:
            assert rule["id"]
            assert rule["tags"]
            assert rule["patterns"]
            assert isinstance(rule["p"], int)

        for rule in gold["forbidden"]:
            assert rule["id"]
            assert rule["tags"]
            assert rule["patterns"]


def test_generalization_stories_use_three_substantive_paragraphs():
    for path in discover_gold_paths():
        gold = json.loads(
            path.read_text(encoding="utf-8")
        )

        if gold["case"] not in GENERALIZATION_CASES:
            continue

        story = (
            ROOT
            / "samples"
            / gold["story"]
        ).read_text(encoding="utf-8")

        paragraphs = [
            p.strip()
            for p in story.split("\n\n")
            if p.strip()
        ]

        assert len(paragraphs) == 4
        assert paragraphs[0].lower().startswith("chapter")


def test_document_map_fold_pattern_does_not_match_unfold():
    import re

    path = (
        ROOT
        / "samples"
        / "benchmarks"
        / "document_map_gold.json"
    )

    gold = json.loads(
        path.read_text(encoding="utf-8")
    )

    rule = next(
        x
        for x in gold["required"]
        if x["id"] == "priya-folds-map"
    )

    fold_pattern = rule["patterns"][1]

    assert re.search(
        fold_pattern,
        "Priya folded the map",
        re.I,
    )

    assert not re.search(
        fold_pattern,
        "Priya unfolded a survey map",
        re.I,
    )
