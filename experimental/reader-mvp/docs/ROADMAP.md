# Reader MVP Roadmap

This roadmap is the operational source of truth.

Legend:

```text
DONE
ACTIVE
NEXT
LATER
DEFERRED
```

# Phase 0 - Stabilize v0.1 Specialized Extractor

## DONE - Real-book ingest

- TXT/MD/EPUB ingest
- chapter segmentation
- resume
- health/reporting
- TOC/frontmatter cleanup

## DONE - ACTION hardening

ACTION is frozen unless regression.

## DONE - SAY attribution hardening through i2

Completed:
- source-aware direct speech verification;
- old-prose speech runs;
- provenance completion/relocation safeguards;
- pronoun anchors;
- microbatch topology;
- semantic dedupe;
- containment dedupe;
- mixed-surface rejection;
- source-authoritative speaker repair;
- source-authoritative speaker discovery.

Known green state:
- 299 full offline tests;
- 34 ambiguity canaries;
- frozen SEG8/SEG11 replay PASS.

## ACTIVE - j1 mixed-surface SAY salvage

Goal:

```text
spoken + narrator + spoken
```

must be projected onto directly spoken SOURCE intervals without weakening mixed-surface rejection.

Acceptance:
- P25 can be recovered safely where source geometry supports it;
- narrator text never becomes SAY content;
- SEG11 precision does not regress;
- all existing canaries remain green.

## NEXT - Final SAY audit

After j1:
- real-book audit across first ten chapters;
- classify remaining misses;
- fix only general failures;
- freeze specialized SAY work.

---

# Phase 1 - Establish v0.2 Executable Semantic Microkernel

Status: NEXT after v0.1 freeze.

Do NOT start with SQLite.

Implement pure Python structures for:

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

Supporting pure functions:

```text
visible_evidence
identity_projection
truth_view
epistemic_access
epistemic_gap
resolve_then_aggregate
build_context_packet
```

Success condition:

```text
manual hostile fixtures are naturally representable
and queryable without special-case ontology hacks
```

---

# Phase 2 - Gate A: Human Representability

Use:

```text
docs/architecture/SEMANTIC_MEMORY_V0_2_RC1_2_HOSTILE_FIXTURES.md
```

Test:
- scope;
- nested attribution;
- conditionals;
- modality;
- quantification;
- identity reveal/retraction;
- unreliable narration;
- epistemic delay;
- contradiction;
- temporal uncertainty;
- technical rules;
- composition stress.

Do not freeze the final v0.2 contract yet.

Revise the kernel if repeated workarounds appear.

---

# Phase 3 - Gate C: Machine Emitability

Only after Gate A.

Compare:

```text
single-pass structured extraction
```

vs:

```text
coarse-to-fine extraction
```

Coarse-to-fine candidate:

Pass 1:
- mentions;
- referents;
- predications;
- evidence spans;
- attribution/negation/modality cues.

Pass 2:
- proposition assembly;
- scope;
- semantic contexts;
- identity;
- temporal constraints;
- ambiguity.

Measure:
- structural validity;
- scope accuracy;
- grounding accuracy;
- repeatability;
- repair rate;
- token cost;
- runtime.

Wire format is not frozen before this gate.

---

# Phase 4 - Gate D: Real-Chapter Economics

Use one real English chapter, about 5k-10k words.

Compare:

## A. Full semanticization

Deep parse the entire chapter.

## B. Progressive semanticization

Cheap base pass plus deep parsing only for hot regions.

## C. Retrieval-first semantic cache

SOURCE + lexical/vector retrieval + minimal persistent semantics + query-time deep parsing.

Measure:

```text
answer accuracy
evidence recall
false-world-fact rate
objects per 1000 words
input/output LLM tokens
wall-clock time
RAM/VRAM
storage bytes
ContextPacket size
source rescue rate
percentage of materialized semantics actually used
```

This gate determines the default semanticization policy.

---

# Phase 5 - Gate G: Proof Closure

Every factual answer must follow:

```text
SOURCE
→ Evidence
→ Derivation
→ semantic object / Proposition
→ ContextPacket.allowed_answer_claim
→ answer claim
→ final text
```

Test modes:

```text
template_grounded
constrained_llm
hybrid
```

Measure:
- unsupported answer claims;
- citation correctness;
- proof coverage;
- stance downgrade frequency.

Add mandatory:

```text
Resolve-Then-Aggregate
```

tests after identity reveal.

---

# Phase 6 - Gate H: Boundary Security

Hard invariant:

```text
Spoiler Leakage Rate = 0
```

