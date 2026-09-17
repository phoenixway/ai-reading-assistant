# Semantic Memory v0.2-rc1.2 Hostile Representation Fixtures

These are manual representation fixtures.

The goal is to break the semantic distinctions before model extraction begins.

Each fixture should eventually record:
- expected Referents;
- Predications;
- Propositions;
- SemanticContexts;
- Evidence;
- SemanticChanges;
- KnowledgeBoundary effects;
- expected queries.

---

# F01 - Negation Scope A

```text
John did not promise to leave.
```

Must differ from F02.

---

# F02 - Negation Scope B

```text
John promised not to leave.
```

Must preserve:

```text
Not(Promise(...))
```

versus:

```text
Promise(Not(...))
```

scope distinction.

---

# F03 - Deep Attribution

```text
The historian claimed that John said Mary believed Peter had lied.
```

Must preserve every embedding layer.

No CLAIM/ATTITUDE side language should be required.

---

# F04 - Modal Under Attribution

```text
John said that Mary might have lied.
```

`might` scopes over Mary's lying proposition, not John's act of communicating.

---

# F05 - Counterfactual / Conditional

```text
He would have done it, she supposed, had the letter arrived a day earlier.
```

Tests:
- reported epistemic state;
- counterfactuality;
- conditional antecedent;
- temporal relation.

---

# F06 - Relative Clause + Quantified Belief

```text
John, who everyone except Mary believed had already left, appeared at the door.
```

Tests:
- nested attribution;
- exception to quantification;
- temporal relation;
- narrator/event contrast.

---

# F07 - Quantifier Scope

```text
Every student read a book.
```

Potential readings:

```text
forall student exists book
```

versus:

```text
exists book forall student
```

Do not invent a single reading if SOURCE does not resolve it.

---

# F08 - Referential Ambiguity

```text
Peter spoke to Robert. He looked frightened.
```

Extraction ambiguity may leave competing interpretations.

Do not misclassify parser uncertainty as narrative claim.

---

# F09 - Narrative Alternative

```text
Either Peter or John took the key.
```

This ambiguity is in SOURCE semantics:

```text
Or(
  took(Peter,key),
  took(John,key)
)
```

not an extractor failure.

---

# F10 - World Knowledge for Reference

Context establishes France.

```text
The government returned to the capital.
```

External knowledge may resolve:

```text
the capital -> Paris
```

without importing:

```text
Paris is the capital of France
```

as textual content.

---

# F11 - Denial vs Truth

```text
John denied that Peter left.
Later, the narrator confirmed that Peter had left.
```

Must preserve John's denial and later establishment without treating one as an extraction correction.

---

# F12 - Story vs Discourse Time

```text
Twenty years earlier, John had hidden the key.
```

Discourse occurrence is later than earlier narrated story event.

---

# F13 - Approximate Temporal Relation

```text
John arrived shortly before Mary.
```

Preserve approximate relation.

Do not invent timestamps.

---

# F14 - Explicit Cause vs Sequence

A:

```text
Because the bridge collapsed, the army retreated.
```

B:

```text
The bridge collapsed. The army retreated.
```

Only A directly supports causal semantics.

---

# F15 - Technical Rule

```text
If the buffer is full, write() blocks unless non-blocking mode is enabled.
```

Must represent:
- condition;
- behavior;
- exception;
- technical referents;
- no special PROGRAMMING_RULE kernel primitive.

---

# F16 - Quantitative Approximation

```text
The army numbered about ten thousand men.
```

Do not force false exact precision.

---

# F17 - Range

```text
The journey lasted between three and five days.
```

Typed range should support minimum/maximum when parsed confidently.

---

# F18 - Plot Identity Reveal

Ch2:

```text
The masked man entered the tower.
```

Ch17:

```text
Marcus removed the mask.
```

At Ch5:
- Masked Man and Marcus are not reader-visible equivalent.

After Ch17:
- identity projection may unify them.

Structural proposition hashes remain unchanged.

---

# F19 - Misdirection / Retraction

Ch4:

```text
All evidence pointed to Robert as the masked man.
```

Ch8:

```text
The identification of Robert was false.
```

Ch9:

```text
The masked man was Marcus.
```

Test SemanticChange history and reader-boundary reconstruction.

---

# F20 - Epistemic Access Is Defeasible

```text
John was present when Peter took the key.
John had been unconscious throughout the scene.
```

