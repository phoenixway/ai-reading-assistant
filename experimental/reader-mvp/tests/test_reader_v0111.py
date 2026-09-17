from app.protocol import merge_parsed, parse_output
from app.reader import (
    _can_targeted_repair,
    _missing_required_tags,
    _repaired_contract_pass,
)


def _dirty_fast_with_useful_records():
    return parse_output(
        """SUM: Mira receives a report.
WHO: Mira, Jonas
EV: Mira reads the warning @P03
REL: Mira -> Jonas | trust_gain | unsupported sibling
END: present=Mira | loc=control room | situation=Mira remains there
""",
        {2, 3, 4},
        required_end_span=4,
    )


def test_low_raw_span_validity_does_not_block_targeted_repair():
    fast = _dirty_fast_with_useful_records()

    assert not fast.contract_pass
    assert fast.stats["span_validity"] < .80
    assert fast.stats["content_count"] >= 1
    assert _missing_required_tags(fast) == {"END"}

    # The good EV survived record-level validation.
    assert any(
        r.tag == "EV"
        and "reads the warning" in r.payload
        for r in fast.records
    )

    assert _can_targeted_repair(fast)


def test_repaired_contract_accepts_valid_subset_despite_dirty_raw_output():
    fast = _dirty_fast_with_useful_records()

    repair = parse_output(
        """END: present=Mira | loc=control room | situation=Mira remains there @P04
""",
        {2, 3, 4},
        allowed_tags={"END"},
        required_tags={"END"},
        min_content=0,
        required_end_span=4,
    )

    candidate = merge_parsed(
        [fast, repair],
        False,
    )

    assert repair.contract_pass
    assert _repaired_contract_pass(
        fast,
        repair,
        candidate,
    )

    merged = merge_parsed(
        [fast, repair],
        True,
    )

    assert merged.contract_pass
    assert any(
        r.tag == "EV"
        and "reads the warning" in r.payload
        for r in merged.records
    )
    assert any(
        r.tag == "END"
        for r in merged.records
    )


def test_targeted_repair_still_requires_missing_required_tag():
    parsed = parse_output(
        """SUM: summary
WHO: Mira
EV: Mira reads the warning @P03
END: present=Mira | loc=control room | situation=waiting @P04
""",
        {2, 3, 4},
        required_end_span=4,
    )

    assert parsed.contract_pass
    assert not _missing_required_tags(parsed)
    assert not _can_targeted_repair(parsed)
