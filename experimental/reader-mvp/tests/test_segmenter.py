from app.segmenter import Para, plan_segments

def test_plan_respects_chapter_boundary():
    ps=[Para('a',1,1,1,1000),Para('b',1,1,2,1000),Para('c',2,2,1,1000)]
    plans=plan_segments(ps,2500)
    assert len(plans)==2
    assert plans[0].chapter==1 and plans[1].chapter==2


class _TinyTokenizer:
    def token_count(self, text):
        return len(text.split())


def test_front_matter_contents_chapter_rows_are_not_real_chapters():
    from app.segmenter import parse_paras

    text = """
IRENE IDDESLEIGH

Some front matter.

CONTENTS.

Page.

CHAPTER I. 9

CHAPTER II. 13

CHAPTER III. 20

CHAPTER IV. 25

CHAPTER I.

First chapter prose begins here.

More first chapter prose.

CHAPTER II.

Second chapter prose begins here.
"""

    paras = parse_paras(
        text,
        _TinyTokenizer(),
    )

    assert [
        p.text
        for p in paras
    ] == [
        "CHAPTER I.",
        "First chapter prose begins here.",
        "More first chapter prose.",
        "CHAPTER II.",
        "Second chapter prose begins here.",
    ]

    assert [
        p.chapter
        for p in paras
    ] == [
        1,
        1,
        1,
        2,
        2,
    ]


def test_first_real_heading_remains_chapter_one_after_front_matter():
    from app.segmenter import parse_paras

    text = """
Title page.

By Somebody.

CHAPTER I.

Actual prose.

CHAPTER II.

More prose.
"""

    paras = parse_paras(
        text,
        _TinyTokenizer(),
    )

    chapter_one_heading = next(
        p
        for p in paras
        if p.text == "CHAPTER I."
    )

    chapter_two_heading = next(
        p
        for p in paras
        if p.text == "CHAPTER II."
    )

    assert chapter_one_heading.chapter == 1
    assert chapter_two_heading.chapter == 2


def test_plain_chapter_heading_is_not_toc_entry():
    from app.segmenter import (
        _looks_like_toc_chapter_entry,
    )

    assert not _looks_like_toc_chapter_entry(
        "CHAPTER I."
    )

    assert not _looks_like_toc_chapter_entry(
        "CHAPTER 9"
    )

    assert _looks_like_toc_chapter_entry(
        "CHAPTER I. 9"
    )

    assert _looks_like_toc_chapter_entry(
        "CHAPTER XII. THE RETURN ........ 102"
    )
