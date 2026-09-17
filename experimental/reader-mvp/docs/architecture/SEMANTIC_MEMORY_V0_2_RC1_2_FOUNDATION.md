# Semantic Memory v0.2-rc1.2 Foundation

Status: **provisional architecture kernel, ready for executable prototype pressure**  
Language scope: **English only**  
Primary record of truth: **immutable SOURCE**

This document consolidates the accepted architecture through rc1.2.

It intentionally defines semantic distinctions and invariants more strongly than storage layout.

The v0.2 wire/database format is NOT frozen.

---

# 1. Product Goal

Build a local-first Reading Assistant that can work over long English text and answer grounded questions such as:

```text
Who is X?
What happened?
What changed?
What does X know?
What does the reader know that X does not?
Who said this?
Where is X?
Why did X act?
What rule applies?
What remains unresolved?
What should I already know at my current reading position?
```

while preserving:

```text
SOURCE provenance
uncertainty
perspective
temporal order
identity revelations
reader knowledge boundary
spoiler safety
```

The system must generalize beyond fiction to biography, technical prose, short tales and other English text without genre hardcoding in the kernel.

---

# 2. Fundamental Reframing

The system does NOT translate an entire document into a complete semantic transcription.

Instead:

```text
SOURCE
  immutable evidence
      ↓
cheap structural/retrieval indexes
      ↓
progressively materialized semantic cache
      ↓
query-specific semantic expansion
      ↓
ContextPacket
      ↓
grounded answer
```

Semantic memory is:

```text
a recomputable,
proof-linked,
query-accelerating cache
over immutable SOURCE
```

It is not the document's new authoritative representation.

---

# 3. Minimal Kernel

The current minimal conceptual kernel is:

```text
SOURCE / Evidence
Mention / Referent
Predication
Proposition DAG
SemanticContext
Derivation
SemanticChange
KnowledgeBoundary
Projection / View
ContextPacket
```

The following are not required as fundamental storage primitives:

```text
EVENT
STATE
CLAIM
ATTITUDE
SAY
ACTION
KN
REL
```

They remain useful classifications or projections.

---

# 4. SOURCE

SOURCE is immutable.

Every document has stable source units and spans.

```text
SourceSpan
  document_id
  ingestion_unit_id
  start_offset
  end_offset
  text
```

The source hierarchy may include:

```text
book
chapter
scene
segment
paragraph
span
```

not all of which are mandatory for every document type.

SOURCE text and offsets must never be destructively normalized away.

---

# 5. Evidence

Evidence identifies the SOURCE basis for semantic interpretation.

```text
Evidence
  id
  source_spans[]
  evidence_role
  ir_schema_version
```

Common evidence roles:

```text
surface
predicate
argument
attribution
identity
temporal
negation
modality
resolution
derivation_support
```

The immutable evidence is the span.

An extracted label such as:

```text
predicate = bequeath
```

is an interpretation, not immutable evidence.

---

# 6. Mention

A Mention is a surface referring expression.

```text
Mention
  id
  span
  surface
  mention_hint?
```

Examples:

```text
John
he
the masked man
the capital
this connection
the device
```

A Mention does not imply a globally canonical referent.

---

# 7. Referent

A Referent is a semantic discourse object.

```text
Referent
  id
  mention_ids[]
  type_hints[]
```

Referents are intentionally weaker than globally merged entities.

Later semantic content may establish:

```text
same_as(A, B)
distinct_from(A, B)
```

but those identity statements themselves require evidence and visibility.

Irreversible global semantic merging is prohibited.

---

# 8. Predication

The universal semantic atom is:

```text
Predication
  id

  predicate_label

  arguments:
    role -> SemanticValue

  semantic_context_id

  grounding / proof

  available_from

  semantic_coverage

  ir_schema_version
```

`SemanticValue` may be:

```text
ReferentRef
PredicationRef
PropositionRef
TypedValue
RawValue
```

