import app.reader as r


PREVIOUS = {
    1: (
        "Lady Dunfern was forced to decide. "
        "She waited in silence. "
        "All she could do was answer."
    ),
    2: (
        '"Sir and husband," she said, '
        '"I will explain everything that troubles me.'
    ),
    3: (
        '"I have tried to answer you faithfully.'
    ),
}


CURRENT = {
    1: (
        '"You speak of matters which I cannot ignore.'
    ),
    2: (
        '"I am tired now, and I bid thee good-night."'
    ),
    3: (
        "Lady Dunfern left the room."
    ),
}


def test_k2b_derives_unique_open_run_seed():
    assert (
        r._say_cross_segment_open_run_seed(
            PREVIOUS,
            CURRENT,
            same_chapter=True,
        )
        == "Lady Dunfern"
    )


def test_k2b_rejects_chapter_boundary():
    assert (
        r._say_cross_segment_open_run_seed(
            PREVIOUS,
            CURRENT,
            same_chapter=False,
        )
        is None
    )


def test_k2b_rejects_closed_previous_run():
    previous = dict(PREVIOUS)
    previous[3] = (
        '"I have tried to answer you faithfully."'
    )

    assert (
        r._say_cross_segment_open_run_seed(
            previous,
            CURRENT,
            same_chapter=True,
        )
        is None
    )


def test_k2b_rejects_unquoted_current_head():
    current = dict(CURRENT)
    current[1] = "Morning came quietly."

    assert (
        r._say_cross_segment_open_run_seed(
            PREVIOUS,
            current,
            same_chapter=True,
        )
        is None
    )


def test_k2b_rejects_missing_previous_terminal_source():
    previous = dict(PREVIOUS)
    previous[3] = ""

    assert (
        r._say_cross_segment_open_run_seed(
            previous,
            CURRENT,
            same_chapter=True,
        )
        is None
    )
