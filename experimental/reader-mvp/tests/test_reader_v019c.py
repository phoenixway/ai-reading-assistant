from app.protocol import Parsed, Record
from app.reader import (
    _say_source_evidence,
    _sanitize_say_coverage,
    _select_document_content_rows,
)


def _say(
    speaker,
    content,
    *,
    p,
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


def test_claim_is_indirect_communication():
    record = _say(
        "Hal",
        "the mast had shifted again",
        p=4,
    )

    evidence = _say_source_evidence(
        record,
        {
            4: (
                "Later Hal claimed the mast "
                "had shifted again."
            ),
        },
    )

    assert evidence == "indirect"


def test_unique_say_support_relocates_provenance():
    record = _say(
        "Sol",
        "reported a loose antenna cable",
        p=3,
    )

    clean = _sanitize_say_coverage(
        _parsed(record),
        {
            2: (
                "Rafi and Sol worked in the "
                "archive office."
            ),
            3: (
                "Sol took a flashlight and "
                "climbed to the roof."
            ),
            4: (
                "Sol phoned from the roof to "
                "report a loose antenna cable."
            ),
        },
    )

    assert len(clean.records) == 1

    repaired = clean.records[0]

    assert repaired.payload == record.payload
    assert repaired.epistemic == record.epistemic
    assert repaired.raw == record.raw
    assert repaired.spans == [4]

    assert clean.stats[
        "say_provenance_relocated"
    ] == 1

    assert clean.stats[
        "say_indirect_supported"
    ] == 1


def test_zero_support_does_not_relocate():
    record = _say(
        "Ivo",
        "He snatched the compass.",
        p=2,
    )

    clean = _sanitize_say_coverage(
        _parsed(record),
        {
            2: (
                "Ivo stood beside the crate."
            ),
            3: (
                "Maeve closed the door."
            ),
        },
    )

    assert clean.records == []

    assert clean.stats[
        "say_provenance_relocated"
    ] == 0

    assert clean.stats[
        "say_unsupported_dropped"
    ] == 1


def test_multiple_supports_abstain_from_relocation():
    record = _say(
        "Mira",
        "Wait.",
        p=3,
    )

    clean = _sanitize_say_coverage(
        _parsed(record),
        {
            2: (
                'Mira said, “Wait.”'
            ),
            3: (
                "They crossed the hall."
            ),
            4: (
                'At the stairs Mira said, “Wait.”'
            ),
        },
    )

    assert clean.records == []

    assert clean.stats[
        "say_provenance_relocated"
    ] == 0


def test_written_content_is_not_relocation_target():
    record = _say(
        "Priya",
        "North culvert blocked. Use ridge path.",
        p=3,
    )

    clean = _sanitize_say_coverage(
        _parsed(record),
        {
            2: (
                "Priya unfolded a survey map. "
                "Its margin read: "
                "“North culvert blocked. "
                "Use ridge path.”"
            ),
            3: (
                "Priya circled checkpoint C."
            ),
        },
    )

    assert clean.records == []

    assert clean.stats[
        "say_provenance_relocated"
    ] == 0


def test_document_selector_includes_text_bearing_surfaces():
    rows = [
        {
            "local_no": 2,
            "tok_len": 12,
            "text": (
                "The terminal display flashed "
                "a warning."
            ),
        },
        {
            "local_no": 3,
            "tok_len": 10,
            "text": (
                "A route was marked on the map."
            ),
        },
        {
            "local_no": 4,
            "tok_len": 8,
            "text": (
                "The screen showed ERROR 12."
            ),
        },
        {
            "local_no": 5,
            "tok_len": 7,
            "text": (
                "Arden crossed the room."
            ),
        },
    ]

    selected = _select_document_content_rows(
        rows
    )

    assert [
        x["local_no"]
        for x in selected
    ] == [2, 3, 4]
