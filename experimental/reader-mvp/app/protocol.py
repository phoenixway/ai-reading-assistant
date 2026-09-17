from __future__ import annotations
import re
from dataclasses import dataclass, field
from .textutil import norm, slug

DEVELOPER_FAST = r"""Reasoning: low
You analyze ONE fragment of fiction and extract observations as tagged lines.
Do not invent. Do not add facts absent from the fragment.
Reply ONLY with tagged lines that start DIRECTLY with one of the tags below, for example `SUM:` or `EV:`.
Do NOT write the word `TAG`. No markdown, no introduction, no conclusion.
One observation per line. Omit a tag if it does not apply.

TAGS
SUM: <2-3 factual sentences about what happened>
WHO: <known ids or names, comma-separated>
LOC: <physical scene setting only; not an object, container, body part, or clothing>
TIME: <time or interval>
EV: <one event, <=15 words> @P01
SAY: <who> | <what they assert> @P01
ST: <who> | <state field> | <new/current state> @P01
KN: <who> | <knowledge newly acquired DURING this fragment> | <source> @P01
REL: <who> -> <to whom> | <type> | <reason <=8 words> @P01
TH+: <new unresolved question/thread>
TH-: <thread resolved> | <how>
DET: <specific named object, number, promise, concrete odd detail> | <note> @P01
Q: <quote <=15 words> @P01
END: present=<id,...> | loc=<physical scene setting at END> | situation=<literal situation at the END of fragment> @P01

REL TYPES ONLY
help | trust_gain | trust_loss | lie_revealed | shared_secret | threat | betrayal | sacrifice | reconciliation | distance
If none fits exactly, OMIT REL. Never invent a new relation type.

RULES
1. Input paragraphs are labeled [P01], [P02], ... . Every EV/SAY/ST/KN/REL/DET/Q/END line MUST end with the exact paragraph reference copied from the fragment, for example @P03. Multiple references: @P03-05 or @P03,@P07. NEVER write @NN, @name, or omit the reference.
2. If a CHARACTER asserts something, use SAY, not EV/ST as world fact.
3. Epistemic marker is explicit: append ~INF before the @ reference for an inference, or ~HYP for a weak hypothesis. Example: ST: Kira | emotion | worried ~INF @P03. Never use ordinary question-mark punctuation as an epistemic marker.
4. Prefer ids from KNOWN. A new person may be written exactly as named in the text.
5. ST records the state of the entity actually described. Do not turn another character's state into the subject's state.
6. KN means knowledge ACQUIRED in this fragment. Do not emit KN merely because the text says someone already knew something earlier.
7. LOC and END.loc are scene locations. A stove, coat, envelope, notebook, body part, etc. is not a location unless the scene literally takes place there.
8. END describes the FINAL lines, not the main event. END MUST cite the final substantive paragraph of the fragment. END is mandatory unless a TASK OVERRIDE explicitly excludes END from the allowed output tags.
9. EV COMPLETENESS: emit a separate EV for each explicit material action that can matter later: acquiring/handing/keeping/destroying an object, opening/closing something, reading/discovering evidence, entering/leaving, following, promising, attacking, helping, hiding, revealing, etc. One paragraph may require several EV lines. Do not use SUM, DET, or END as a substitute for these events.
10. Give the FINAL SUBSTANTIVE PARAGRAPH special attention. Preserve its explicit material actions individually before writing END.
11. SAY speaker must be the character who actually speaks the words. A question asked by one character is SAY by that character. Text written in a note, letter, sign, message, or document is NOT SAY unless a character actually speaks it aloud; use DET or Q for document text.
12. ST is for an explicit state of the entity. Behavior such as looking, hesitating, staying silent, or handling an object is not automatically an emotion or personality state. If a state is only inferred, mark ~INF; omit weak guesses.
13. REL requires evidence of an actual relationship event matching the closed type. Embarrassment, hesitation, silence, awkwardness, or failure to correct someone do NOT by themselves imply trust_loss, distance, or another REL.
14. Provenance must point to the paragraph where the extracted fact/action/detail actually occurs, not an earlier paragraph where the same object or person was introduced.
15. END.loc is the physical location of the characters at the END. If the location is not explicit, leave the value empty as `loc=`. Never borrow another character's destination as the scene location.

"""