Examples:

```text
resemble(John, Peter)

become(John, angry)

remain(John, angry)

run(John)

believe(Mary, Proposition X)

communicate(John, Proposition X)

married_to(Alice, Bob)

member_of(John, Guild)

cause(P1, P2)

same_as(MaskedMan, Marcus)
```

There is no parallel authoritative Entity-to-Entity edge language for these same semantics.

---

# 9. Derived Semantic Classifications

Predications may receive classifications such as:

```text
eventive
stative
relational
property
habitual
generic
process
transition
epistemic
communicative
causal
```

These support views, query planning and analysis.

They do not fork storage semantics.

---

# 10. Proposition DAG

Propositions provide semantic composition and scope.

Conceptually:

```text
Proposition :=
    Atom(PredicationRef)

  | Not(PropositionRef)

  | And(PropositionRef[])

  | Or(PropositionRef[])

  | Conditional(
        condition: PropositionRef,
        consequence: PropositionRef
    )

  | Modal(
        modality,
        PropositionRef
    )

  | Quantified(
        quantifier,
        variable,
        restriction?,
        body
    )
```

Propositions should be DAG objects rather than recursively duplicated trees.

Example:

```text
P1 = Atom(leave(Peter))
```

may be referenced from:

```text
believe(John, P1)
deny(Mary, P1)
assert(Narrator, P1)
```

without cloning P1.

---

# 11. Negation Scope

Negation belongs primarily to proposition scope.

These must remain different:

```text
John did not promise to leave.
```

approximately:

```text
Not(
  promise(
    John,
    leave(John)
  )
)
```

versus:

```text
John promised not to leave.
```

approximately:

```text
promise(
  John,
  Not(
    leave(John)
  )
)
```

A generic event-level `actuality=negated` must not replace explicit scope.

---

# 12. Modality and Temporal Meaning

Modality and time are separate.

Modal operators may represent:

```text
possible
necessary
required
permitted
hypothetical
counterfactual
desired
```

Ordinary future temporal placement should not be redundantly encoded as both:

```text
Modal(future, P)
```

and a temporal constraint.

One semantic distinction should have one canonical representation.

---

# 13. Nested Attribution

Because epistemic/communicative relations are ordinary predications over propositions, nested attribution remains compositional.

Example:

```text
The historian claimed that
John said that
Mary believed that
Peter lied.
```

can be represented conceptually as:

```text
P1 = Atom(lie(Peter))

P2 = Atom(
  believe(Mary, P1)
)

P3 = Atom(
  communicate(
    speaker=John,
    content=P2,
    illocution=assert
  )
)

P4 = Atom(
  claim(Historian, P3)
)
```

No separate fundamental CLAIM or ATTITUDE language is required.

---

# 14. Communication

Communication is a Predication.

Example:

```text
communicate(
  speaker=John,
  recipient=Mary?,
  medium=spoken,
  content=P1,
  illocution=assert
)
```

Content has one canonical semantic location.

Do not duplicate communication content across separate event and attitude records.

Legacy SAY is a projection.

---

# 15. Semantic Context

Semantic content occurs under a context.

```text
SemanticContext
  id

  context_kind:
    narration
    quoted_speech
    document_inside_document
    dream
    hypothetical
    counterfactual
    example
    simulation
    reported_content
    open

  perspective?
  parent_context?

  grounding
  available_from
```

A predication being under narration means:

```text
the narrative asserted it
```

not automatically:

```text
it is objectively true in the story world
```

Truth is a projection.

---

# 16. Truth Views

The kernel supports query-time views including:

```text
text_asserted
currently_established
challenged
retracted
disputed
retrospectively_established
```

These are computed from:

```text
SemanticContext
Grounding / Derivation
SemanticChange
Contradictions
KnowledgeBoundary
truth policy
```

No global binary story-truth flag is authoritative.

---

