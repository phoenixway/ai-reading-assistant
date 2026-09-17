# Semantic Memory v0.2-rc1.2 Critical Validation

Only architecture-killing gates belong in the immediate cycle.

Current blockers to v0.2 freeze:

```text
A Human representability
C Machine emitability
D Real-chapter economics
G Proof closure
H Boundary security
```

---

# Gate A - Human Representability

Goal:

```text
Can humans encode difficult English naturally
with the rc1.2 distinctions?
```

This is a representation test, not an extraction test.

Test:
- negation scope;
- nested attribution;
- modality;
- conditionals;
- quantifier scope;
- referential ambiguity;
- identity reveal;
- identity retraction/misdirection;
- unreliable narration;
- epistemic delay;
- contradiction;
- temporal approximation;
- causal wording;
- technical rules;
- numeric approximation/ranges.

FAIL if representation repeatedly requires:
- genre-specific hacks;
- two canonical encodings for the same meaning;
- hidden precision;
- destructive identity merge;
- semantic aliases between core and graph edges;
- new fields for isolated constructions.

## Gate A+

Include at least one composition-stress fixture combining:

```text
identity reveal
misidentification/retraction
contradiction
epistemic access
nested attribution
temporal ordering
```

The goal is to test the interaction of mechanisms, not just each mechanism independently.

---

# Gate C - Machine Emitability

Only after Gate A is credible.

Compare:

## Single-pass

One model call emits structured semantics.

## Coarse-to-fine

Pass 1:

```text
mentions
referents
predications
evidence spans
attribution cues
negation cues
modality cues
```

Pass 2:

```text
proposition assembly
scope
contexts
identity
temporal constraints
ambiguity
```

Measure:

```text
schema validity
scope correctness
grounding correctness
nested attribution correctness
repeatability
repair rate
input tokens
output tokens
latency
```

Do not freeze wire format before this experiment.

---

# Gate D - Real-Chapter Economics

Use one real 5k-10k word English chapter.

Compare:

## A Full semanticization

Deep parse everything.

## B Progressive semanticization

Cheap full-chapter baseline + deep semanticization of hot regions.

## C Retrieval-first cache

Raw retrieval + compact semantic memory + query-time semanticization.

Measure:

```text
query answer accuracy
evidence recall
false world facts
semantic objects / 1000 words
tokens spent extracting
wall-clock time
peak RAM/VRAM
bytes stored
ContextPacket size
raw-source rescue rate
percentage of materialized semantics actually used
```

The result determines the default ingestion policy.

A theoretically elegant architecture that spends most semantic work on unused objects fails economically.

---

# Gate G - Proof Closure

For every factual answer:

```text
SOURCE
→ Evidence
→ Derivation
→ Proposition/Predication
→ ContextPacket.allowed_answer_claim
→ answer claim
→ final response
```

Measure:

```text
unsupported factual claim rate
citation correctness
proof coverage
answer stance correctness
```

Test:

```text
template_grounded
constrained_llm
hybrid
```

## Gate G: Resolve-Then-Aggregate

Mandatory queries after an identity reveal:

```text
How many times did Marcus do X?
List all actions by Marcus.
How often did X interact with Marcus?
```

Earlier masked/aliased references must aggregate correctly only when their identity equivalence is visible.

Structural proposition hashes must not be mutated.

## Verification recovery

Compare policies experimentally:

```text
remove unsupported claim
regenerate
retrieve more
downgrade stance
template fallback
abstain
```

No policy is frozen before measurements.

---

# Gate H - Boundary / Spoiler Security

Hard target:

```text
Spoiler Leakage Rate = 0
```

Attack every path:

```text
semantic lookup
FTS
vector retrieval
raw source retrieval
identity projection
equivalence projection
EpistemicAccess cache
ContradictionView
SemanticChange cache
summary/macro memory
derived state
ContextPacket
answer stance side channel
```

Test hidden future:
- identity;
- false identity later retracted;
- death;
- betrayal;
- explanation;
- relationship change;
- location;
- causal reveal.

No retriever may search invisible evidence first.

## Dramatic irony

Add queries:

```text
What does the reader know that Alice does not?
Which danger is visible to the reader but not John?
Who currently knows the secret?
When does Bob learn what the reader already knew?
```

This simultaneously tests:

```text
truth projection
EpistemicAccess
KnowledgeBoundary
temporal semantics
```

---

# Freeze Sequence

After A+C+D+G+H:

## Freeze semantic distinctions

Freeze:
- Predication semantics;
- Proposition scope/composition;
- SemanticContext;
- Evidence/Derivation;
- SemanticChange;
- KnowledgeBoundary;
- ContextPacket answer-proof contract.

## Do not yet freeze

- database schema;
- vector backend;
- index strategy;
- e-graph implementation;
- ranking weights;
- semanticization thresholds;
- reasoner technology.

---

# Deferred Experimental Backlog

Only after critical gates:

```text
proposition interning benchmark
packed ambiguity representation
specialized coreference
SRL / FrameNet
temporal reasoner
e-graph equivalence
Datalog
vector filtering strategy
state-delta optimization
spatial reasoning
causal reasoning
compaction tuning
```