TAG_RE = re.compile(r'^\s*(SUM|WHO|LOC|TIME|EV|SAY|ST|KN|REL|TH\+|TH-|DET|Q|END)\s*:\s*(.+?)\s*$', re.I)
REF_BLOCK_RE = re.compile(r'\s+((?:@P?\d{1,3}(?:\s*-\s*(?:@P?)?\d{1,3})?)(?:\s*,\s*@P?\d{1,3}(?:\s*-\s*(?:@P?)?\d{1,3})?)*)\s*$', re.I)
CONTENT_TAGS = {'EV','SAY','ST','KN','REL','TH+','TH-','DET','Q'}
NEEDS_SPAN = {'EV','SAY','ST','KN','REL','DET','Q','END'}
REL_TYPES = {'help','trust_gain','trust_loss','lie_revealed','shared_secret','threat','betrayal','sacrifice','reconciliation','distance'}

@dataclass
class Record:
    tag: str
    payload: str
    spans: list[int] = field(default_factory=list)
    epistemic: str = 'EXPLICIT'
    raw: str = ''

@dataclass
class Parsed:
    records: list[Record]
    ignored: list[str]
    quarantined: list[tuple[str,str]]
    stats: dict
    contract_pass: bool


def _expand_span_spec(spec: str) -> list[int]:
    out = []
    for part in re.split(r'\s*,\s*', spec):
        part = re.sub(r'@?P?', '', part, flags=re.I).strip()
        if '-' in part:
            a,b = [int(x) for x in part.split('-',1)]
            out.extend(range(min(a,b), max(a,b)+1))
        elif part:
            out.append(int(part))
    return sorted(set(out))

def parse_output(text: str, valid_local_nos: set[int], *, allowed_tags: set[str] | None = None,
                 required_tags: set[str] | None = None, min_content: int = 1,
                 required_end_span: int | None = None) -> Parsed:
    records: list[Record] = []
    ignored: list[str] = []
    quarantined: list[tuple[str,str]] = []
    needed_span = 0
    valid_span = 0
    tags = set()
    repaired_prefix = 0
    disallowed = 0
    shape_invalid = 0
    end_tail_miss = 0

    required_tags = {'SUM','WHO','END'} if required_tags is None else set(required_tags)
    allowed_tags = set(allowed_tags) if allowed_tags is not None else None

    for line in text.splitlines():
        if not line.strip():
            continue

        clean_line = line

        if re.match(r'^\s*TAG\s*:', clean_line, re.I):
            clean_line = re.sub(
                r'^\s*TAG\s*:\s*',
                '',
                clean_line,
                count=1,
                flags=re.I,
            )
            repaired_prefix += 1

        m = TAG_RE.match(clean_line)

        if not m:
            ignored.append(line)
            continue

        tag, val = m.group(1).upper(), m.group(2).strip()

        if allowed_tags is not None and tag not in allowed_tags:
            disallowed += 1
            continue

        spans = []

        sm = REF_BLOCK_RE.search(val)
        if sm:
            spans = _expand_span_spec(sm.group(1))
            val = val[:sm.start()].strip()

        epi = 'EXPLICIT'

        em = re.search(r'\s+~(INF|HYP)\s*$', val, re.I)
        if em:
            epi = 'INFERRED' if em.group(1).upper() == 'INF' else 'HYPOTHESIS'
            val = val[:em.start()].strip()

        if tag in NEEDS_SPAN:
            needed_span += 1

            if spans and all(x in valid_local_nos for x in spans):
                valid_span += 1
            else:
                quarantined.append((line, 'missing or invalid @Pxx'))
                continue

        # Structured payload validation. A syntactically recognized tag is
        # not allowed to satisfy the contract unless its payload has the
        # canonical shape expected by downstream projections.
        if tag in {'SAY', 'ST', 'KN'}:
            expected_parts = {
                'SAY': 2,
                'ST': 3,
                'KN': 3,
            }[tag]
            parts = [x.strip() for x in val.split('|')]

            if len(parts) != expected_parts or any(not x for x in parts):
                quarantined.append(
                    (line, f'invalid {tag} payload shape')
                )
                shape_invalid += 1
                continue

        if tag == 'REL':
            parts = [x.strip() for x in val.split('|')]
            rel_type = parts[1] if len(parts) >= 2 else ''
            left = parts[0] if parts else ''
            endpoints = [x.strip() for x in left.split('->')] if '->' in left else []

            if (
                len(parts) != 3
                or any(not x for x in parts)
                or rel_type not in REL_TYPES
                or len(endpoints) != 2
                or any(not x for x in endpoints)
            ):
                reason = (
                    f'invalid REL type: {rel_type or "(missing)"}'
                    if rel_type not in REL_TYPES
                    else 'invalid REL payload shape'
                )
                quarantined.append((line, reason))
                shape_invalid += 1
                continue

        if tag == 'END':
            fields = {}
            valid_shape = True

            for part in val.split('|'):
                part = part.strip()
                if '=' not in part:
                    valid_shape = False
                    break

                key, value = part.split('=', 1)
                key = key.strip()
                value = value.strip()

                if not key or key in fields:
                    valid_shape = False
                    break

                fields[key] = value

            if not valid_shape or set(fields) != {'present', 'loc', 'situation'}:
                quarantined.append(
                    (line, 'invalid END payload shape; expected present= | loc= | situation=')
                )
                shape_invalid += 1
                continue

            if required_end_span is not None and required_end_span not in spans:
                quarantined.append(
                    (
                        line,
                        f'END must reference final substantive paragraph @P{required_end_span:02}',
                    )
                )
                end_tail_miss += 1
                continue

        tags.add(tag)
        records.append(Record(tag, val, spans, epi, line))

    lines = max(1, sum(1 for x in text.splitlines() if x.strip()))

    span_validity = valid_span / needed_span if needed_span else 1.0
    junk_ratio = len(ignored) / lines

    content_count = sum(
        1 for r in records
        if r.tag in CONTENT_TAGS
    )

    contract = (
        required_tags.issubset(tags)
        and content_count >= min_content
        and junk_ratio <= .25
        and span_validity >= .80
    )

    stats = dict(
        parsed=len(records),
        ignored=len(ignored),
        quarantined=len(quarantined),
        no_span=needed_span-valid_span,
        span_needed=needed_span,
        span_valid=valid_span,
        span_validity=span_validity,
        junk_ratio=junk_ratio,
        content_count=content_count,
        repaired_prefix=repaired_prefix,
        disallowed=disallowed,
        shape_invalid=shape_invalid,
        end_tail_miss=end_tail_miss,
    )

    return Parsed(
        records,
        ignored,
        quarantined,
        stats,
        contract,
    )


