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

## DONE - j1 mixed-surface SAY salvage

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

## FROZEN - Specialized SAY

Specialized SAY extraction is frozen for rc1.2.

Completed:
- j1: mixed spoken/narrator quote-surface salvage;
- k1: SOURCE-authoritative quote-surface canonicalization;
- k2a: intra-segment post-run speaker continuity;
- k2b: cross-segment open-quote-run speaker continuity.

Validation:
- focused SAY regression suite: PASS;
- full offline suite: 324 PASS;
- compileall: PASS;
- frozen SEG8/SEG11 replay: PASS;
- fresh real-book canonical audit on book366: PASS;
- SEG9 canonical continuation: exactly 3 Lady Dunfern SAY records at P01/P01/P02;
- SEG9 P04 false-SAY leakage: none.

Precision rule:
- model proposes;
- immutable SOURCE proves;
- deterministic sanitizer decides canonical acceptance.

Do not extend SAY with additional heuristics unless a concrete
regression fixture demonstrates a general failure.

## FROZEN - BASE-G1 + BASE-C1 grounding firewall

The proven BASE firewall has two deliberately separate layers.

### G1 - canonical lexical grounding

G1a:
- removed concrete synthetic ACTION examples from the extraction prompt;
- added narrow SOURCE role support where positive lexical proof is available;
- kept persistence dumb: grounding happens before canonical commit.

G1b:
- rejects malformed pipe-shaped EV payloads at the final canonical boundary;
- rejects EV whose exact lexical surface occurs only inside direct-quote SOURCE;
- uses immutable SOURCE geometry;
- does not use broad semantic inference as a global grounding oracle.

Validation:
- book368: 12/12 selected segments done;
- known synthetic/example contamination: zero surviving canonical EV;
- known quote-surface garbage EV: zero survivors;
- pipe-shaped EV survivors: zero;
- G1b production quarantine: 16 deterministic drops.

### C1 - quote-only provenance topology

C1 covers semantic speech leakage that G1b cannot catch when a weak model
paraphrases direct speech into an EV.

Rule:

    provenance entirely inside direct speech
        -> cannot by itself establish canonical world EV

The decision uses SOURCE topology rather than semantic interpretation.
Mixed narration + speech paragraphs deliberately abstain.

Validation:
- authoritative offline suite: 355/355 PASS;
- compileall: PASS;
- git diff --check: PASS;
- book369: 12/12 selected segments done;
- one initial SEG9 needs_review was retried from an empty canonical ledger
  and passed on the next stochastic local-model run;
- C1 production quarantine: 19 EV drops;
- zero surviving EV for the known semantic-speech leaks:
  - I have given orders;
  - I was never thwarted in any way from acting;
  - Sir John confronts Irene about her changed behavior;
  - Irene Iddesleigh requests Sir John to have a seat opposite her;
- pipe-shaped EV survivors: zero;
- SAY is unchanged between book368 and book369: 58 total in both, with
  identical per-segment counts;
- EV totals are 245 -> 244; ordinary EV differential is not treated as
  deterministic evidence because the local model is stochastic.

Canonical flow:

    LLM proposal
        -> protocol / shape validation
        -> G1 lexical/canonical firewall
        -> C1 provenance-topology firewall
        -> canonical ledger OR quarantine/drop

The grounding decision uses immutable SOURCE and does not use previously
generated canonical observations as proof.

Scope limit:
- this does not prove that every possible unsupported BASE/world observation
  is solved;
- G1 covers its proven lexical/canonical failure classes;
- C1 covers quote-only provenance leakage;
- broader epistemic/context leakage remains a separate extraction-contract
  reliability problem.

Freeze rule:
- do not extend G1 or C1 without a concrete regression fixture demonstrating
  a general failure.

## NEXT - BASE extraction-contract reliability audit

Audit remaining cases where a model proposal acquires stronger canonical
world semantics than its SOURCE evidence permits.

Discover candidate failure classes from measured production failures rather
than inventing additional heuristics in advance.

After this reliability gate, continue toward the pure-Python rc1.2 semantic
microkernel.

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

    BASE extraction-contract reliability audit

G1 and C1 are frozen.

Investigate measured epistemic/context leakage classes outside quote-only
provenance without expanding the frozen firewalls by default.

After the BASE reliability gate:

    build pure-Python rc1.2 semantic microkernel
