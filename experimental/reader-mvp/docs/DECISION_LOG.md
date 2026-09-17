# Architecture Decision Log

Append-only.

Format:

```text
## ADR-XXX - Title
Status:
Date:
Decision:
Why:
Consequences:
Supersedes:
```

---

## ADR-001 - SOURCE is authoritative

Status: accepted

Decision:

SOURCE text and stable spans are immutable. Semantic representations are derived and rebuildable.

Why:

A weak model may miss or misinterpret content. The project must never lose original evidence.

Consequences:

- semantic memory cannot replace SOURCE;
- every grounded semantic object must link back to SOURCE or a documented derivation;
- improved models can rebuild semantic caches later.

---

## ADR-002 - False world facts are more dangerous than missed facts

Status: accepted

Decision:

Precision and abstention take priority over forcing extraction completeness.

Consequences:

`unknown`, `ambiguous`, `not_found`, and unresolved identity are legitimate outcomes.

---

## ADR-003 - Legacy SAY/ACTION/etc. become projections

Status: accepted

Decision:

The existing v0.1 tags remain useful but are not the universal v0.2 ontology.

Consequences:

Existing code/tests are preserved as compatibility and regression layers.

---

## ADR-004 - English-only for v0.2

Status: accepted

Decision:

v0.2 extraction/evaluation targets English only.

Consequences:

No multilingual adapter work is required now. Language metadata may still store `en`.

---

## ADR-005 - Predication is the universal semantic atom

Status: accepted provisionally in rc1+

Decision:

Use one general `Predication(predicate, arguments, context, grounding)` substrate.

EVENT/STATE/relation/property are classifications or projections rather than fundamental storage forks.

Why:

The EVENT/STATE split becomes ambiguous for many English constructions and encourages parallel semantics.

---

## ADR-006 - Proposition semantics are compositional DAGs

Status: accepted provisionally

Decision:

Negation, conjunction, disjunction, conditionals, modality and quantification belong in compositional proposition structure.

Propositions are shared DAG objects where practical.

Consequences:

Negation scope is preserved.

`John did not promise to leave` differs structurally from `John promised not to leave`.

---

## ADR-007 - Truth is a projection, not a global stored bit

Status: accepted

Decision:

Semantic content exists under contexts and perspectives.

`narrated(P)` does not automatically mean `story_truth(P)`.

Consequences:

Unreliable narration, dreams, embedded documents and later revision can be represented without overwriting content.

---

## ADR-008 - Identity is boundary-aware

Status: accepted

Decision:

Do not irreversibly merge semantic entities/referents based on later revelations.

Identity assertions are semantic content with evidence and visibility.

Consequences:

A masked identity can remain unresolved for an earlier reader boundary while resolved later.

---

## ADR-009 - Structural proposition hash is boundary-independent

Status: accepted

Decision:

If structural interning/hashing is used, it is based on stable raw representation IDs.

Boundary-dependent identity equivalence is a separate projection.

Why:

Recomputing hashes after every identity reveal would make storage unstable and mix structure with epistemic knowledge.

Consequences:

Aggregation must perform explicit resolve-then-aggregate under the active boundary.

---

## ADR-010 - Semantic memory is a cache over SOURCE

Status: accepted

Decision:

Do not fully semanticize every document by default.

Semantic memory is incrementally/progressively materialized where useful.

Consequences:

The project must experimentally compare full semanticization, progressive semanticization and retrieval-first semantic caching.

---

## ADR-011 - Grounding is proof-carrying

Status: accepted

Decision:

Derived semantic objects retain a recoverable chain:

```text
semantic object
← derivation
← evidence
← SOURCE
```

Consequences:

Answer verification can reconstruct proof slices.

---

## ADR-012 - World knowledge for reference is not world knowledge as content

Status: accepted

Decision:

External knowledge may help resolve a referent but does not become textual content unless independently grounded.

---

## ADR-013 - One semantic lifecycle mechanism

Status: accepted in rc1.2

Decision:

Use an append-only `SemanticChange` mechanism for assert/retract/supersede/confirm/reinterpret/invalidate/resolve/reopen.

Do not build separate lifecycle ledgers for identity, contradiction and epistemic access.

Consequences:

Semantic objects and lifecycle history remain distinct.

---

## ADR-014 - Epistemic access is derived and defeasible

Status: accepted in rc1.1+

Decision:

Presence/participation may support an epistemic-access inference but must not automatically create a canonical `know()` fact.

Consequences:

Character knowledge queries can use derivation while allowing later defeating evidence.

---

## ADR-015 - Contradictions are explicit and auditable

Status: accepted

Decision:

Conflicting propositions are represented and classified through a contradiction view/relation rather than silently resolved.

Extraction fixes remain lifecycle/supersession issues, not narrative contradiction.

---

## ADR-016 - KnowledgeBoundary applies before retrieval

Status: accepted

Decision:

All semantic, FTS, vector and raw-source retrieval for spoiler-sensitive queries must operate only inside the visible evidence universe.

Consequences:

No future passage may be retrieved first and filtered later.

---

## ADR-017 - ContextPacket is the answer security boundary

Status: accepted in rc1.1+

Decision:

The answer model receives a bounded ContextPacket with allowed answer claims and proof/evidence.

Consequences:

Proof discipline must continue through final synthesis.

Unsupported answer claims are verification failures.

---

## ADR-018 - Empty retrieval does not prove absence

Status: accepted

Decision:

`not_found` is the normal negative stance for open-world textual questions.

`verified_not_stated` is allowed only in closed/enumerable domains with an explicit negative-verification procedure.

---

## ADR-019 - Resolve before aggregate

Status: accepted in rc1.2

Decision:

Count/list/group queries whose entities/propositions may become equivalent after visible identity resolution must compute the active equivalence view before aggregation.

Consequences:

Stable proposition hashes can coexist with boundary-dependent identity.

---

## ADR-020 - Do not freeze the v0.2 wire format before machine emitability

Status: accepted

Decision:

Human representability comes first, then weak/local-model emission testing, then wire-format freeze.

Why:

A mathematically elegant representation that weak local models cannot reliably emit is an architectural signal, not merely a prompt problem.

---

## ADR-021 - Current architecture label is v0.2-rc1.2

Status: current

Decision:

rc1.2 is ready for executable prototype pressure but is not the final v0.2 contract.

Promotion requires Gates A, C, D, G and H.
