from __future__ import annotations

import re

from app.db import connect
from app.reader import _DOCUMENT_CUE_RE


BOOK_ID = 364
SEGMENT_IDXS = [5, 8, 11]


SPEECH_VERBS = (
    r"said|asked|replied|answered|added|"
    r"whispered|shouted|called|told|remarked|"
    r"murmured|cried|exclaimed|continued|"
    r"requested|declared|responded|protested|"
    r"insisted|urged|"
    r"started|began|interrupted"
)

NAME = (
    r"(?:"
    r"(?:Sir|Lady|Lord|Doctor|Dr\.?|Mr\.?|Mrs\.?|Miss)"
    r"\s+[A-Z][A-Za-z'-]+"
    r"(?:\s+[A-Z][A-Za-z'-]+)?"
    r"|"
    r"[A-Z][A-Za-z'-]+"
    r"(?:\s+[A-Z][A-Za-z'-]+){0,1}"
    r")"
)

QUOTE_CHARS_RE = re.compile(
    r'["“”]'
)

STARTS_QUOTE_RE = re.compile(
    r'^\s*["“]'
)

NAMED_POST_RE = re.compile(
    rf'["”][\s,;:!?—-]*'
    rf'(?:'
    rf'(?P<verb1>{SPEECH_VERBS})\s+'
    rf'(?P<name1>{NAME})'
    rf'|'
    rf'(?P<name2>{NAME})\s+'
    rf'(?P<verb2>{SPEECH_VERBS})'
    rf')\b',
    re.I,
)

NAMED_PRE_RE = re.compile(
    rf'\b(?P<name>{NAME})\b'
    rf'[^.!?]{{0,100}}?'
    rf'\b(?:{SPEECH_VERBS})\b'
    rf'[^.!?]{{0,30}}?'
    rf'["“]',
    re.I,
)

NAMED_LEADIN_RE = re.compile(
    rf'\b(?P<name>{NAME})\b'
    rf'[^.!?]{{0,120}}?'
    rf'\b(?:began|continued|started)\b'
    rf'\s*(?::|--|—|-)\s*$',
    re.I,
)

PRONOUN_ATTR_RE = re.compile(
    rf'\b(?:he|she|they)\s+'
    rf'(?:{SPEECH_VERBS})\b'
    rf'|'
    rf'\b(?:{SPEECH_VERBS})\s+'
    rf'(?:he|she|they)\b',
    re.I,
)


def clean_name(
    value: str | None,
) -> str | None:
    if not value:
        return None

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip(" ,;:-—")

    # Regex capture can occasionally absorb a discourse word
    # before a titled/name phrase. Keep this shadow conservative.
    words = value.split()

    while (
        len(words) > 1
        and words[0] in {
            "Here",
            "Then",
            "And",
            "But",
            "So",
        }
    ):
        words.pop(0)

    return " ".join(words)


def explicit_named_anchor(
    text: str,
) -> tuple[str | None, str | None]:
    """
    Return (speaker, evidence-kind) only for strong explicit
    named attribution in the same paragraph.
    """

    post = NAMED_POST_RE.search(
        text
    )

    if post:
        name = (
            post.group("name1")
            or post.group("name2")
        )

        return (
            clean_name(name),
            "named-postquote",
        )

    pre = NAMED_PRE_RE.search(
        text
    )

    if pre:
        return (
            clean_name(
                pre.group("name")
            ),
            "named-prequote",
        )

    return None, None


def pending_named_leadin(
    text: str,
) -> str | None:
    """
    Strong cross-paragraph lead-in:

        Sir John began--
        [next paragraph] "Irene, ..."

    No pronoun/coreference inference here.
    """

    match = NAMED_LEADIN_RE.search(
        text
    )

    if not match:
        return None

    return clean_name(
        match.group("name")
    )


def looks_like_document_quote(
    text: str,
) -> bool:
    """
    Conservative shadow-only document marker.

    We mainly want to prevent:
        The lines were these:
        "Accept my warmest greeting ..."

    from becoming a spoken continuation.
    """

    lowered = text.casefold()

    if (
        "the lines were these" in lowered
        or "the words were these" in lowered
        or "written with" in lowered
    ):
        return True

    return bool(
        _DOCUMENT_CUE_RE.search(
            text
        )
        and re.search(
            r'\b(?:written|note|letter|card|message)\b',
            text,
            re.I,
        )
    )


def main():
    with connect() as con:
        for seg_idx in SEGMENT_IDXS:
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

            if seg is None:
                continue

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
            pending_speaker = None

            for row in rows:
                local_no = int(
                    row["local_no"]
                )

                text = (
                    row["text"]
                    or ""
                ).strip()

                quote_count = len(
                    QUOTE_CHARS_RE.findall(
                        text
                    )
                )

                starts_quote = bool(
                    STARTS_QUOTE_RE.search(
                        text
                    )
                )

                document = (
                    looks_like_document_quote(
                        text
                    )
                )

                explicit, evidence = (
                    explicit_named_anchor(
                        text
                    )
                )

                leadin = (
                    pending_named_leadin(
                        text
                    )
                )

                pronoun_attr = bool(
                    PRONOUN_ATTR_RE.search(
                        text
                    )
                )

                resolved = None
                reason = None

                # ------------------------------------------
                # Strongest evidence: explicit named speaker
                # inside the paragraph.
                # ------------------------------------------
                if (
                    quote_count
                    and explicit
                    and not document
                ):
                    resolved = explicit
                    reason = evidence

                # ------------------------------------------
                # Previous paragraph explicitly introduced
                # a named speaker and ended with a speech
                # lead-in.
                # ------------------------------------------
                elif (
                    starts_quote
                    and pending_speaker
                    and not document
                ):
                    resolved = (
                        pending_speaker
                    )
                    reason = (
                        "previous-named-leadin"
                    )

                # ------------------------------------------
                # Old-style multi-paragraph quotation:
                #
                # P13 "....          # unmatched opening
                # P14 "....
                # P15 "....
                #
                # Propagate only while we have an OPEN quoted
                # run. Do not infer across a closed quote.
                # ------------------------------------------
                elif (
                    starts_quote
                    and active_open
                    and active_speaker
                    and not document
                ):
                    resolved = (
                        active_speaker
                    )
                    reason = (
                        "open-quote-continuation"
                    )

                # ------------------------------------------
                # Update quote-run state.
                # ------------------------------------------
                if document:
                    active_speaker = None
                    active_open = False

                elif resolved:
                    active_speaker = resolved

                    # Odd number of quote marks means an
                    # unmatched quote remains open.
                    active_open = (
                        quote_count % 2
                        == 1
                    )

                elif quote_count:
                    # An unattributed fresh quotation must not
                    # inherit a CLOSED speaker run.
                    if not active_open:
                        active_speaker = None

                # A strong named lead-in applies to the next
                # paragraph only.
                pending_speaker = leadin

                if (
                    quote_count
                    or leadin
                    or pronoun_attr
                ):
                    sample = re.sub(
                        r"\s+",
                        " ",
                        text,
                    )

                    if len(sample) > 170:
                        sample = (
                            sample[:167]
                            + "..."
                        )

                    print(
                        f"P{local_no:02} "
                        f"q={quote_count:<2} "
                        f"start={int(starts_quote)} "
                        f"doc={int(document)} "
                        f"pron={int(pronoun_attr)} "
                        f"lead={leadin or '-':20} "
                        f"=> {resolved or '?':20} "
                        f"[{reason or '-'}]"
                    )

                    print(
                        "   ",
                        sample,
                    )


if __name__ == "__main__":
    main()
