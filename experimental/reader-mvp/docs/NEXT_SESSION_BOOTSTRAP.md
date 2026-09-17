# Next Session Bootstrap

Use this when continuing the project in a fresh chat/model session.

## Instruction to the next assistant

You are continuing work on:

```text
/home/romankozak/studio/public/it/ai-reading-assistant/experimental/reader-mvp
```

Do not redesign from scratch.

First read, in order:

```text
docs/CURRENT_STATE.md
docs/ROADMAP.md
docs/architecture/SEMANTIC_MEMORY_V0_2_RC1_2_FOUNDATION.md
docs/architecture/SEMANTIC_MEMORY_V0_2_RC1_2_VALIDATION.md
docs/architecture/SEMANTIC_MEMORY_V0_2_RC1_2_HOSTILE_FIXTURES.md
docs/DECISION_LOG.md
tail of docs/WORKLOG.md
```

Then inspect current git diff/status before proposing code.

## Current immediate task

If v0.1 j1 is not yet completed:

```text
implement j1 mixed-surface SAY salvage
```

Do not weaken the existing mixed-surface firewall.

The defect to fix is model output combining:

```text
spoken + narrator attribution + spoken
```

inside one candidate.

Correct architecture:

```text
candidate
→ align to SOURCE
→ project onto directly spoken quote intervals
→ discard narrator interval
→ ordinary speaker repair/source verification
```

Do not solve with a list of speech verbs or names from the fixture.

Run all relevant SAY/full regressions and the frozen SEG8/SEG11 replay.

After the final SAY audit, freeze specialized v0.1 SAY development.

## Then begin v0.2 executable prototype

Do NOT start with SQLite, embeddings, coreference models or LLM extraction.

Build a tiny pure-Python semantic laboratory around:

```text
Referent
Predication
Proposition DAG
SemanticContext
Evidence
Derivation
SemanticChange
KnowledgeBoundary
ContextPacket
```

plus pure functions:

```text
visible_evidence
identity_projection
truth_view
epistemic_access
epistemic_gap
resolve_then_aggregate
build_context_packet
```

Use the hostile fixtures manually.

Gate A must pass before machine extraction experiments.

## Architectural guardrails

Do not:
- reintroduce EVENT/STATE as competing universal storage languages;
- store direct Entity-to-Entity semantic edges as a second ontology;
- globally merge identity across reader boundaries;
- use external world knowledge as textual content;
- treat narrator assertion as automatic story truth;
- infer character knowledge as certain merely from presence;
- search future evidence then filter it after retrieval;
- interpret empty retrieval as proof of absence;
- freeze database/index technology before measurements;
- fully semanticize entire books by default without the Gate D comparison.

## Update docs after work

After meaningful progress:

```text
1. append docs/WORKLOG.md
2. update docs/CURRENT_STATE.md
3. update docs/ROADMAP.md if phase changed
4. append docs/DECISION_LOG.md if architecture changed
5. update this bootstrap if next task changed
```

No important decision should exist only in chat history.
