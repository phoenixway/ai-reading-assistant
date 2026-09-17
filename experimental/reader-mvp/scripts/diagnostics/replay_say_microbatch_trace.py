from __future__ import annotations

import re
import sys
from pathlib import Path

from app.db import connect
from app.protocol import (
    merge_parsed,
    parse_output,
)
from app.reader import (
    _repair_say_missing_provenance,
    _sanitize_say_coverage,
    _say_coverage_batches,
    _say_segment_source_rows,
    _select_say_coverage_rows,
)


BOOK_ID = 364


SEG_HEADER_RE = re.compile(
    r"(?m)^SEG (?P<idx>\d+) "
    r"chapter=.*$"
)

BATCH_RAW_RE = re.compile(
    r"(?ms)^--- BATCH "
    r"(?P<batch>\d+) RAW ---\n"
    r"(?P<raw>.*?)"
    r"^elapsed:\s"
)


def segment_blocks(
    text: str,
):
    matches = list(
        SEG_HEADER_RE.finditer(
            text
        )
    )

    for pos, match in enumerate(
        matches
    ):
        start = match.end()

        if pos + 1 < len(matches):
            end = matches[
                pos + 1
            ].start()
        else:
            end = len(text)

        yield (
            int(
                match.group(
                    "idx"
                )
            ),
            text[
                start:end
            ],
        )


def raw_batches(
    block: str,
):
    result = []

    for match in BATCH_RAW_RE.finditer(
        block
    ):
        result.append(
            (
                int(
                    match.group(
                        "batch"
                    )
                ),
                match.group(
                    "raw"
                ).rstrip(),
            )
        )

    return result


def print_records(
    records,
):
    if not records:
        print("(none)")
        return

    for i, record in enumerate(
        records,
        start=1,
    ):
        print(
            f"{i:02}. "
            f"{record.tag}: "
            f"{record.payload} "
            f"@{record.spans}"
        )


def speaker_of(
    record,
):
    if (
        record.tag != "SAY"
        or "|" not in record.payload
    ):
        return None

    return (
        record.payload.split(
            "|",
            1,
        )[0].strip()
    )


def replay_segment(
    idx: int,
    trace_batches,
):
    with connect() as con:
        seg = con.execute(
            """
            SELECT *
            FROM segments
            WHERE book_id=?
              AND idx=?
            """,
            (
                BOOK_ID,
                idx,
            ),
        ).fetchone()

        if seg is None:
            raise AssertionError(
                f"missing SEG {idx}"
            )

        source_rows = list(
            _say_segment_source_rows(
                con,
                seg["id"],
            )
        )

    source_by_local = {
        int(row["local_no"]):
            (row["text"] or "")
        for row in source_rows
    }

    targets = (
        _select_say_coverage_rows(
            source_rows
        )
    )

    batches = (
        _say_coverage_batches(
            targets
        )
    )

    if len(trace_batches) != len(
        batches
    ):
        raise AssertionError(
            f"SEG {idx}: trace has "
            f"{len(trace_batches)} batches, "
            f"current selector has "
            f"{len(batches)}"
        )

    parsed_parts = []
    provenance_completed = 0

    print()
    print(
        "=" * 118
    )
    print(
        f"SEG {idx} "
        "FROZEN RAW → CURRENT PIPELINE"
    )
    print(
        "=" * 118
    )

    for (
        expected_batch_index,
        batch,
    ), (
        trace_batch_index,
        raw,
    ) in zip(
        enumerate(
            batches,
            start=1,
        ),
        trace_batches,
        strict=True,
    ):
        if (
            expected_batch_index
            != trace_batch_index
        ):
            raise AssertionError(
                f"SEG {idx}: expected batch "
                f"{expected_batch_index}, "
                f"trace says "
                f"{trace_batch_index}"
            )

        batch_nos = [
            int(
                target[
                    "local_no"
                ]
            )
            for target in batch
        ]

        batch_source = {
            int(target["local_no"]):
                (target["text"] or "")
            for target in batch
        }

        (
            repaired_raw,
            completed,
        ) = _repair_say_missing_provenance(
            raw,
            batch_source,
        )

        provenance_completed += (
            completed
        )

        parsed = parse_output(
            repaired_raw,
            set(
                batch_nos
            ),
            allowed_tags={
                "SAY",
            },
            required_tags=set(),
            min_content=0,
        )

        parsed_parts.append(
            parsed
        )

        print(
            f"BATCH {expected_batch_index:02}: "
            f"targets={batch_nos} "
            f"raw→parsed="
            f"{len(parsed.records)} "
            f"d2a={completed}"
        )

    if len(parsed_parts) == 1:
        merged = parsed_parts[0]
    else:
        merged = merge_parsed(
            parsed_parts,
            all(
                part.contract_pass
                for part in parsed_parts
            ),
        )

    print()
    print(
        "--- MERGED BEFORE SANITIZER ---"
    )
    print(
        "records:",
        len(
            merged.records
        ),
    )
    print(
        "quarantined:",
        len(
            merged.quarantined
        ),
    )
    print(
        "d2a completed:",
        provenance_completed,
    )

    clean = _sanitize_say_coverage(
        merged,
        source_by_local,
    )

    print()
    print(
        "--- CURRENT SURVIVORS ---"
    )

    print_records(
        clean.records
    )

    print()
    print(
        "--- CURRENT STATS ---"
    )

    for key in [
        "say_provenance_relocated",
        "say_speaker_rewritten",
        "say_conflict_dropped",
        "say_conflict_resolved",
        "say_document_dropped",
        "say_unsupported_dropped",
        "say_speaker_surface_dropped",
        "say_duplicate_dropped",
        "say_containment_duplicate_dropped",
        "say_direct_supported",
        "say_indirect_supported",
        "say_source_supported",
    ]:
        print(
            f"{key}:",
            clean.stats.get(
                key,
                0,
            ),
        )

    print(
        "say_provenance_completed:",
        provenance_completed,
    )

    return (
        source_by_local,
        clean,
    )


