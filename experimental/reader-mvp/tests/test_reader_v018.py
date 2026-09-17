import json
from pathlib import Path

from app.reader import ACTION_COVERAGE_SYSTEM
from scripts.score_smoke import _match_patterns


def _forbidden(rule_id):
    gold = json.loads(
        Path("samples/smoke_gold.json").read_text()
    )

    return next(
        x for x in gold["forbidden"]
        if x["id"] == rule_id
    )


def test_correct_handoff_does_not_trigger_wrong_direction():
    rule = _forbidden(
        "wrong-direction-mara-hands-envelope"
    )

    assert not _match_patterns(
        "Sava handed Mara an envelope",
        rule["patterns"],
    )

    assert _match_patterns(
        "Mara handed Sava the envelope",
        rule["patterns"],
    )


def test_preserved_as_if_hedge_is_not_promoted_intent():
    rule = _forbidden(
        "hedged-sava-intent-promoted-to-fact"
    )

    assert not _match_patterns(
        "Sava paused as if he wanted to correct her",
        rule["patterns"],
    )

    assert _match_patterns(
        "Sava wanted to correct her",
        rule["patterns"],
    )


def test_coverage_requires_names_not_pronouns():
    prompt = ACTION_COVERAGE_SYSTEM.lower()

    assert "explicit character name instead of a pronoun" in prompt


def test_coverage_splits_coordinated_actions():
    prompt = ACTION_COVERAGE_SYSTEM.lower()

    assert "split coordinated or sequential verbs" in prompt
    assert "do not omit one explicit action" in prompt


def test_coverage_excludes_speech_acts():
    prompt = ACTION_COVERAGE_SYSTEM.lower()

    assert "do not emit speech acts" in prompt
    assert "ask, say, tell, reply, or answer" in prompt


def test_coverage_strips_hedged_interpretation():
    prompt = ACTION_COVERAGE_SYSTEM.lower()

    assert "omit the hedged intent or interpretation" in prompt


def test_coverage_excludes_gaze_noise():
    prompt = ACTION_COVERAGE_SYSTEM.lower()

    assert "do not emit eye/gaze actions" in prompt