# 17. Grounding Axes

Grounding dimensions must remain orthogonal.

## Content support

```text
direct_source
derived_from_source
external
unsupported
```

## Resolution support

```text
source
external_reference_knowledge
heuristic
unresolved
```

Admission is derived from these axes rather than authored independently.

Default:

```text
direct_source
derived_from_source
    -> grounded

external
unsupported
    -> hypothesis/inadmissible for asserted textual views
```

---

# 18. World Knowledge

World knowledge may assist reference resolution.

Example:

```text
"The government returned to the capital."
```

External knowledge may help identify what `the capital` means.

This does NOT import:

```text
Paris is the capital of France
```

as a textual claim unless SOURCE independently supports it.

Referential knowledge and content knowledge are distinct.

---

# 19. Derivation and Proof

Every derived semantic object carries a recoverable derivation.

```text
Derivation
  id
  output_object
  rule_or_model
  input_evidence[]
  input_semantic_objects[]
  version
```

Required chain:

```text
semantic object
  <- derivation
  <- evidence
  <- SOURCE
```

Proof-carrying semantics must continue into answer generation.

---

# 20. Structural Proposition Identity

If structural interning/hashing is used:

```text
proposition_hash =
  H(
    ir_schema_version,
    normalized_structure
  )
```

it uses stable raw representation IDs.

It is boundary-independent.

Structural identity means:

```text
same normalized representation
```

not:

```text
semantically equivalent under every context
```

Boundary/query-specific equivalence is a different layer.

---

# 21. Identity

Identity is semantic content:

```text
same_as(A, B)
distinct_from(A, B)
```

with:

```text
grounding
SemanticContext
available_from
SemanticChange history
```

A boundary-local identity projection computes visible equivalences.

Global semantic merge is forbidden.

Conflicting identity assertions must produce unresolved/conflict output, not silent union.

---

# 22. Semantic Change

One lifecycle mechanism controls revisions.

```text
SemanticChange
  id

  change_kind:
    assert
    retract
    supersede
    confirm
    reinterpret
    invalidate
    resolve
    reopen

  target_objects[]

  replacement_objects[]?

  reason:
    narrative_reveal
    narrative_retraction
    misdirection_resolution
    extraction_fix
    model_upgrade
    source_correction
    query_time_resolution
    open

  related_changes[]

  semantic_context?
  grounding
  derivation?

  available_from
```

This is the append-only history mechanism.

Identity, contradiction and epistemic access do not each invent separate lifecycle systems.

---

# 23. Contradiction

A semantic opposition may be represented through:

```text
contradicts(P1, P2)
```

and a derived/auditable view:

```text
ContradictionView
  proposition_a
  proposition_b

  classification:
    source_disagreement
    narrative_intentional
    narrative_revision
    extraction_conflict
    unresolved

  resolving_changes[]
```

Classification itself may be uncertain.

Do not automatically label an unreliable narrator or narrative intent without evidence/derivation.

---

# 24. Epistemic Access

Character knowledge should not require manually materializing every `know()` statement.

Use a derived projection:

```text
EpistemicAccess(
  subject,
  proposition,
  boundary
)
```

Possible derivation basis:

```text
explicit_knowledge
explicit_belief
witnessed_event
participated_in_event
received_communication
inferred_from_context
```

Strength:

```text
certain
probable
defeasible
```

Presence during an event does NOT automatically equal knowledge.

Defeating evidence may invalidate an access derivation.

---

# 25. Epistemic Gap

Define:

```text
EpistemicGap(P, subject, B)
```

conceptually:

```text
currently_established(P, B)
AND
NOT epistemically_accessible(
  subject,
  P,
  B
)
```

This directly supports dramatic-irony queries.

Examples:

```text
What does the reader know that Alice does not?

Which danger is known to the reader but not John?

When does Bob learn the secret the reader already knew?
```

---

# 26. Temporal Representation

