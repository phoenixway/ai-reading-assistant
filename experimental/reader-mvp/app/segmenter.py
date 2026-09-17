from __future__ import annotations
from dataclasses import dataclass
import re
from .textutil import paragraphs, CHAPTER_RE, SCENE_BREAK_RE
from .llama import LlamaClient

@dataclass
class Para:
    text: str
    chapter: int
    scene: int
    para: int
    tok_len: int

@dataclass
class SegmentPlan:
    chapter: int
    paras: list[Para]
    tok_len: int



_CONTENTS_RE = re.compile(
    r"^\s*(?:table\s+of\s+contents|contents)\.?\s*$",
    re.I,
)


def _looks_like_toc_chapter_entry(
    block: str,
) -> bool:
    """
    Detect chapter-shaped TOC entries such as:

        CHAPTER I. 9
        CHAPTER II. Some title ........ 13

    A normal narrative heading such as:

        CHAPTER I.

    is deliberately NOT treated as a TOC entry.

    This helper is used only inside a front-matter TOC context.
    """

    match = CHAPTER_RE.match(
        block
    )

    if match is None:
        return False

    suffix = block[
        match.end():
    ].strip()

    if not suffix:
        return False

    # Page number must appear AFTER the chapter identifier.
    #
    # CHAPTER I. 9
    #            ^
    #
    # This avoids mistaking "CHAPTER 9" itself for a TOC row.
    return bool(
        re.search(
            r"(?:\.{1,}|…|\s)"
            r"\s*\d+\s*$",
            suffix,
        )
    )


def _strip_front_matter_toc_blocks(
    blocks: list[str],
) -> list[str]:
    """
    Remove a front-matter table of contents when it is followed by
    the real narrative chapter sequence.

    Conservative requirements:
    - CONTENTS / TABLE OF CONTENTS near the front;
    - at least three chapter-shaped entries carrying page numbers;
    - followed by a chapter heading that is NOT a page-number TOC
      entry.

    Everything from the beginning of the book through the TOC is
    excluded from narrative SOURCE.

    The original input text remains untouched outside the parsed
    representation.
    """

    if not blocks:
        return blocks

    scan_limit = min(
        len(blocks),
        160,
    )

    contents_positions = [
        i
        for i, block in enumerate(
            blocks[:scan_limit]
        )
        if _CONTENTS_RE.match(
            block
        )
    ]

    for contents_i in contents_positions:
        toc_entries = 0

        for i in range(
            contents_i + 1,
            scan_limit,
        ):
            block = blocks[i]

            if _looks_like_toc_chapter_entry(
                block
            ):
                toc_entries += 1
                continue

            if CHAPTER_RE.match(
                block
            ):
                # First chapter-shaped row after a sufficiently
                # large page-number TOC run is the beginning of
                # the actual narrative.
                if toc_entries >= 3:
                    return blocks[i:]

                break

            # Labels such as "Page." or short TOC decorations may
            # appear before/between entries.
            if len(block.strip()) <= 80:
                continue

            # Long prose before a real heading means this was not
            # the compact front-matter pattern we are looking for.
            if toc_entries:
                break

            if (
                i - contents_i
                > 10
            ):
                break

    return blocks


def parse_paras(text: str, llama: LlamaClient) -> list[Para]:
    blocks = _strip_front_matter_toc_blocks(
        paragraphs(text)
    )

    out: list[Para] = []

    chapter = 1
    scene = 1
    para_no = 0
    seen_chapter_heading = False

    for block in blocks:
        if CHAPTER_RE.match(block):
            # The first genuine chapter heading is chapter 1 even
            # when title/front-matter blocks preceded it.
            #
            # Subsequent genuine headings advance the chapter.
            if seen_chapter_heading:
                chapter += 1
                scene += 1
            else:
                seen_chapter_heading = True

            para_no = 0

        elif SCENE_BREAK_RE.match(block):
            scene += 1

        para_no += 1

        out.append(
            Para(
                block,
                chapter,
                scene,
                para_no,
                llama.token_count(block),
            )
        )

    return out


def plan_segments(paras: list[Para], target: int = 2500, min_fill: float = 0.55) -> list[SegmentPlan]:
    plans: list[SegmentPlan] = []
    cur: list[Para] = []
    cur_tok = 0
    cur_ch = paras[0].chapter if paras else 1

    def flush():
        nonlocal cur, cur_tok, cur_ch
        if cur:
            plans.append(SegmentPlan(cur_ch, cur, cur_tok))
            cur = []
            cur_tok = 0

    for p in paras:
        hard_boundary = p.chapter != cur_ch
        if hard_boundary and cur:
            flush()
            cur_ch = p.chapter
        if cur and cur_tok + p.tok_len > target and cur_tok >= int(target * min_fill):
            flush()
            cur_ch = p.chapter
        cur.append(p)
        cur_tok += p.tok_len
        if SCENE_BREAK_RE.match(p.text) and cur_tok >= int(target * 0.35):
            flush()
            cur_ch = p.chapter
    flush()
    return plans