def safety_assertions(
    idx: int,
    clean,
):
    say_records = [
        record
        for record in clean.records
        if record.tag == "SAY"
    ]

    speakers = {
        speaker_of(
            record
        )
        for record in say_records
    }

    spans = {
        span
        for record in say_records
        for span in record.spans
    }

    if idx == 8:
        forbidden = {
            "Silas",
            "Irene",
            "Duchess of Nante",
            "Lady Dunfern",
            "Earl Peden",
            "Lady Dilworth",
            "I",
            "he",
            "she",
        }

        assert not (
            speakers
            & forbidden
        ), (
            "SEG8 wrong speaker survived: "
            f"{speakers & forbidden}"
        )

        # Frozen trace contains model proposals throughout the
        # long Sir John run P13-P22. Current deterministic source
        # logic should recover speaker continuity across it.
        expected = set(
            range(
                13,
                23,
            )
        )

        missing = (
            expected
            - spans
        )

        assert not missing, (
            "SEG8 missing recovered "
            f"Sir John run spans: "
            f"{sorted(missing)}"
        )

        for record in say_records:
            if any(
                13 <= span <= 22
                for span in record.spans
            ):
                assert (
                    speaker_of(
                        record
                    )
                    == "Sir John"
                ), record

    elif idx == 11:
        forbidden = {
            "Sir Sydney",
            "Kathleen",
            "Rodney Rupert",
            "Edward",
        }

        assert not (
            speakers
            & forbidden
        ), (
            "SEG11 wrong speaker survived: "
            f"{speakers & forbidden}"
        )

        # P18 frozen proposal crosses direct speech ->
        # narrator attribution -> direct speech, so h1
        # precision firewall intentionally rejects it.
        #
        # P19 provides an independent clean Sir John seed and
        # P19-P23 remain recoverable as the grounded open run.
        expected = set(
            range(
                19,
                24,
            )
        )

        missing = (
            expected
            - spans
        )

        assert not missing, (
            "SEG11 missing recovered "
            f"Sir John run spans: "
            f"{sorted(missing)}"
        )

        for record in say_records:
            if any(
                18 <= span <= 23
                for span in record.spans
            ):
                assert (
                    speaker_of(
                        record
                    )
                    == "Sir John"
                ), record

        # Mixed narrator material must never survive inside
        # canonical spoken content.
        assert all(
            "said Sir John"
            not in record.payload
            for record in say_records
        )

        assert all(
            "here Sir John pointed to the wardrobe"
            not in record.payload
            for record in say_records
        )

        # Christmas card stays document, not SAY.
        assert 5 not in spans, (
            "SEG11 P05 document "
            "survived as SAY"
        )

        # No positive source anchor for the later
        # "said he" run yet. g/g1 must abstain.
        assert 31 not in spans
        assert 32 not in spans


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: replay_say_microbatch_trace.py "
            "/path/to/say-trace.txt"
        )

    path = Path(
        sys.argv[1]
    )

    text = path.read_text(
        encoding="utf-8"
    )

    blocks = dict(
        segment_blocks(
            text
        )
    )

    wanted = [
        8,
        11,
    ]

    for idx in wanted:
        if idx not in blocks:
            raise AssertionError(
                f"trace missing SEG {idx}"
            )

        batches = raw_batches(
            blocks[
                idx
            ]
        )

        _sources, clean = (
            replay_segment(
                idx,
                batches,
            )
        )

        safety_assertions(
            idx,
            clean,
        )

        print()
        print(
            f"SEG {idx} "
            "FROZEN SAFETY ASSERTIONS: "
            "PASS"
        )

    print()
    print(
        "=" * 118
    )
    print(
        "FROZEN SEG8/SEG11 REPLAY: PASS"
    )
    print(
        "=" * 118
    )


if __name__ == "__main__":
    main()
