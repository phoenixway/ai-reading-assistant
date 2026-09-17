# Reader MVP Documentation Index

Status: canonical documentation map  
Current semantic architecture candidate: **v0.2-rc1.2**  
Current production extraction line: **v0.1.x, specialized pipeline**

This directory is intended to make the project restartable after a chat ends, a model changes, or implementation pauses.

## Read order for a new session

1. `CURRENT_STATE.md`
2. `ROADMAP.md`
3. `architecture/SEMANTIC_MEMORY_V0_2_RC1_2_FOUNDATION.md`
4. `architecture/SEMANTIC_MEMORY_V0_2_RC1_2_VALIDATION.md`
5. `architecture/SEMANTIC_MEMORY_V0_2_RC1_2_HOSTILE_FIXTURES.md`
6. `DECISION_LOG.md`
7. `NEXT_SESSION_BOOTSTRAP.md`
8. latest entries in `WORKLOG.md`

## Canonical documents

### Current state

`CURRENT_STATE.md`

The short source of truth for:
- what already works;
- what is frozen;
- what is currently in progress;
- exact next work;
- last known regression state.

This file should stay compact.

### Roadmap

`ROADMAP.md`

The ordered execution plan. It distinguishes:
- current work;
- near-term gates;
- later experiments;
- explicitly deferred ideas.

### Semantic architecture

`architecture/SEMANTIC_MEMORY_V0_2_RC1_2_FOUNDATION.md`

The current provisional architecture kernel.

Important: `rc1.2` is not a frozen v0.2 wire format. It defines semantic distinctions and invariants to test in an executable microkernel.

### Validation

`architecture/SEMANTIC_MEMORY_V0_2_RC1_2_VALIDATION.md`

The five architecture-killing gates that must pass before the v0.2 contract is frozen.

### Hostile fixtures

`architecture/SEMANTIC_MEMORY_V0_2_RC1_2_HOSTILE_FIXTURES.md`

The initial manual representation torture set. The fixture set should grow when a new failure class is found.

### Decision log

`DECISION_LOG.md`

Append-only record of architectural decisions. New decisions are appended; old decisions are not silently rewritten. If a decision changes, append a superseding decision.

### Work log

`WORKLOG.md`

Append-only operational log of completed changes, tests and measured results.

### Session bootstrap

`NEXT_SESSION_BOOTSTRAP.md`

A compact handoff instruction for a new AI session or human contributor.

---

# Documentation Governance

The documentation has three levels.

## 1. Canonical state

- `CURRENT_STATE.md`
- `ROADMAP.md`
- current architecture files under `architecture/`

These may be edited when the project state changes.

## 2. Append-only history

- `DECISION_LOG.md`
- `WORKLOG.md`

Do not rewrite history except to correct a factual typo. Supersede old entries with new entries.

## 3. Experimental notes

Future research notes may live under:

```text
docs/research/
```

They are not canonical until promoted by an explicit decision.

---

# Update Protocol After Every Meaningful Change

When a task changes project behavior:

1. run the relevant regression suite;
2. append results to `WORKLOG.md`;
3. update `CURRENT_STATE.md`;
4. update `ROADMAP.md` if phase/gate status changed;
5. append to `DECISION_LOG.md` if architecture or invariants changed;
6. update `NEXT_SESSION_BOOTSTRAP.md` if the next action changed materially.

No chat should be the only location of an important project decision.

---

# Architecture Versioning

Names mean:

```text
v0.1
```

Existing specialized extraction system.

```text
v0.2-rcN
```

Provisional universal semantic-memory architecture under representation and implementation pressure.

```text
v0.2
```

May be declared only after:
- human representability;
- machine emitability;
- real-chapter economics;
- proof closure;
- boundary security.

Wire/storage layout is allowed to remain less frozen than semantic distinctions.

---

# Current strategic principle

The project is transitioning from:

```text
specialized narrative extractor
```

toward:

```text
source-grounded temporal/epistemic semantic memory
```

The authoritative record remains immutable SOURCE.

Semantic memory is a progressively materialized, recomputable cache over SOURCE, not a replacement transcription of the document.
