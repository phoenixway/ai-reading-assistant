from app.protocol import Parsed, Record
from app.reader import (
    _say_source_evidence,
    _sanitize_say_coverage,
)


def _say(
    speaker,
    content,
    *,
    p=2,
):
    return Record(
        tag="SAY",
        payload=f"{speaker} | {content}",
        spans=[p],
        epistemic="EXPLICIT",
        raw="",
    )


def _parsed(*records):
    return Parsed(
        records=list(records),
        ignored=[],
        quarantined=[],
        stats={
            "parsed": len(records),
            "content_count": len(records),
        },
        contract_pass=True,
    )


def _evidence(source, speaker, content):
    return _say_source_evidence(
        _say(
            speaker,
            content,
        ),
        {
            2: source,
        },
    )


def test_direct_speech_has_positive_evidence():
    source = (
        "Malik asked whether the culvert was safe. "
        "Priya answered, “We take the ridge.”"
    )

    assert _evidence(
        source,
        "Priya",
        "We take the ridge",
    ) == "spoken"


def test_indirect_report_has_positive_evidence():
    source = (
        "Sol phoned from the roof to report "
        "a loose antenna cable."
    )

    assert _evidence(
        source,
        "Sol",
        "reported a loose antenna cable",
    ) == "indirect"


def test_indirect_question_has_positive_evidence():
    source = (
        "Selene entered the operations bay "
        "and asked what happened."
    )

    assert _evidence(
        source,
        "Selene",
        "what happened",
    ) == "indirect"


def test_narrated_action_is_not_speech():
    source = (
        "Maeve set a brass compass beside Ivo. "
        "He snatched it and wrapped it in a scarf."
    )

    assert _evidence(
        source,
        "Ivo",
        "He snatched it and wrapped it in a scarf.",
    ) == "unknown"


def test_ambiguous_quote_is_not_supported():
    source = (
        "Mira and Jonas stood beside the door. "
        "“Wait.” Neither of them moved."
    )

    assert _evidence(
        source,
        "Mira",
        "Wait",
    ) == "unknown"


def test_negated_report_is_not_supported():
    source = (
        "Jun did not report the pressure loss."
    )

    assert _evidence(
        source,
        "Jun",
        "pressure loss",
    ) == "unknown"


def test_refused_answer_is_not_supported():
    source = (
        "Mira refused to answer "
        "what was inside the box."
    )

    assert _evidence(
        source,
        "Mira",
        "what was inside the box",
    ) == "unknown"


def test_display_warning_is_not_supported_as_speech():
    source = (
        "Jun woke the wall terminal. "
        "Its display flashed: "
        "“Pump array offline. Manual reset required.”"
    )

    assert _evidence(
        source,
        "Jun",
        "Pump array offline. Manual reset required.",
    ) in {
        "document",
        "unknown",
    }


def test_unknown_say_is_dropped():
    record = _say(
        "Ivo",
        "He snatched it and wrapped it in a scarf.",
    )

    parsed = _parsed(record)

    clean = _sanitize_say_coverage(
        parsed,
        {
            2: (
                "Maeve set a brass compass beside Ivo. "
                "He snatched it and wrapped it in a scarf."
            ),
        },
    )

    assert clean.records == []
    assert clean.stats[
        "say_unsupported_dropped"
    ] == 1


def test_indirect_say_is_kept():
    record = _say(
        "Sol",
        "reported a loose antenna cable",
    )

    parsed = _parsed(record)

    clean = _sanitize_say_coverage(
        parsed,
        {
            2: (
                "Sol phoned from the roof to report "
                "a loose antenna cable."
            ),
        },
    )

    assert clean.records == [record]
    assert clean.stats[
        "say_indirect_supported"
    ] == 1
