from app.semantic import (
    ASSERT,
    IDENTITY_ADD,
    KNOWLEDGE_ADD,
    Evidence,
    KnowledgeBoundary,
    Proposition,
    Referent,
    SemanticChange,
    SemanticContext,
    build_context_packet,
    epistemic_access,
    epistemic_gap,
    identity_projection,
    resolve_then_aggregate,
    truth_view,
    visible_evidence,
)


def ev(eid, source_id, position, text=""):
    return Evidence(
        id=eid,
        source_ids=(source_id,),
        position=position,
        text=text,
    )


def test_f01_f02_negation_scope_differs():
    leave = Proposition.atom(
        "leave",
        (("actor", "john"),),
    )

    promise_leave = Proposition.atom(
        "promise",
        (("actor", "john"),),
        (leave,),
    )

    f01 = Proposition.not_(
        promise_leave
    )

    f02 = Proposition.atom(
        "promise",
        (("actor", "john"),),
        (
            Proposition.not_(leave),
        ),
    )

    assert f01.key != f02.key
    assert f01.op == "NOT"
    assert f02.op == "PRED"
    assert f02.children[0].op == "NOT"


def test_f03_deep_attribution_preserved():
    lied = Proposition.atom(
        "lie",
        (("actor", "peter"),),
    )

    believed = Proposition.atom(
        "believe",
        (("experiencer", "mary"),),
        (lied,),
    )

    said = Proposition.atom(
        "say",
        (("speaker", "john"),),
        (believed,),
    )

    claimed = Proposition.atom(
        "claim",
        (("speaker", "historian"),),
        (said,),
    )

    assert (
        claimed.children[0]
        .children[0]
        .children[0]
        .predication.predicate
        == "lie"
    )


def test_f09_source_ambiguity_is_or():
    peter = Proposition.atom(
        "take",
        (
            ("actor", "peter"),
            ("object", "key"),
        ),
    )

    john = Proposition.atom(
        "take",
        (
            ("actor", "john"),
            ("object", "key"),
        ),
    )

    p = Proposition.or_(
        peter,
        john,
    )

    assert p.op == "OR"
    assert p.children == (
        peter,
        john,
    )


def test_f11_denial_and_world_truth_coexist():
    peter_left = Proposition.atom(
        "leave",
        (("actor", "peter"),),
    )

    john_denied = Proposition.atom(
        "deny",
        (("speaker", "john"),),
        (peter_left,),
    )

    context = SemanticContext(
        propositions=(
            peter_left,
            john_denied,
        ),
        evidence=(
            ev(
                "e1",
                "P01",
                1,
                "John denied that Peter left.",
            ),
            ev(
                "e2",
                "P02",
                2,
                "Narrator confirmed Peter left.",
            ),
        ),
        changes=(
            SemanticChange(
                position=1,
                kind=ASSERT,
                target_key=john_denied.key,
                evidence_ids=("e1",),
            ),
            SemanticChange(
                position=2,
                kind=ASSERT,
                target_key=peter_left.key,
                evidence_ids=("e2",),
            ),
        ),
    )

    assert (
        truth_view(
            context,
            peter_left,
            KnowledgeBoundary(position=1),
        ).status
        == "UNKNOWN"
    )

    assert (
        truth_view(
            context,
            peter_left,
            KnowledgeBoundary(position=2),
        ).status
        == "SUPPORTED"
    )

    assert (
        truth_view(
            context,
            john_denied,
            KnowledgeBoundary(position=2),
        ).status
        == "SUPPORTED"
    )


def test_f18_identity_reveal_is_boundary_sensitive():
    entered = Proposition.atom(
        "enter",
        (
            ("actor", "masked_man"),
            ("destination", "tower"),
        ),
    )

    original_key = entered.key

    context = SemanticContext(
        referents=(
            Referent(
                "masked_man",
                "Masked Man",
            ),
            Referent(
                "marcus",
                "Marcus",
            ),
            Referent(
                "tower",
                "Tower",
                kind="place",
            ),
        ),
        propositions=(entered,),
        evidence=(
            ev(
                "enter",
                "CH2.P03",
                2,
            ),
            ev(
                "reveal",
                "CH17.P08",
                17,
            ),
        ),
        changes=(
            SemanticChange(
                position=2,
                kind=ASSERT,
                target_key=entered.key,
                evidence_ids=("enter",),
            ),
            SemanticChange(
                position=17,
                kind=IDENTITY_ADD,
                left_id="masked_man",
                right_id="marcus",
                evidence_ids=("reveal",),
            ),
        ),
    )

    early = KnowledgeBoundary(
        position=5
    )

    late = KnowledgeBoundary(
        position=17
    )

    early_ids = identity_projection(
        context,
        early,
    )

    late_ids = identity_projection(
        context,
        late,
    )

    assert (
        early_ids["masked_man"]
        != early_ids["marcus"]
    )

    assert (
        late_ids["masked_man"]
        == late_ids["marcus"]
    )

    early_group = resolve_then_aggregate(
        context,
        (entered,),
        early,
    )

    late_group = resolve_then_aggregate(
        context,
        (entered,),
        late,
    )

    assert (
        next(iter(early_group))
        != next(iter(late_group))
    )

    assert entered.key == original_key


