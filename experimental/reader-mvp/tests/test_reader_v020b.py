from app.protocol import (
    Parsed,
    Record,
)
from app.reader import (
    _compile_terminal_situation,
)


def rec(
    tag,
    payload,
    spans,
    epistemic="EXPLICIT",
):
    return Record(
        tag=tag,
        payload=payload,
        spans=list(spans),
        epistemic=epistemic,
        raw="",
    )


def parsed(*records):
    return Parsed(
        records=list(records),
        ignored=[],
        quarantined=[],
        stats={},
        contract_pass=True,
    )


def test_terminal_tail_preserves_incumbent_and_last_three_final_evs():
    end = rec(
        "END",
        (
            "present=Mara | "
            "loc=workshop | "
            "situation=Mara burns the note and keeps the receipt"
        ),
        [6],
    )

    value = _compile_terminal_situation(
        parsed(
            rec(
                "EV",
                "She opened the envelope",
                [6],
            ),
            rec(
                "EV",
                "Mara read the note twice",
                [6],
            ),
            rec(
                "EV",
                "Mara burned the note",
                [6],
            ),
            rec(
                "EV",
                "Mara kept the receipt",
                [6],
            ),
            end,
        ),
        end,
        "Mara burns the note and keeps the receipt",
    )

    assert value == (
        "Mara burns the note and keeps the receipt; "
        "Mara read the note twice; "
        "Mara burned the note; "
        "Mara kept the receipt"
    )


def test_terminal_tail_uses_only_end_final_paragraph():
    end = rec(
        "END",
        (
            "present=Vero | "
            "loc=rooftop | "
            "situation=Vero measures the antenna"
        ),
        [4],
    )

    value = _compile_terminal_situation(
        parsed(
            rec(
                "EV",
                "Vero examined the antenna",
                [2],
            ),
            rec(
                "EV",
                "Vero marked a chalk line",
                [3],
            ),
            rec(
                "EV",
                "Vero measured the distance to the chalk line",
                [4],
            ),
            rec(
                "EV",
                "Vero found no change",
                [4],
            ),
            rec(
                "EV",
                "She remained on the rooftop",
                [4],
            ),
            end,
        ),
        end,
        "Vero measures the antenna",
    )

    assert (
        "examined"
        not in value
    )

    assert (
        "marked a chalk line"
        not in value
    )

    assert (
        "measured the distance to the chalk line"
        in value
    )

    assert (
        "found no change"
        in value
    )


def test_terminal_tail_rejects_nonexplicit_records():
    end = rec(
        "END",
        (
            "present=Vero | "
            "loc=rooftop | "
            "situation=Vero waits"
        ),
        [4],
    )

    value = _compile_terminal_situation(
        parsed(
            rec(
                "EV",
                "The antenna leaned east",
                [4],
                epistemic="INFERRED",
            ),
            rec(
                "EV",
                "The mast shifted",
                [4],
                epistemic="HYPOTHESIS",
            ),
            rec(
                "EV",
                "Vero found no change",
                [4],
            ),
            end,
        ),
        end,
        "Vero waits",
    )

    assert (
        "leaned east"
        not in value
    )

    assert (
        "mast shifted"
        not in value
    )

    assert (
        "Vero found no change"
        in value
    )


def test_terminal_tail_deduplicates_identical_coverage_records():
    end = rec(
        "END",
        (
            "present=Petro | "
            "loc=courtyard gate | "
            "situation=Olek walks away"
        ),
        [4],
    )

    value = _compile_terminal_situation(
        parsed(
            rec(
                "EV",
                "Petro hid the key inside his boot",
                [4],
            ),
            rec(
                "EV",
                "Petro hid the key inside his boot",
                [4],
            ),
            rec(
                "EV",
                "Petro stayed by the gate",
                [4],
            ),
            end,
        ),
        end,
        "Olek walks away",
    )

    assert (
        value.count(
            "Petro hid the key inside his boot"
        )
        == 1
    )


def test_terminal_tail_keeps_original_record_order():
    end = rec(
        "END",
        (
            "present=Ada | "
            "loc=kitchen | "
            "situation=Ada recorded the pump belt"
        ),
        [4],
    )

    value = _compile_terminal_situation(
        parsed(
            rec(
                "EV",
                "Ada wrote pump belt in the ledger",
                [4],
            ),
            rec(
                "EV",
                "Ada returned the ledger to the cabinet",
                [4],
            ),
            rec(
                "EV",
                "Ada stayed in the kitchen",
                [4],
            ),
            end,
        ),
        end,
        "Ada recorded the pump belt",
    )

    assert value.endswith(
        "Ada wrote pump belt in the ledger; "
        "Ada returned the ledger to the cabinet; "
        "Ada stayed in the kitchen"
    )


def test_terminal_tail_no_end_span_returns_incumbent():
    end = rec(
        "END",
        (
            "present=Jun | "
            "loc=operations bay | "
            "situation=terminal shut"
        ),
        [],
    )

    value = _compile_terminal_situation(
        parsed(
            rec(
                "EV",
                "Jun pocketed the paper",
                [4],
            ),
            end,
        ),
        end,
        "terminal shut",
    )

    assert value == "terminal shut"


def test_terminal_tail_does_not_touch_non_ev_records():
    end = rec(
        "END",
        (
            "present=Jun | "
            "loc=operations bay | "
            "situation=terminal shut"
        ),
        [4],
    )

    value = _compile_terminal_situation(
        parsed(
            rec(
                "SAY",
                "Selene | reset the pump",
                [4],
            ),
            rec(
                "DET",
                "scrap paper | X9-14",
                [4],
            ),
            rec(
                "EV",
                "Jun pocketed the paper",
                [4],
            ),
            end,
        ),
        end,
        "terminal shut",
    )

    assert (
        "reset the pump"
        not in value
    )

    assert (
        "X9-14"
        not in value
    )

    assert (
        "Jun pocketed the paper"
        in value
    )
