from app.protocol import parse_output
from app.reader import ACTION_COVERAGE_SYSTEM


def test_action_coverage_preserves_roles():
    prompt = ACTION_COVERAGE_SYSTEM.lower()

    assert "never swap actor" in prompt
    assert "giver" in prompt
    assert "receiver" in prompt
    assert "near-extractive wording" in prompt


def test_action_coverage_requires_explicit_read_action():
    prompt = ACTION_COVERAGE_SYSTEM.lower()

    assert "reading a note" in prompt
    assert "emit each action separately" in prompt


def test_action_coverage_discourages_gaze_noise():
    prompt = ACTION_COVERAGE_SYSTEM.lower()

    assert "do not emit eye/gaze actions" in prompt


def test_action_coverage_rejects_reference_outside_targets():
    parsed = parse_output(
        """EV: Sava arrives @P03
EV: Levin tests handle @P02
""",
        {3, 5, 6},
        allowed_tags={"EV"},
        required_tags=set(),
        min_content=0,
    )

    assert [r.spans for r in parsed.records] == [[3]]
    assert parsed.stats["quarantined"] == 1
    assert parsed.stats["no_span"] == 1