Presence alone must not yield certain knowledge.

---

# F21 - Communication Access

```text
Mary told John that Peter took the key.
```

Supports access to the proposition via communication.

Whether John believes it is a separate semantic question.

---

# F22 - Dramatic Irony

Reader-visible source establishes:

```text
The bridge is rigged to explode.
```

Alice does not witness/read/hear this information.

Query:

```text
What danger does the reader know about that Alice does not?
```

Should produce an EpistemicGap.

---

# F23 - Contradictory Sources

```text
Historian A called the battle a victory.
Historian B called it a defeat.
```

Must remain dispute/source disagreement.

No automatic truth choice.

---

# F24 - Extraction Supersession

Old extraction:

```text
speaker = Mary
```

Verified extraction:

```text
speaker = Alice
```

This is SemanticChange/supersession, not narrative contradiction.

---

# F25 - Embedded Document

Narration:

```text
The letter read, "Peter has betrayed us."
```

Must distinguish:
- existence/content of the letter;
- proposition asserted by the letter;
- story-world truth of betrayal.

---

# F26 - Dream Context

```text
John dreamed that Mary was dead.
```

Do not establish Mary's death as story truth.

---

# F27 - Generic/Habitual

```text
Wolves hunt at night.
```

Test generic semantics without inventing a specific wolf/hunt event.

---

# F28 - Free Indirect / Perspective Stress

Use a real fiction passage where narrator surface and character perspective blur.

Goal:
- test SemanticContext;
- do not force a false binary narrator/character assignment.

Fixture text should be chosen from legally usable test material or project source text.

---

# F29 - Quotation / Speech Surface

```text
"Sir and husband," she said, "you have summoned me..."
```

Tests separation of:
- spoken surface;
- narrator attribution;
- content proposition;
- speaker grounding.

This corresponds conceptually to the v0.1 j1 problem.

---

# F30 - Resolve Then Aggregate

Before identity reveal:

```text
Masked Man performs action A.
Marcus performs action B.
```

After visible reveal:

```text
Masked Man same_as Marcus.
```

Query:

```text
How many relevant actions has Marcus performed?
```

Must aggregate A+B after visible identity resolution.

Before reveal, it must not.

---

# F31 - Answer Boundary Side Channel

At Ch3 user asks:

```text
Is John still alive?
```

Decisive information exists only much later and is plot-critical.

Internal system may detect `out_of_boundary`.

Public spoiler-safe answer must not reveal that a decisive future answer exists.

---

# F32 - Raw Retrieval Boundary

At Ch5, a semantically perfect answer exists in Ch17.

Verify:

```text
structured retrieval
FTS
vector retrieval
raw source lookup
```

cannot retrieve Ch17 under the Ch5 KnowledgeBoundary.

---

# F33 - Composition Stress Fixture

Use one multi-chapter mini-passage with this shape:

```text
Ch2:
The masked man witnessed Event E.

Ch4:
Evidence suggested the masked man was Robert.

Ch6:
Marcus denied witnessing E.

Ch8:
The Robert identification was disproved.

Ch9:
The masked man was revealed as Marcus.
```

At each boundary test:

```text
Who was believed to be the masked man?

Who currently has epistemic access to E?

What did the reader know at Ch5?

What is currently established at Ch9?

Was Marcus's denial compatible with what he could know?
```

This fixture is mandatory before declaring Gate A passed.

---

# F34 - Complex Scope Composite

```text
John didn't promise not to leave unless Mary asked him, although Peter later claimed that John had already decided to stay.
```

Stress:
- negation;
- promise;
- conditional;
- temporal relation;
- nested attribution;
- intention/state semantics.

---

# F35 - Meta Query vs World Query

At Chapter 5:

```text
Does the word "dragon" occur anywhere in the book?
```

This is a SOURCE/document query, not automatically a diegetic world query.

The query planner must apply the correct policy explicitly.

---

# Fixture Evaluation Template

For each fixture:

```text
Representable naturally?            YES/NO
Multiple canonical encodings?       YES/NO
Information lost?                   YES/NO
Unsupported precision introduced?   YES/NO
Boundary leak possible?             YES/NO
New fundamental primitive needed?   YES/NO
Notes:
```

Repeated awkwardness is architectural evidence.

One unusual English construction is not automatically justification for a new kernel primitive.
