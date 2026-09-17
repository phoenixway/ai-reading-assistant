from app.protocol import merge_parsed, parse_output
from app.reader import _can_targeted_repair, _missing_required_tags


def test_missing_end_is_targeted_repair_candidate():
    fast = parse_output(
        """SUM: Mara receives a message.
WHO: Mara
EV: Mara opens the envelope @P06
""",
        {1, 2, 3, 4, 5, 6},
        required_end_span=6,
    )

    assert not fast.contract_pass
    assert _missing_required_tags(fast) == {"END"}
    assert _can_targeted_repair(fast)


def test_bad_provenance_is_not_salvaged_by_contract_repair():
    fast = parse_output(
        """SUM: Mara receives a message.
WHO: Mara
EV: Mara opens the envelope @NN
""",
        {1, 2, 3, 4, 5, 6},
        required_end_span=6,
    )

    assert not fast.contract_pass
    assert not _can_targeted_repair(fast)


def test_merge_preserves_valid_fast_records_when_end_is_repaired():
    fast = parse_output(
        """SUM: Mara receives a message.
WHO: Mara
EV: Mara opens the envelope @P06
EV: Mara burns the note @P06
""",
        {1, 2, 3, 4, 5, 6},
        required_end_span=6,
    )

    repair = parse_output(
        """END: present=Mara | loc= | situation=note burned, receipt kept @P06
""",
        {1, 2, 3, 4, 5, 6},
        allowed_tags={"END"},
        required_tags={"END"},
        min_content=0,
        required_end_span=6,
    )

    merged = merge_parsed([fast, repair], True)

    assert merged.contract_pass
    assert [r.tag for r in merged.records] == [
        "SUM",
        "WHO",
        "EV",
        "EV",
        "END",
    ]

    assert any(
        r.payload == "Mara opens the envelope"
        for r in merged.records
    )

    assert any(
        r.payload == "Mara burns the note"
        for r in merged.records
    )
