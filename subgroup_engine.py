"""Subgroup validation, generation and (budgeted) enumeration."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

from group_engine import Group
from group_validation import CheckResult


@dataclass
class SubgroupReport:
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def is_subgroup(self) -> bool:
        return bool(self.checks) and all(c.passed for c in self.checks)

    def explain(self) -> str:
        return "\n".join(f"[{'PASS' if c.passed else 'FAIL'}] {c.name}: {c.detail}" for c in self.checks)


def check_subgroup(G: Group, subset: Iterable[int]) -> SubgroupReport:
    """Test the subgroup criteria explicitly: non-empty, identity, closure, inverses.

    No shortcut is taken: a set is a subgroup only if every condition is verified.
    """
    S = frozenset(subset)
    rep = SubgroupReport()
    L = G.label
    bad = [x for x in S if not 0 <= x < G.order]
    if bad:
        rep.checks.append(CheckResult("Subset of G", False, "Some elements are not in G."))
        return rep
    rep.checks.append(CheckResult("Subset of G", True, f"All {len(S)} elements belong to {G.name}."))
    if not S:
        rep.checks.append(CheckResult("Non-empty", False, "A subgroup must contain at least the identity."))
        return rep
    rep.checks.append(CheckResult("Non-empty", True, f"|H| = {len(S)}."))
    if G.identity not in S:
        rep.checks.append(CheckResult("Identity", False, f"The identity {L(G.identity)} of G is not in H."))
        return rep
    rep.checks.append(CheckResult("Identity", True, f"{L(G.identity)} is in H."))
    for a in sorted(S):
        for b in sorted(S):
            p = G.mul(a, b)
            if p not in S:
                rep.checks.append(CheckResult("Closure", False,
                                  f"{L(a)} * {L(b)} = {L(p)} is not in H.", (a, b, p)))
                return rep
    rep.checks.append(CheckResult("Closure", True, "Every product of two elements of H lies in H."))
    for a in sorted(S):
        if G.inv(a) not in S:
            rep.checks.append(CheckResult("Inverses", False,
                              f"The inverse of {L(a)} is {L(G.inv(a))}, which is not in H.", (a,)))
            return rep
    rep.checks.append(CheckResult("Inverses", True, "Every element of H has its inverse in H."))
    return rep


def is_subgroup(G: Group, subset: Iterable[int]) -> bool:
    return check_subgroup(G, subset).is_subgroup


def generate_subgroup(G: Group, gens: Iterable[int]) -> FrozenSet[int]:
    """The subgroup <gens>: closure of {e} under right multiplication by the generators.

    In a finite group this orbit is exactly the generated subgroup.
    """
    gens = list(gens)
    seen = {G.identity}
    stack = [G.identity]
    while stack:
        x = stack.pop()
        for g in gens:
            y = G.mul(x, g)
            if y not in seen:
                seen.add(y)
                stack.append(y)
    return frozenset(seen)


def cyclic_subgroup(G: Group, g: int) -> FrozenSet[int]:
    return generate_subgroup(G, [g])


@dataclass
class SubgroupSearch:
    subgroups: List[FrozenSet[int]]
    exhaustive: bool
    note: str

    def of_order(self, k: int) -> List[FrozenSet[int]]:
        return [H for H in self.subgroups if len(H) == k]


def all_subgroups(G: Group, max_subgroups: int = 2000, max_seconds: float = 10.0) -> SubgroupSearch:
    """Enumerate subgroups of G by repeatedly joining known subgroups with cyclic subgroups.

    Every subgroup is a join of cyclic subgroups, so the search is complete when it
    terminates. If a resource budget is hit, the result is flagged ``exhaustive=False``
    and must not be used to claim that a subgroup does *not* exist.
    """
    start = time.monotonic()
    cyc = {}
    for g in G.elements:
        C = cyclic_subgroup(G, g)
        cyc.setdefault(C, g)
    trivial = frozenset({G.identity})
    gens_of: Dict[FrozenSet[int], Tuple[int, ...]] = {trivial: ()}
    for C, g in cyc.items():
        gens_of.setdefault(C, (g,))
    frontier = list(gens_of)
    cyc_items = list(cyc.items())
    while frontier:
        new = []
        for H in frontier:
            for C, g in cyc_items:
                if g in H:
                    continue
                K = generate_subgroup(G, gens_of[H] + (g,))
                if K not in gens_of:
                    gens_of[K] = gens_of[H] + (g,)
                    new.append(K)
                if len(gens_of) > max_subgroups or time.monotonic() - start > max_seconds:
                    subs = sorted(gens_of, key=lambda s: (len(s), sorted(s)))
                    return SubgroupSearch(subs, False,
                        f"Search stopped at its resource limit after finding {len(subs)} subgroups; "
                        "the list may be incomplete, so absence of a subgroup is NOT proven.")
        frontier = new
    subs = sorted(gens_of, key=lambda s: (len(s), sorted(s)))
    return SubgroupSearch(subs, True, f"Exhaustive search complete: {len(subs)} subgroups found.")


def subgroups_of_order(G: Group, k: int, **limits) -> SubgroupSearch:
    """Subgroups of order k, with a clear exhaustive / resource-limited flag."""
    res = all_subgroups(G, **limits)
    found = res.of_order(k)
    if res.exhaustive:
        note = (f"Exhaustive search: {len(found)} subgroup(s) of order {k}." if found
                else f"Exhaustive search: G has NO subgroup of order {k}.")
    else:
        note = f"Resource-limited search: found {len(found)} subgroup(s) of order {k}; list may be incomplete."
    return SubgroupSearch(found, res.exhaustive, note)
