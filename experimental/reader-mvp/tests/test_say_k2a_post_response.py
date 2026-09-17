import app.reader as r


def rec(speaker, content, p):
    return r.Record(
        tag="SAY",
        payload=f"{speaker} | {content}",
        spans=[p],
        epistemic=None,
        raw="test",
    )


SOURCE = {
    15: (
        '"Tell me, I implore of you, Sir John and husband, '
        'why is the castle dark?'
    ),
    16: (
        '"Can it be that she who waited for us is no more?'
    ),
    17: (
        '"Speak at once, for pity\'s sake! '
        'Oh, merciful heavens!"'
    ),
    18: (
        "Here Lady Dunfern drooped her head before "
        "Sir John got time to even answer a word, "
        "and drew a flask from his pocket."
    ),
}


def content(p):
    text = SOURCE[p]
    value = text[1:]

    if value.endswith('"'):
        value = value[:-1]

    return value


def test_k2a_supports_first_paragraph_of_closed_quote_run():
    c = content(15)

    assert r._source_supports_speaker_run(
        rec("Lady Dunfern", c, 15),
        SOURCE,
        "Lady Dunfern",
        c,
    )


def test_k2a_supports_middle_paragraph_of_closed_quote_run():
    c = content(16)

    assert r._source_supports_speaker_run(
        rec("Lady Dunfern", c, 16),
        SOURCE,
        "Lady Dunfern",
        c,
    )


def test_k2a_supports_final_paragraph_of_closed_quote_run():
    c = content(17)

    assert r._source_supports_speaker_run(
        rec("Lady Dunfern", c, 17),
        SOURCE,
        "Lady Dunfern",
        c,
    )


def test_k2a_does_not_attribute_run_to_responder():
    c = content(17)

    assert not r._source_supports_speaker_run(
        rec("Sir John", c, 17),
        SOURCE,
        "Sir John",
        c,
    )


def test_k2a_requires_communication_after_response_opportunity():
    bad = dict(SOURCE)
    bad[18] = (
        "Lady Dunfern drooped her head before "
        "Sir John got time to open the carriage door."
    )

    c = content(17)

    assert not r._source_supports_speaker_run(
        rec("Lady Dunfern", c, 17),
        bad,
        "Lady Dunfern",
        c,
    )


def test_k2a_requires_immediate_next_paragraph():
    bad = dict(SOURCE)
    bad[18] = ""
    bad[19] = SOURCE[18]

    c = content(17)

    assert not r._source_supports_speaker_run(
        rec("Lady Dunfern", c, 17),
        bad,
        "Lady Dunfern",
        c,
    )


def test_k2a_requires_closed_run():
    bad = dict(SOURCE)
    bad[17] = (
        '"Speak at once, for pity\'s sake! '
        'Oh, merciful heavens!'
    )

    c = bad[17][1:]

    assert not r._source_supports_speaker_run(
        rec("Lady Dunfern", c, 17),
        bad,
        "Lady Dunfern",
        c,
    )