def merge_parsed(parts: list[Parsed], contract_pass: bool) -> Parsed:
    seen = set()
    records = []

    for p in parts:
        for r in p.records:
            key = (
                r.tag,
                r.payload,
                tuple(r.spans),
                r.epistemic,
            )

            if key not in seen:
                seen.add(key)
                records.append(r)

    ignored = [
        x
        for p in parts
        for x in p.ignored
    ]

    quarantined = [
        x
        for p in parts
        for x in p.quarantined
    ]

    needed = sum(
        p.stats.get('span_needed', 0)
        for p in parts
    )

    valid = sum(
        p.stats.get('span_valid', 0)
        for p in parts
    )

    stats = {
        'parsed': len(records),
        'ignored': len(ignored),
        'quarantined': len(quarantined),
        'no_span': needed - valid,
        'span_needed': needed,
        'span_valid': valid,
        'span_validity': valid / needed if needed else 1.0,
        'junk_ratio': (
            0.0
            if not ignored
            else len(ignored) / max(1, len(ignored) + len(records))
        ),
        'content_count': sum(
            1 for r in records
            if r.tag in CONTENT_TAGS
        ),
        'repaired_prefix': sum(
            p.stats.get('repaired_prefix', 0)
            for p in parts
        ),
        'disallowed': sum(
            p.stats.get('disallowed', 0)
            for p in parts
        ),
        'shape_invalid': sum(
            p.stats.get('shape_invalid', 0)
            for p in parts
        ),
        'end_tail_miss': sum(
            p.stats.get('end_tail_miss', 0)
            for p in parts
        ),
    }

    return Parsed(
        records,
        ignored,
        quarantined,
        stats,
        contract_pass,
    )

def entity_id(name: str) -> str:
    return slug(name)

def fact_key(tag: str, payload: str) -> str:
    # deliberately simple v0.1 key; replace after benchmark if claim matching needs it
    base = norm(payload)
    return f"{tag.lower()}:{' '.join(base.split()[:8])}"