Separate:

```text
discourse time
story time
epistemic availability
```

Temporal storage is constraint-oriented.

```text
TemporalAnchor
TemporalInterval
TemporalConstraint
```

A constraint may include:

```text
axis:
  story
  discourse

possible_relations[]

certainty:
  fixed
  approximate
  inferred
  narrative_order_only

grounding
```

Allen-style relations are vocabulary/reasoner interface, not an O(n²) materialized pair table.

---

# 27. Semantic Coverage

Progressive semanticization is multi-axis.

```text
SemanticCoverage
  mention_detection
  referent_resolution
  predication
  proposition_scope
  attribution
  temporal
  epistemic
  grounding
  identity
```

Each axis may independently be:

```text
none
light
deep
verified
```

Processing pipelines may still use coarse stage names, but stored coverage is not one scalar.

---

# 28. Progressive Semanticization

The system does not deep-parse the entire document by default.

Conceptual processing levels:

```text
L0 SOURCE
L1 LIGHT
L2 COARSE SEMANTIC
L3 DEEP SEMANTIC
L4 TARGETED DEEP REASONING
```

Potential triggers:

```text
query relevance
salient/repeated entity
ambiguity
identity knot
temporal query
epistemic query
failed answer proof
chapter/scene compaction
repeated retrieval
explicit request
```

Semantic memory is materialized where useful.

---

# 29. KnowledgeBoundary

Boundary is fundamentally a capability over evidence.

```text
KnowledgeBoundary
  current_position?
  visible_source_units?
  explicit_includes[]
  explicit_excludes[]
  explicit_known_items[]
  policy
```

For ordinary linear reading:

```text
visible_units = prefix(current_position)
```

is a convenience, not the universal representation.

---

# 30. Boundary Rules

Boundary resolution order:

```text
R1 resolve reading mode/current position

R2 build base visible source units

R3 apply explicit includes/excludes

R4 build visible Evidence universe

R5 apply visible SemanticChange objects

R6 compute boundary-visible identity projection

R7 expose semantic/derived objects whose proof
   is valid entirely inside the visible universe

R8 perform graph/FTS/vector/raw retrieval
   only inside that universe
```

This applies equally to:

```text
semantic objects
identity projections
EpistemicAccess
ContradictionView
revisions
summaries
macro memory
derived caches
retrieval indexes
ContextPacket inputs
```

Core rule:

```text
If an object's proof depends on invisible evidence,
the object is invisible.
```

---

# 31. Resolve Then Aggregate

Any query performing:

```text
COUNT
GROUP BY
list all
deduplicate
frequency
timeline aggregation
```

must:

```text
1. establish KnowledgeBoundary
2. compute active equivalence/identity projection
3. match through that view
4. collect results
5. deduplicate under that view
6. aggregate
```

Structural proposition hashes remain unchanged.

---

# 32. Retrieval Planes

Authoritative semantic memory and disposable retrieval indexes are distinct.

Authoritative:

```text
Predication(...)
```

Derived retrieval indexes may denormalize:

```text
Alice --married_to--> Bob
```

for speed.

Such indexes:
- are not authoritative semantics;
- are versioned/rebuildable;
- obey KnowledgeBoundary;
- can be deleted without losing meaning.

Retrieval paths:

```text
structured semantic
FTS
vector
raw source
```

all obey boundary before search.

---

# 33. ContextPacket

ContextPacket is the final evidence/security boundary before answer synthesis.

```text
ContextPacket
  query
  query_type

  knowledge_boundary
  projection_lens?

  answer_stance

  semantic_objects[]
  propositions[]
  referents[]

  equivalence_view?
  epistemic_views?
  disputes[]

  allowed_answer_claims[]

  proof_slice:
    derivations[]
    evidence[]

  raw_source_spans[]

  unresolved_items[]

  synthesis_mode
  token_budget
  packet_version
```

