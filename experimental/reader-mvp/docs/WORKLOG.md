# Project Work Log

Append-only operational history.

Use ISO date when possible.

---

## 2026-09-17 - SAY source-authoritative speaker discovery i2

Installed `SAY v0.1.20h-i2 source-authoritative run seeds`.

Regression:

```text
focused:             106 passed
SAY regression:      174 passed
ambiguity canaries:   34 passed
full offline:        299 passed
compileall:          OK
```

Frozen SEG8 replay after updating obsolete safety expectation:

```text
Sir John      P13-P22 recovered
Lady Dunfern  P26-P30 recovered

say_speaker_rewritten: 17
say_source_supported:  19
```

Frozen SEG11 precision behavior remained intact.

Final deterministic result:

```text
SEG 8 FROZEN SAFETY ASSERTIONS: PASS
SEG 11 FROZEN SAFETY ASSERTIONS: PASS
FROZEN SEG8/SEG11 REPLAY: PASS
```

Important finding:

SEG8 P25 remains missing because the weak model emitted:

```text
"Sir and husband," she said, with great nervousness at first,
"you have summoned me ..."
```

as one SAY candidate crossing direct-speech/narrator/direct-speech surfaces.

Existing mixed-surface firewall correctly rejects the record.

Next task:

```text
j1 mixed-surface salvage
```

---

## 2026-09-17 - Universal semantic-memory architecture pivot

The project direction was broadened from specialized SAY/ACTION/KN extraction toward an English-only general semantic-memory substrate.

Major conclusions after multiple adversarial design reviews:

```text
SOURCE remains authoritative.

Semantic memory is a progressively materialized cache.

Predication is preferred as the universal semantic atom.

Propositions require explicit scope/composition.

Truth is context-relative/query-time.

Identity is boundary-aware.

Character epistemic access is defeasible.

Lifecycle changes use one SemanticChange mechanism.

KnowledgeBoundary constrains every retrieval path.

ContextPacket must constrain final answer claims.
```

Current architecture candidate:

```text
v0.2-rc1.2
```

Next architecture task after v0.1 SAY freeze:

```text
pure-Python semantic microkernel
+
manual hostile representation fixtures
```
