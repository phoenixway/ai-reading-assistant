from scripts.score_smoke import _match_patterns, _obs_matches


def test_match_patterns_are_case_insensitive_and_partial():
    assert _match_patterns(
        "Levin tested the brass handle",
        ["levin", "test", "brass handle"],
    )


def test_observation_match_checks_tag_and_epistemic():
    obs = {
        "tag": "ST",
        "payload": "Sava | intent | wanted to correct Mara",
        "epistemic": "HYPOTHESIS",
    }

    rule = {
        "tags": ["ST"],
        "epistemic": "EXPLICIT",
        "patterns": ["sava", "correct"],
    }

    assert not _obs_matches(obs, rule)

    obs["epistemic"] = "EXPLICIT"
    assert _obs_matches(obs, rule)


def test_end_keep_pattern_accepts_kept():
    import json
    from pathlib import Path
    from scripts.score_smoke import _match_patterns

    gold = json.loads(
        Path("samples/smoke_gold.json").read_text()
    )

    assert _match_patterns(
        "Mara opened the envelope, burned the note, and kept the receipt.",
        gold["end"]["situation_patterns"],
    )


def test_structural_paragraph_regex_shape():
    import re

    structural_re = re.compile(
        r"^(?:chapter\s+\d+|\*{3,}|-{3,}|_{3,}|#{3,})$",
        re.I,
    )

    assert structural_re.fullmatch("CHAPTER 1")
    assert structural_re.fullmatch("***")
    assert structural_re.fullmatch("-----")
    assert not structural_re.fullmatch("Mara opened the envelope.")