def test_f20_presence_does_not_create_knowledge():
    took = Proposition.atom(
        "take",
        (
            ("actor", "peter"),
            ("object", "key"),
        ),
    )

    present = Proposition.atom(
        "present",
        (
            ("actor", "john"),
            ("scene", "room"),
        ),
    )

    context = SemanticContext(
        referents=(
            Referent("john", "John"),
            Referent("peter", "Peter"),
            Referent(
                "key",
                "Key",
                kind="object",
            ),
        ),
        propositions=(
            took,
            present,
        ),
        evidence=(
            ev(
                "e1",
                "P01",
                1,
            ),
        ),
        changes=(
            SemanticChange(
                position=1,
                kind=ASSERT,
                target_key=took.key,
                evidence_ids=("e1",),
            ),
            SemanticChange(
                position=1,
                sequence=1,
                kind=ASSERT,
                target_key=present.key,
                evidence_ids=("e1",),
            ),
        ),
    )

    boundary = KnowledgeBoundary(
        position=1
    )

    assert (
        truth_view(
            context,
            took,
            boundary,
        ).status
        == "SUPPORTED"
    )

    assert not epistemic_access(
        context,
        "john",
        took,
        boundary,
    )

    assert epistemic_gap(
        context,
        "john",
        took,
        boundary,
    )


def test_character_knowledge_requires_positive_access():
    entered = Proposition.atom(
        "enter",
        (
            ("actor", "john"),
            ("destination", "room"),
        ),
    )

    context = SemanticContext(
        referents=(
            Referent("john", "John"),
            Referent("mary", "Mary"),
            Referent("peter", "Peter"),
            Referent(
                "room",
                "Room",
                kind="place",
            ),
        ),
        propositions=(entered,),
        evidence=(
            ev(
                "world",
                "P01",
                1,
            ),
            ev(
                "mary-saw",
                "P02",
                2,
            ),
        ),
        changes=(
            SemanticChange(
                position=1,
                kind=ASSERT,
                target_key=entered.key,
                evidence_ids=("world",),
            ),
            SemanticChange(
                position=2,
                kind=KNOWLEDGE_ADD,
                subject_id="mary",
                target_key=entered.key,
                evidence_ids=("mary-saw",),
            ),
        ),
    )

    boundary = KnowledgeBoundary(
        position=2
    )

    assert epistemic_access(
        context,
        "mary",
        entered,
        boundary,
    )

    assert not epistemic_access(
        context,
        "peter",
        entered,
        boundary,
    )

    assert epistemic_gap(
        context,
        "peter",
        entered,
        boundary,
    )


def test_context_packet_drills_to_source():
    entered = Proposition.atom(
        "enter",
        (
            ("actor", "john"),
            ("destination", "room"),
        ),
    )

    context = SemanticContext(
        propositions=(entered,),
        evidence=(
            ev(
                "e1",
                "b1.ch001.s001.p003.x00042",
                42,
                "John entered the room.",
            ),
        ),
        changes=(
            SemanticChange(
                position=42,
                kind=ASSERT,
                target_key=entered.key,
                evidence_ids=("e1",),
            ),
        ),
    )

    packet = build_context_packet(
        context,
        "Did John enter?",
        (entered,),
        KnowledgeBoundary(
            position=42
        ),
    )

    assert packet.proposition_keys == (
        entered.key,
    )

    assert packet.evidence_ids == (
        "e1",
    )

    assert packet.source_ids == (
        "b1.ch001.s001.p003.x00042",
    )


def test_visible_evidence_respects_boundary():
    context = SemanticContext(
        evidence=(
            ev(
                "early",
                "CH02.P01",
                2,
            ),
            ev(
                "late",
                "CH17.P01",
                17,
            ),
        ),
    )

    assert [
        e.id
        for e in visible_evidence(
            context,
            KnowledgeBoundary(
                position=5
            ),
        )
    ] == [
        "early",
    ]