Attack:
- semantic graph/cache;
- FTS;
- embeddings;
- raw SOURCE retrieval;
- identity projection;
- epistemic-access cache;
- contradiction/revision views;
- summaries/macros;
- answer stance side channels.

Test future:
- identity;
- identity retraction;
- death;
- betrayal;
- explanation;
- relationship;
- location.

No retrieval path searches invisible evidence first.

---

# Phase 7 - Freeze Semantic Distinctions

After A+C+D+G+H pass:

Freeze:
- Predication semantics;
- Proposition composition;
- SemanticContext semantics;
- Evidence/Derivation semantics;
- SemanticChange lifecycle;
- KnowledgeBoundary semantics;
- ContextPacket proof contract.

Still do NOT freeze:
- database layout;
- embedding backend;
- index layout;
- ranking weights;
- e-graph implementation;
- exact semanticization trigger thresholds.

This becomes semantic-memory v0.2 contract.

---

# Phase 8 - Semantic Storage

Only after semantic contract stability.

Initial storage candidate:

```text
SQLite
```

Why:
- local-first;
- transactions;
- easy audit/debug;
- FTS5;
- recursive queries;
- one-file deployment.

Logical planes:

```text
SOURCE
authoritative semantic plane
proof/derivation plane
lifecycle/change plane
disposable retrieval/index plane
cache/projection plane
```

Physical schema may optimize away some logical object boundaries.

---

# Phase 9 - Progressive Semanticization

Implement materialization triggers based on measurements.

Candidate triggers:
- query hit;
- important/repeated entity;
- ambiguity knot;
- temporal query;
- epistemic query;
- failed proof;
- scene/chapter compaction;
- repeated retrieval;
- explicit user request.

Semantic coverage is multi-axis, not one L0-L4 scalar.

---

# Phase 10 - Retrieval

Inside KnowledgeBoundary:

```text
structured semantic retrieval
FTS
embeddings
```

Raw retrieval remains a recall firewall.

A disposable retrieval plane may contain denormalized indexes not considered authoritative semantics.

---

# Phase 11 - ProjectionLens / Schema-on-Demand

Queries may create temporary semantic lenses.

Examples:
- office holding;
- character knowledge;
- magic rules;
- programming constraints;
- relationship changes;
- timeline;
- SAY/ACTION/KN compatibility views.

A lens never mutates the core ontology.

Successful lenses may be cached.

---

# Phase 12 - Context Compiler

Pipeline:

```text
Question
→ query classification
→ KnowledgeBoundary
→ ProjectionLens
→ VisibleEvidenceUniverse
→ identity/equivalence projection
→ semantic/raw retrieval
→ resolve/deduplicate
→ granularity selection
→ salience + diversity
→ ContextPacket
```

ContextPacket contains a proof slice and allowed factual claims.

---

# Phase 13 - Q&A Product

Required internal answer stances:

```text
answered
disputed
ambiguous
not_found
verified_not_stated
out_of_boundary
```

`verified_not_stated` only for closed/enumerable domains.

Spoiler-sensitive rendering may mask internal `out_of_boundary`.

Product-level high-value queries include:
- who is X?
- what happened?
- what changed?
- what does X know?
- what does the reader know that X does not?
- who said X?
- why did X act?
- where is X?
- what rule applies?
- what remains unresolved?
- what should I already know here?

---

# Phase 14 - Legacy v0.1 Projections

Map v0.2 semantics into:

```text
SAY
ACTION
KN
REL
ST
EV
```

Classify old tests:

```text
CONTRACT
BUG REGRESSION
LEGACY SNAPSHOT
```

Preserve intended behavior, not accidental formatting/legacy mistakes.

---

# Phase 15 - Book-Scale Compaction

Later, after chapter-scale success:

```text
BOOK
  ARC
    EPISODE
      SCENE
        DETAIL
          SOURCE
```

Every compacted memory retains proof links downward.

Context compiler chooses granularity and drills down when required.

---

# Research Backlog - Not Foundations

## Potential

- specialized long-document coreference;
- FrameNet/SRL/dependency adapters;
- proposition structural interning;
- packed ambiguity;
- e-graph query equivalence;
- temporal reasoner;
- Datalog;
- vector filtering strategies;
- state-delta optimization;
- spatial reasoning;
- causal reasoning.

## Rule

No component becomes mandatory because it is academically elegant or available on pip.

It must solve a measured failure at acceptable cost.

---

# Current Next Action

```text
j1 mixed-surface SAY salvage
```

After j1 and final SAY freeze:

```text
build pure-Python rc1.2 semantic microkernel
```
