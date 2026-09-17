from app.protocol import merge_parsed, parse_output


def test_p_refs_and_tag_prefix_repair():
    raw = """TAG: SUM: Things happen.
TAG: WHO: mara,levin
TAG: EV: Mara opens the envelope @P03
TAG: SAY: Mara | Only an invoice @P05
TAG: END: present=mara | loc=kitchen | situation=Mara keeps the receipt @P05
"""

    p = parse_output(raw, set(range(1, 10)))

    assert p.contract_pass
    assert p.stats["span_validity"] == 1.0
    assert p.stats["repaired_prefix"] == 5
    assert p.records[2].spans == [3]
    assert p.records[3].spans == [5]


def test_literal_nn_reference_is_rejected():
    raw = """SUM: Things happen.
WHO: mara
EV: Mara opens the envelope @NN
END: present=mara | loc=kitchen | situation=Mara waits @P05
"""

    p = parse_output(raw, set(range(1, 10)))

    assert not p.contract_pass
    assert p.stats["no_span"] == 1
    assert len(p.quarantined) == 1


def test_allowed_tags_filter_robust_pass():
    raw = """SUM: summary that should be rejected
ST: Mara | posture | standing @P02
DET: envelope | grey @P03
END: present=mara | loc=kitchen | situation=waiting
"""

    p = parse_output(
        raw,
        set(range(1, 10)),
        allowed_tags={"ST", "DET"},
        required_tags=set(),
        min_content=0,
    )

    assert p.contract_pass
    assert p.stats["disallowed"] == 2
    assert [r.tag for r in p.records] == ["ST", "DET"]


def test_invalid_rel_type_is_quarantined():
    raw = """REL: Levin -> Mara | embarrassment | testing handle @P02"""

    p = parse_output(
        raw,
        set(range(1, 10)),
        allowed_tags={"REL"},
        required_tags=set(),
        min_content=0,
    )

    assert p.contract_pass
    assert p.stats["quarantined"] == 1
    assert p.records == []
    assert "invalid REL type" in p.quarantined[0][1]


def test_question_mark_is_not_inference_marker():
    raw = """TH+: Why did Sava hesitate?"""

    p = parse_output(
        raw,
        set(range(1, 10)),
        allowed_tags={"TH+"},
        required_tags=set(),
        min_content=0,
    )

    assert p.contract_pass
    assert len(p.records) == 1
    assert p.records[0].epistemic == "EXPLICIT"
    assert p.records[0].payload == "Why did Sava hesitate?"


def test_explicit_inference_marker():
    raw = """ST: Levin | emotion | worried ~INF @P03"""

    p = parse_output(
        raw,
        set(range(1, 10)),
        allowed_tags={"ST"},
        required_tags=set(),
        min_content=0,
    )

    assert p.contract_pass
    assert len(p.records) == 1
    assert p.records[0].epistemic == "INFERRED"
    assert p.records[0].payload == "Levin | emotion | worried"


def test_merge_parsed_deduplicates_identical_records():
    a = parse_output(
        "EV: Levin tests the brass handle @P02",
        {2},
        allowed_tags={"EV"},
        required_tags=set(),
        min_content=0,
    )
    b = parse_output(
        "EV: Levin tests the brass handle @P02",
        {2},
        allowed_tags={"EV"},
        required_tags=set(),
        min_content=0,
    )

    merged = merge_parsed([a, b], True)

    assert merged.contract_pass
    assert len(merged.records) == 1
    assert merged.stats["parsed"] == 1
    assert merged.stats["content_count"] == 1


def test_merge_keeps_distinct_observations():
    a = parse_output(
        "EV: Levin tests the brass handle @P02",
        {2, 3},
        allowed_tags={"EV"},
        required_tags=set(),
        min_content=0,
    )
    b = parse_output(
        "DET: envelope | grey @P03",
        {2, 3},
        allowed_tags={"DET"},
        required_tags=set(),
        min_content=0,
    )

    merged = merge_parsed([a, b], True)

    assert [r.tag for r in merged.records] == ["EV", "DET"]
    assert merged.stats["content_count"] == 2


def test_prompt_examples_do_not_contaminate_b17_fixture():
    from app.protocol import DEVELOPER_FAST

    lowered = DEVELOPER_FAST.lower()

    forbidden_fragments = (
        "mara",
        "levin",
        "sava",
        "b17",
        "eastern stair",
        "railway receipt",
        "only an invoice",
        "father welded",
    )

    for forbidden in forbidden_fragments:
        assert forbidden not in lowered