No answer model receives arbitrary semantic storage.

---

# 34. Answer Synthesis

Candidate modes:

```text
template_grounded
constrained_llm
hybrid
```

`template_grounded` is suitable for simple high-trust factual responses.

`constrained_llm` allows fluent synthesis but factual claims must remain within:

```text
allowed_answer_claims
```

`hybrid` combines deterministic factual skeleton with LLM realization.

Post-generation verification is mandatory for free synthesis.

---

# 35. Answer Proof Closure

Required chain:

```text
SOURCE
↓
Evidence
↓
Derivation
↓
semantic object / Proposition
↓
ContextPacket.allowed_answer_claim
↓
answer claim
↓
surface answer
```

A factual answer claim not covered by the packet is a verification failure.

The recovery policy is currently experimental and may include:

```text
remove claim
regenerate
retrieve more evidence
downgrade stance
template fallback
abstain
```

---

# 36. Answer Stances

Internal:

```text
answered
disputed
ambiguous
not_found
verified_not_stated
out_of_boundary
```

`verified_not_stated` is limited to closed/enumerable domains with an explicit complete negative procedure.

For ordinary open-world textual questions:

```text
not_found
```

is the strongest default negative conclusion.

Empty retrieval alone never proves absence.

---

# 37. Spoiler-Safe Rendering

Internal `out_of_boundary` may itself reveal a future secret.

Spoiler policy may publicly render such cases as a weaker:

```text
not_found
```

or:

```text
insufficient visible evidence
```

when merely revealing the existence of future decisive evidence is itself a spoiler.

Spoiler protection is structural, not prompt-only.

---

# 38. Schema-on-Demand / ProjectionLens

A query may create a semantic lens.

Example:

```text
OFFICE_HOLDING
CHARACTER_KNOWLEDGE
MAGIC_RULE
PROGRAMMING_CONSTRAINT
RELATIONSHIP_CHANGE
```

A ProjectionLens:
- queries the semantic/cache substrate;
- may trigger deeper semanticization;
- may be cached;
- never mutates the core ontology.

---

# 39. Long-Document Compaction

Future book-scale memory may use proof-linked abstraction:

```text
BOOK
  ARC
    EPISODE
      SCENE
        DETAIL
          SOURCE
```

Compressed memory never replaces SOURCE or detailed semantics.

The Context Compiler chooses an appropriate granularity and drills down when necessary.

---

# 40. Explicit Non-Commitments

The kernel does NOT currently require:

```text
graph database
full-document deep semanticization
Datalog
SAT/SMT
e-graph implementation
bitmask-HNSW
formal state-delta engine
formal causal reasoner
formal spatial reasoner
mandatory SRL/FrameNet
mandatory coreference model
```

These remain empirical implementation hypotheses.

---

# 41. Core Invariants

```text
SOURCE is authoritative.

Semantic memory is a cache over SOURCE.

Predication is the universal semantic atom.

Semantic relations are Predications, not a second edge ontology.

Propositions preserve scope through shared DAG structure.

Structural proposition identity is boundary-independent.

Semantic equivalence is a separate boundary/query-time projection.

Truth is projected, not globally stored.

Narrative assertion does not automatically equal story truth.

Identity is evidence- and boundary-dependent.

One SemanticChange mechanism handles lifecycle.

Epistemic access is derived and defeasible.

Contradictions are explicit and auditable.

Semantic depth is multi-axis.

No cache bypasses KnowledgeBoundary.

No retrieval path searches invisible evidence first.

Resolve precedes aggregation.

ContextPacket constrains factual answer content.

Proof chains continue to final answer claims.

Empty retrieval does not prove absence.

The system may abstain.
```

---

# 42. Current Status

rc1.2 is ready for implementation pressure.

It is NOT the final v0.2 contract.

The next activity is a small executable semantic microkernel and hostile manual fixtures, not another broad prose redesign.
