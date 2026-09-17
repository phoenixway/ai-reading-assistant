# Current Project State

Updated for semantic architecture **v0.2-rc1.2**.

This file is intentionally compact. Read it first after resuming work.

# 1. Project

Repository:

```text
/home/romankozak/studio/public/it/ai-reading-assistant/experimental/reader-mvp
```

Primary product direction:

```text
AI Reading Assistant
```

Current language scope for v0.2:

```text
English only
```

Primary local-model environment:

```text
llama.cpp
Gemma 3 4B class model for weak/local extraction experiments
RTX 4060 8 GB
```

A stronger local model may later be evaluated, but architecture must not depend on one specific model.

---

# 2. Frozen Architectural Principles from v0.1

The existing reading pipeline established several principles that remain valid:

```text
SOURCE immutable
LEDGER append-oriented
VIEWS rebuildable
provenance explicit
unresolved is safer than invented
false world fact is worse than missed fact
deterministic SOURCE verification can constrain weak LLM output
```

Current v0.1 extraction tags include:

```text
SUM WHO LOC TIME EV SAY ST KN REL TH+ TH- DET Q END
```

These are no longer assumed to be the universal v0.2 ontology.

They are expected to become legacy semantic projections/views.

---

# 3. ACTION Branch

ACTION work is considered frozen unless a regression appears.

Existing architecture includes:
- actuality firewall;
- terminal evidence handling;
- literal complement completion;
- subject/object bridges;
- coordinated-tail repair;
- ACTION-GAP;
- novelty/source-role firewall.

Do not continue lexical ACTION specialization without a demonstrated general failure.

---

# 4. SAY Branch

SAY has undergone extensive real-book hardening.

Important completed capabilities include:
- old-prose multi-paragraph speech runs;
- source-aware attribution;
- provenance repair;
- document-vs-spoken distinction;
- pronoun-chain attribution;
- full-segment verifier source map;
- semantic dedupe;
- provenance relocation firewall;
- source-authoritative run speaker repair;
- source-authoritative run speaker discovery;
- mixed spoken/narrator surface rejection;
- SOURCE-bounds containment dedupe.

Important frozen real-book behavior:

## SEG8

Sir John speech run P13-P22 is recovered.

Lady Dunfern run P26-P30 is recovered through source-authoritative speaker discovery.

## SEG11

Sir John P19-P23 remains recovered.

Written document content remains rejected as SAY.

Unsafe P31/P32 attribution remains abstained.

Last known deterministic frozen replay:

```text
SEG 8 FROZEN SAFETY ASSERTIONS: PASS
SEG 11 FROZEN SAFETY ASSERTIONS: PASS
FROZEN SEG8/SEG11 REPLAY: PASS
```

Last known offline regression state after i2:

```text
focused:             106 passed
SAY regression:      174 passed
ambiguity canaries:   34 passed
full offline:        299 passed
compileall:          OK
```

---

# 5. Current v0.1 Task

One important SAY defect remains explicitly identified:

```text
j1 mixed-surface salvage
```

Canonical example, SEG8 P25:

```text
"Sir and husband," she said, with great nervousness at first,
"you have summoned me hither ..."
```

The weak model merges:

```text
spoken
+ narrator attribution
+ spoken
```

into one SAY candidate.

Current h1 correctly rejects it as mixed surface.

j1 should:
- preserve h1 precision;
- project the candidate onto SOURCE quote surfaces;
- salvage only the directly spoken intervals;
- leave narrator text outside spoken content;
- allow existing source-authoritative speaker machinery to resolve Lady Dunfern;
- avoid lexical/speaker-specific hardcoding.

After j1:
1. run focused tests;
2. run full SAY regression;
3. run ambiguity canaries;
4. run full offline suite;
5. run frozen SEG8/SEG11 replay;
6. perform one final real-book SAY audit;
7. freeze specialized SAY development.

---

# 6. v0.2 Strategic State

The universal architecture has moved through several iterations and is currently:

```text
v0.2-rc1.2
```

The current foundation is NOT a frozen storage schema.

Core direction:

```text
SOURCE
  ↓
cheap structural indexes
  ↓
progressively materialized semantic cache
  ↓
query-specific semantic expansion
  ↓
ContextPacket
  ↓
grounded answer
```

The current semantic kernel is centered on:

```text
Mention / Referent
Predication
Proposition DAG
SemanticContext
Evidence / Derivation
SemanticChange
KnowledgeBoundary
ContextPacket
```

Major accepted principles:
- Predication is the universal semantic atom.
- EVENT/STATE are derived classifications, not fundamental ontology forks.
- Proposition structure preserves scope, negation, modality and composition.
- Truth is a context/query-time projection, not a global stored bit.
- Identity is evidence- and boundary-dependent.
- Proposition structural hash is boundary-independent.
- Equivalence is a separate boundary/query-time projection.
- Character epistemic access is defeasible and derived.
- One lifecycle mechanism (`SemanticChange`) handles retraction/supersession/etc.
- Contradictions are explicit/auditable.
- Every retrieval path obeys KnowledgeBoundary before searching.
- Semantic memory is a cache over SOURCE, not a full semantic transcription.
- Deep semantics are materialized progressively.
- ContextPacket is the answer security boundary.
- Empty retrieval does not prove absence.

---

# 7. v0.2 Next Implementation Target

Do NOT implement the database schema yet.

Do NOT add:
- embeddings;
- fastcoref;
- FrameNet;
- Datalog;
- HNSW;
- graph DB.

Build a pure-Python executable semantic laboratory containing only the smallest useful kernel:

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

plus pure functions approximating:

```text
visible_evidence(boundary)
identity_projection(boundary)
truth_view(proposition, boundary)
epistemic_access(subject, proposition, boundary)
epistemic_gap(subject, proposition, boundary)
resolve_then_aggregate(query, boundary)
build_context_packet(query, boundary)
```

Initial goal:

```text
the executable kernel can represent and query hostile manual fixtures
```

before any LLM extraction is connected.

---

# 8. Critical v0.2 Gates

Only five gates currently block architecture freeze:

```text
Gate A  Human representability
Gate C  Machine emitability
Gate D  Real-chapter economics
Gate G  Proof closure through final answer
Gate H  Boundary/spoiler security
```

See:

```text
architecture/SEMANTIC_MEMORY_V0_2_RC1_2_VALIDATION.md
```

---

# 9. Explicitly Deferred

Do not promote these to foundations without measurements:

```text
e-graph implementation
Datalog/SAT/SMT
formal state delta streams
formal causal reasoner
formal spatial reasoner
bitmask-filtered HNSW
mandatory full-document deep semantic parsing
mandatory NLP ensemble
graph database
```

---

# 10. Immediate Next Sequence

```text
1. implement j1 mixed-surface SAY salvage
2. final SAY audit
3. freeze specialized v0.1 semantic extraction work
4. implement tiny pure-Python rc1.2 semantic microkernel
5. manually encode hostile fixtures
6. add composition stress fixture
7. only after Gate A, test local model machine emitability
```
