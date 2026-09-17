from __future__ import annotations

import re

from app.db import connect
from app.reader import (
    _source_supports_speaker,
    _DOCUMENT_CUE_RE,
)


BOOK_ID = 364

SEGMENTS = {
    5: [
        "Sir John",
        "Irene",
        "Lady Dunfern",
    ],
    8: [
        "Sir John",
        "Irene",
        "Lady Dunfern",
    ],
    11: [
        "Sir John",
        "Lady Dunfern",
        "Rachel",
        "Rachel Hyde",
        "Doctor Doherty",
        "Oscar Otwell",
    ],
}


QUOTE_RE = re.compile(
    r'["“”]'
)

STARTS_QUOTE_RE = re.compile(
    r'^\s*["“]'
)

LEADIN_VERBS = (
    r"began|continued|started|"
    r"replied|answered|said|"
    r"remarked|declared"
)


def quote_spans(
    text: str,
):
    """
    Return literal closed double-quote spans.

    This is intentionally simple. We only need small literal
    anchors such as:

        "Great heaven!" murmured Sir John
        "This," said Sir John, "is ..."

    Open speech-run continuation is handled separately.
    """

    positions = [
        m.start()
        for m in QUOTE_RE.finditer(
            text
        )
    ]

    spans = []

    for i in range(
        0,
        len(positions) - 1,
        2,
    ):
        start = positions[i] + 1
        end = positions[i + 1]

        if end > start:
            spans.append(
                (
                    start,
                    end,
                )
            )

    return spans


def directly_anchors(
    text: str,
    speaker: str,
) -> bool:
    """
    Ask the existing precision verifier whether ANY literal
    quotation in this paragraph is directly attributed to the
    candidate speaker.
    """

    for bounds in quote_spans(
        text
    ):
        if _source_supports_speaker(
            text,
            speaker,
            bounds,
        ):
            return True

    return False


def named_leadin(
    text: str,
    speaker: str,
) -> bool:
    """
    Positive cross-paragraph source form:

        Sir John began--
        "Irene, ..."

        Irene ... she thus began:
        "My dearest ..."

    The candidate name itself MUST occur before the lead-in verb.
    No generic name extraction and no pronoun resolution.
    """

    speaker_re = re.escape(
        speaker
    )

    tail = text[-360:]

    return bool(
        re.search(
            rf'\b{speaker_re}\b'
            rf'[^.!?]{{0,300}}'
            rf'\b(?:{LEADIN_VERBS})\b'
            rf'[^.!?]{{0,80}}'
            rf'(?::|--|—|-)\s*$',
            tail,
            re.I,
        )
    )


def document_leadin(
    text: str,
) -> bool:
    """
    Cross-paragraph written-content introduction.

    Examples:
        The lines were these:--
        The note read:
        The letter said:

    This blocks the next quoted paragraph from becoming a
    spoken run.
    """

    tail = text[-320:]

    if not re.search(
        r'(?::|:--|:—)\s*$',
        tail,
    ):
        return False

    if re.search(
        r'\b(?:'
        r'lines?\s+were\s+these|'
        r'words?\s+were\s+these|'
        r'note|letter|card|'
        r'written|inscription|'
        r'document|message'
        r')\b',
        tail,
        re.I,
    ):
        return True

    return bool(
        _DOCUMENT_CUE_RE.search(
            tail
        )
    )


def unique(
    values,
):
    values = [
        value
        for value in values
        if value
    ]

    values = list(
        dict.fromkeys(
            values
        )
    )

    if len(values) == 1:
        return values[0]

    return None


def main():
    with connect() as con:
        for seg_idx, candidates in (
            SEGMENTS.items()
        ):
            seg = con.execute(
                """
                SELECT *
                FROM segments
                WHERE book_id=?
                  AND idx=?
                """,
                (
                    BOOK_ID,
                    seg_idx,
                ),
            ).fetchone()

            rows = con.execute(
                """
                SELECT
                    ss.local_no,
                    s.text
                FROM segment_spans ss
                JOIN spans s
                  ON s.id=ss.span_id
                WHERE ss.seg_id=?
                ORDER BY ss.local_no
                """,
                (
                    seg["id"],
                ),
            ).fetchall()

            print()
            print(
                "=" * 120
            )
            print(
                f"SEG {seg_idx} "
                f"chapter={seg['chapter']} "
                f"tokens={seg['tok_len']}"
            )
            print(
                "=" * 120
            )

            active_speaker = None
            active_open = False

            pending_speakers = []
            pending_document = False

            for row in rows:
                local_no = int(
                    row["local_no"]
                )

                text = (
                    row["text"]
                    or ""
                ).strip()

                qcount = len(
                    QUOTE_RE.findall(
                        text
                    )
                )

                starts_quote = bool(
                    STARTS_QUOTE_RE.match(
                        text
                    )
                )

                direct = [
                    candidate
                    for candidate in candidates
                    if directly_anchors(
                        text,
                        candidate,
                    )
                ]

                direct_speaker = unique(
                    direct
                )

                pending_speaker = unique(
                    pending_speakers
                )

                resolved = None
                reason = None

                # -----------------------------------------
                # Strong same-paragraph named attribution.
                # -----------------------------------------
                if direct_speaker:
                    resolved = direct_speaker
                    reason = "direct-anchor"

                # -----------------------------------------
                # Strong named lead-in in PREVIOUS
                # paragraph.
                # -----------------------------------------
                elif (
                    starts_quote
                    and pending_speaker
                    and not pending_document
                ):
                    resolved = pending_speaker
                    reason = "named-leadin"

                # -----------------------------------------
                # Continuation only while an explicitly
                # anchored quotation remains structurally
                # open.
                # -----------------------------------------
                elif (
                    starts_quote
                    and active_open
                    and active_speaker
                    and not pending_document
                ):
                    resolved = active_speaker
                    reason = "open-continuation"

                if (
                    qcount
                    or pending_speakers
                    or pending_document
                ):
                    sample = re.sub(
                        r"\s+",
                        " ",
                        text,
                    )

                    if len(sample) > 180:
                        sample = (
                            sample[:177]
                            + "..."
                        )

                    print(
                        f"P{local_no:02} "
                        f"q={qcount:<2} "
                        f"direct={','.join(direct) or '-':28} "
                        f"prev={pending_speaker or '-':14} "
                        f"docprev={int(pending_document)} "
                        f"=> {resolved or '?':14} "
                        f"[{reason or '-'}]"
                    )

                    print(
                        "   ",
                        sample,
                    )

                # -----------------------------------------
                # Run state for NEXT paragraph.
                # -----------------------------------------
                if resolved:
                    active_speaker = resolved

                    active_open = (
                        qcount % 2
                        == 1
                    )

                elif qcount:
                    if not active_open:
                        active_speaker = None

                # A prose paragraph without an active quoted
                # continuation closes the inherited run.
                elif active_open:
                    active_speaker = None
                    active_open = False

                pending_speakers = [
                    candidate
                    for candidate in candidates
                    if named_leadin(
                        text,
                        candidate,
                    )
                ]

                pending_document = (
                    document_leadin(
                        text
                    )
                )


if __name__ == "__main__":
    main()
