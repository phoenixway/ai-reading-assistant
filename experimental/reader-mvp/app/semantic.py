from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable


ASSERT = "ASSERT"
RETRACT = "RETRACT"
IDENTITY_ADD = "IDENTITY_ADD"
IDENTITY_REMOVE = "IDENTITY_REMOVE"
KNOWLEDGE_ADD = "KNOWLEDGE_ADD"
KNOWLEDGE_REMOVE = "KNOWLEDGE_REMOVE"

_CHANGE_KINDS = {
    ASSERT,
    RETRACT,
    IDENTITY_ADD,
    IDENTITY_REMOVE,
    KNOWLEDGE_ADD,
    KNOWLEDGE_REMOVE,
}


@dataclass(frozen=True)
class Referent:
    id: str
    label: str | None = None
    kind: str = "entity"

    def __post_init__(self):
        if not self.id.strip():
            raise ValueError("Referent.id must be non-empty")


@dataclass(frozen=True)
class Predication:
    predicate: str
    roles: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if not self.predicate.strip():
            raise ValueError("predicate must be non-empty")

    def structural_data(self):
        return {
            "predicate": self.predicate,
            "roles": sorted(
                [list(x) for x in self.roles]
            ),
        }


@dataclass(frozen=True)
class Proposition:
    """
    Immutable structural proposition node.

    Identity projection never rewrites this object.
    """

    op: str
    predication: Predication | None = None
    children: tuple["Proposition", ...] = ()

    def __post_init__(self):
        if self.op == "PRED":
            if self.predication is None:
                raise ValueError("PRED requires predication")
        elif self.op == "NOT":
            if self.predication is not None or len(self.children) != 1:
                raise ValueError("NOT requires one child")
        elif self.op == "OR":
            if self.predication is not None or len(self.children) < 2:
                raise ValueError("OR requires at least two children")
        else:
            raise ValueError(f"unsupported op: {self.op}")

    @classmethod
    def atom(
        cls,
        predicate: str,
        roles: Iterable[tuple[str, str]] = (),
        children: Iterable["Proposition"] = (),
    ):
        return cls(
            op="PRED",
            predication=Predication(
                predicate,
                tuple(roles),
            ),
            children=tuple(children),
        )

    @classmethod
    def not_(cls, child: "Proposition"):
        return cls(
            op="NOT",
            children=(child,),
        )

    @classmethod
    def or_(cls, *children: "Proposition"):
        return cls(
            op="OR",
            children=tuple(children),
        )

    @classmethod
    def modal(
        cls,
        modality: str,
        child: "Proposition",
    ):
        if not modality.strip():
            raise ValueError("modality must be non-empty")

        return cls.atom(
            "modal",
            (("mode", modality),),
            (child,),
        )

    @classmethod
    def conditional(
        cls,
        antecedent: "Proposition",
        consequent: "Proposition",
        *,
        counterfactual: bool = False,
    ):
        return cls.atom(
            "conditional",
            (
                (
                    "counterfactual",
                    "true" if counterfactual else "false",
                ),
            ),
            (
                antecedent,
                consequent,
            ),
        )

    @classmethod
    def cause(
        cls,
        cause: "Proposition",
        effect: "Proposition",
    ):
        return cls.atom(
            "cause",
            (),
            (
                cause,
                effect,
            ),
        )

    @classmethod
    def attitude(
        cls,
        subject_id: str,
        attitude: str,
        child: "Proposition",
    ):
        if not subject_id.strip():
            raise ValueError("attitude subject required")

        if not attitude.strip():
            raise ValueError("attitude type required")

        return cls.atom(
            attitude,
            (("subject", subject_id),),
            (child,),
        )

    def structural_data(self):
        return {
            "op": self.op,
            "predication": (
                self.predication.structural_data()
                if self.predication
                else None
            ),
            "children": [
                child.structural_data()
                for child in self.children
            ],
        }

    @property
    def key(self):
        raw = json.dumps(
            self.structural_data(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()

        return sha256(raw).hexdigest()


@dataclass(frozen=True)
class Evidence:
    id: str
    source_ids: tuple[str, ...]
    position: int
    text: str = ""

    def __post_init__(self):
        if not self.id:
            raise ValueError("Evidence.id required")
        if not self.source_ids:
            raise ValueError("Evidence requires SOURCE")


@dataclass(frozen=True)
class SemanticChange:
    position: int
    kind: str
    sequence: int = 0
    target_key: str | None = None
    subject_id: str | None = None
    left_id: str | None = None
    right_id: str | None = None
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if self.kind not in _CHANGE_KINDS:
            raise ValueError(self.kind)

        if self.kind in {
            ASSERT,
            RETRACT,
            KNOWLEDGE_ADD,
            KNOWLEDGE_REMOVE,
        } and not self.target_key:
            raise ValueError(
                f"{self.kind} requires target_key"
            )

        if self.kind in {
            KNOWLEDGE_ADD,
            KNOWLEDGE_REMOVE,
        } and not self.subject_id:
            raise ValueError(
                f"{self.kind} requires subject_id"
            )

        if self.kind in {
            IDENTITY_ADD,
            IDENTITY_REMOVE,
        } and (
            not self.left_id
            or not self.right_id
        ):
            raise ValueError(
                f"{self.kind} requires identity endpoints"
            )


@dataclass(frozen=True)
class TemporalConstraint:
    """
    Story-time relation attached to an immutable proposition.

    This is deliberately separate from Evidence.position, which is
    discourse/reader visibility order.

    Example:

        proposition:
            John hid the key

        evidence.position:
            chapter/discourse position where this is narrated

        temporal relation:
            proposition happened twenty years before a story anchor
    """

    proposition_key: str
    relation: str
    anchor: str
    amount: float | None = None
    unit: str | None = None
    approximate: bool = False

    def __post_init__(self):
        if not self.proposition_key:
            raise ValueError(
                "TemporalConstraint requires proposition_key"
            )

        if not self.relation.strip():
            raise ValueError(
                "TemporalConstraint requires relation"
            )

        if not self.anchor.strip():
            raise ValueError(
                "TemporalConstraint requires anchor"
            )


@dataclass(frozen=True)
class KnowledgeBoundary:
    position: int | None = None
    evidence_ids: frozenset[str] | None = None


@dataclass(frozen=True)
class TruthView:
    proposition_key: str
    status: str
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContextPacket:
    query: str
    boundary: KnowledgeBoundary
    proposition_keys: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class SemanticContext:
    referents: tuple[Referent, ...] = ()
    propositions: tuple[Proposition, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    changes: tuple[SemanticChange, ...] = ()
    temporal_constraints: tuple[TemporalConstraint, ...] = ()

    @property
    def proposition_by_key(self):
        return {
            p.key: p
            for p in self.propositions
        }

    @property
    def evidence_by_id(self):
        return {
            e.id: e
            for e in self.evidence
        }


def visible_evidence(
    context: SemanticContext,
    boundary: KnowledgeBoundary,
):
    rows = []

    for e in context.evidence:
        if (
            boundary.position is not None
            and e.position > boundary.position
        ):
            continue

        if (
            boundary.evidence_ids is not None
            and e.id not in boundary.evidence_ids
        ):
            continue

        rows.append(e)

    return tuple(
        sorted(
            rows,
            key=lambda e: (e.position, e.id),
        )
    )


def _visible_changes(
    context: SemanticContext,
    boundary: KnowledgeBoundary,
):
    visible_ids = {
        e.id
        for e in visible_evidence(
            context,
            boundary,
        )
    }

    rows = []

    for change in context.changes:
        if (
            boundary.position is not None
            and change.position > boundary.position
        ):
            continue

        if not all(
            eid in visible_ids
            for eid in change.evidence_ids
        ):
            continue

        rows.append(change)

    return tuple(
        sorted(
            rows,
            key=lambda c: (
                c.position,
                c.sequence,
            ),
        )
    )


def truth_view(
    context: SemanticContext,
    proposition: Proposition | str,
    boundary: KnowledgeBoundary,
):
    key = (
        proposition
        if isinstance(proposition, str)
        else proposition.key
    )

    latest = None

    for change in _visible_changes(
        context,
        boundary,
    ):
        if (
            change.target_key == key
            and change.kind in {
                ASSERT,
                RETRACT,
            }
        ):
            latest = change

    if latest is None:
        return TruthView(
            key,
            "UNKNOWN",
        )

    return TruthView(
        key,
        (
            "SUPPORTED"
            if latest.kind == ASSERT
            else "RETRACTED"
        ),
        latest.evidence_ids,
    )


def identity_projection(
    context: SemanticContext,
    boundary: KnowledgeBoundary,
):
    active = {}

    for change in _visible_changes(
        context,
        boundary,
    ):
        if change.kind not in {
            IDENTITY_ADD,
            IDENTITY_REMOVE,
        }:
            continue

        pair = tuple(
            sorted(
                (
                    change.left_id,
                    change.right_id,
                )
            )
        )

        active[pair] = (
            change.kind == IDENTITY_ADD
        )

    ids = {
        r.id
        for r in context.referents
    }

    for left, right in active:
        ids.add(left)
        ids.add(right)

    parent = {
        value: value
        for value in ids
    }

    def find(value):
        if parent[value] != value:
            parent[value] = find(
                parent[value]
            )
        return parent[value]

    def union(left, right):
        a = find(left)
        b = find(right)

        if a == b:
            return

        root = min(a, b)
        other = b if root == a else a
        parent[other] = root

    for (left, right), enabled in sorted(
        active.items()
    ):
        if enabled:
            union(left, right)

    return {
        value: find(value)
        for value in sorted(ids)
    }


def _project_proposition(
    proposition: Proposition,
    projection: dict[str, str],
):
    if proposition.op == "NOT":
        return Proposition.not_(
            _project_proposition(
                proposition.children[0],
                projection,
            )
        )

    if proposition.op == "OR":
        return Proposition.or_(
            *[
                _project_proposition(
                    child,
                    projection,
                )
                for child
                in proposition.children
            ]
        )

    pred = proposition.predication
    assert pred is not None

    return Proposition.atom(
        pred.predicate,
        (
            (
                role,
                projection.get(
                    value,
                    value,
                ),
            )
            for role, value
            in pred.roles
        ),
        (
            _project_proposition(
                child,
                projection,
            )
            for child
            in proposition.children
        ),
    )


def resolve_then_aggregate(
    context: SemanticContext,
    propositions: Iterable[Proposition | str],
    boundary: KnowledgeBoundary,
):
    projection = identity_projection(
        context,
        boundary,
    )

    grouped = {}
    by_key = context.proposition_by_key

    for value in propositions:
        proposition = (
            by_key[value]
            if isinstance(value, str)
            else value
        )

        projected = _project_proposition(
            proposition,
            projection,
        )

        grouped.setdefault(
            projected.key,
            [],
        ).append(
            proposition.key
        )

    return {
        key: tuple(values)
        for key, values
        in grouped.items()
    }


def epistemic_access(
    context: SemanticContext,
    subject_id: str,
    proposition: Proposition | str,
    boundary: KnowledgeBoundary,
):
    key = (
        proposition
        if isinstance(proposition, str)
        else proposition.key
    )

    projection = identity_projection(
        context,
        boundary,
    )

    canonical = projection.get(
        subject_id,
        subject_id,
    )

    equivalent_subjects = {
        value
        for value, root
        in projection.items()
        if root == canonical
    }

    equivalent_subjects.add(
        subject_id
    )

    latest = None

    for change in _visible_changes(
        context,
        boundary,
    ):
        if (
            change.kind
            in {
                KNOWLEDGE_ADD,
                KNOWLEDGE_REMOVE,
            }
            and change.target_key == key
            and change.subject_id
            in equivalent_subjects
        ):
            latest = change

    return (
        latest is not None
        and latest.kind == KNOWLEDGE_ADD
    )


def epistemic_gap(
    context: SemanticContext,
    subject_id: str,
    proposition: Proposition | str,
    boundary: KnowledgeBoundary,
):
    return (
        truth_view(
            context,
            proposition,
            boundary,
        ).status
        == "SUPPORTED"
        and not epistemic_access(
            context,
            subject_id,
            proposition,
            boundary,
        )
    )


def build_context_packet(
    context: SemanticContext,
    query: str,
    propositions: Iterable[Proposition | str],
    boundary: KnowledgeBoundary,
):
    keys = []
    evidence_ids = []

    for proposition in propositions:
        view = truth_view(
            context,
            proposition,
            boundary,
        )

        if view.status != "SUPPORTED":
            continue

        keys.append(
            view.proposition_key
        )
        evidence_ids.extend(
            view.evidence_ids
        )

    visible = {
        e.id: e
        for e in visible_evidence(
            context,
            boundary,
        )
    }

    evidence_ids = tuple(
        dict.fromkeys(
            eid
            for eid in evidence_ids
            if eid in visible
        )
    )

    source_ids = tuple(
        dict.fromkeys(
            source_id
            for eid in evidence_ids
            for source_id
            in visible[eid].source_ids
        )
    )

    return ContextPacket(
        query=query,
        boundary=boundary,
        proposition_keys=tuple(
            dict.fromkeys(keys)
        ),
        evidence_ids=evidence_ids,
        source_ids=source_ids,
    )

def temporal_constraints_for(
    context: SemanticContext,
    proposition: Proposition | str,
):
    key = (
        proposition
        if isinstance(proposition, str)
        else proposition.key
    )

    return tuple(
        constraint
        for constraint
        in context.temporal_constraints
        if constraint.proposition_key == key
    )


def truth_history(
    context: SemanticContext,
    proposition: Proposition | str,
    boundary: KnowledgeBoundary,
):
    """
    Visible ASSERT/RETRACT history for one immutable proposition.

    This supports historical reconstruction without rewriting the
    proposition itself.
    """

    key = (
        proposition
        if isinstance(proposition, str)
        else proposition.key
    )

    return tuple(
        change
        for change in _visible_changes(
            context,
            boundary,
        )
        if (
            change.target_key == key
            and change.kind in {
                ASSERT,
                RETRACT,
            }
        )
    )
