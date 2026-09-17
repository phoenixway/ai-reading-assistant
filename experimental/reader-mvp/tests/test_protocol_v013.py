from app.protocol import parse_output


def test_end_requires_provenance():
    raw = """SUM: Things happen.
WHO: Mara
EV: Mara waits @P05
END: present=Mara | loc=kitchen | situation=Mara waits
"""

    parsed = parse_output(raw, {1, 2, 3, 4, 5})

    assert not parsed.contract_pass
    assert parsed.stats["no_span"] == 1
    assert not any(r.tag == "END" for r in parsed.records)


def test_end_must_reference_final_substantive_paragraph():
    raw = """SUM: Things happen.
WHO: Mara
EV: Mara waits @P05
END: present=Mara | loc=kitchen | situation=Mara waits @P05
"""

    parsed = parse_output(
        raw,
        {1, 2, 3, 4, 5, 6},
        required_end_span=6,
    )

    assert not parsed.contract_pass
    assert parsed.stats["end_tail_miss"] == 1
    assert any(
        "final substantive paragraph @P06" in reason
        for _, reason in parsed.quarantined
    )


def test_end_accepts_final_substantive_paragraph():
    raw = """SUM: Things happen.
WHO: Mara
EV: Mara burns the note @P06
END: present=Mara | loc=kitchen | situation=note burned, receipt retained @P06
"""

    parsed = parse_output(
        raw,
        {1, 2, 3, 4, 5, 6},
        required_end_span=6,
    )

    assert parsed.contract_pass
    end = next(r for r in parsed.records if r.tag == "END")
    assert end.spans == [6]


def test_end_rejects_location_alias():
    raw = """SUM: Things happen.
WHO: Mara
EV: Mara waits @P06
END: present=Mara | location=workshop | situation=Mara waits @P06
"""

    parsed = parse_output(
        raw,
        {1, 2, 3, 4, 5, 6},
        required_end_span=6,
    )

    assert not parsed.contract_pass
    assert parsed.stats["shape_invalid"] == 1
    assert not any(r.tag == "END" for r in parsed.records)


def test_st_requires_entity_field_value():
    parsed = parse_output(
        "ST: Levin | embarrassed @P02",
        {2},
        allowed_tags={"ST"},
        required_tags=set(),
        min_content=0,
    )

    assert parsed.contract_pass
    assert parsed.records == []
    assert parsed.stats["shape_invalid"] == 1


def test_kn_requires_entity_knowledge_source():
    parsed = parse_output(
        "KN: Mara | father welded the stair @P02",
        {2},
        allowed_tags={"KN"},
        required_tags=set(),
        min_content=0,
    )

    assert parsed.contract_pass
    assert parsed.records == []
    assert parsed.stats["shape_invalid"] == 1


def test_say_requires_speaker_and_claim():
    parsed = parse_output(
        "SAY: Mara @P02",
        {2},
        allowed_tags={"SAY"},
        required_tags=set(),
        min_content=0,
    )

    assert parsed.contract_pass
    assert parsed.records == []
    assert parsed.stats["shape_invalid"] == 1
