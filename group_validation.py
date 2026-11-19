"""Group-axiom validation for finite multiplication (Cayley) tables.

Nothing in AlgebraLab is called a group until it passes these checks.
Every failed check carries a concrete witness so the UI can explain *why*.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    witness: Optional[tuple] = None


@dataclass
class GroupReport:
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def is_group(self) -> bool:
        return bool(self.checks) and all(c.passed for c in self.checks)

    def get(self, name: str) -> CheckResult:
        for c in self.checks:
            if c.name == name:
                return c
        raise KeyError(name)

    def explain(self) -> str:
        lines = []
        for c in self.checks:
            lines.append(f"[{'PASS' if c.passed else 'FAIL'}] {c.name}: {c.detail}")
        return "\n".join(lines)


def validate_table(table: Sequence[Sequence[int]], labels: Optional[Sequence[str]] = None) -> GroupReport:
    """Check closure, associativity, identity and inverses of a table of indices.

    ``table[a][b]`` is the index of a*b. Checks stop early only where later
    checks would be meaningless (e.g. a malformed table).
    """
    rep = GroupReport()
    try:
        T = np.array(table, dtype=np.int64)
    except (ValueError, TypeError):
        rep.checks.append(CheckResult("Well-formed table", False, "Table rows must all have the same length and contain integers."))
        return rep
    if T.ndim != 2 or T.shape[0] != T.shape[1] or T.shape[0] == 0:
        rep.checks.append(CheckResult("Well-formed table", False, "The table must be a non-empty square n x n array."))
        return rep
    n = T.shape[0]
    lab = (lambda i: str(labels[i])) if labels is not None else (lambda i: str(i))
    rep.checks.append(CheckResult("Well-formed table", True, f"{n} x {n} table."))

    # Closure: every entry must be a valid element index.
    bad = np.argwhere((T < 0) | (T >= n))
    if bad.size:
        a, b = (int(x) for x in bad[0])
        rep.checks.append(CheckResult("Closure", False,
                          f"{lab(a)} * {lab(b)} = {T[a, b]} is not an element of the set.", (a, b)))
        return rep
    rep.checks.append(CheckResult("Closure", True, "Every product lies in the set."))

    # Associativity (vectorised, O(n^3) arithmetic but fast in numpy).
    idx = np.arange(n)
    for a in range(n):
        left = T[T[a][:, None], idx[None, :]]   # (a*b)*c indexed [b, c]
        right = T[a][T]                          # a*(b*c) indexed [b, c]
        diff = np.argwhere(left != right)
        if diff.size:
            b, c = (int(x) for x in diff[0])
            rep.checks.append(CheckResult(
                "Associativity", False,
                f"({lab(a)}*{lab(b)})*{lab(c)} = {lab(int(left[b, c]))} but "
                f"{lab(a)}*({lab(b)}*{lab(c)}) = {lab(int(right[b, c]))}.", (a, b, c)))
            return rep
    rep.checks.append(CheckResult("Associativity", True, f"All {n**3} triples satisfy (ab)c = a(bc)."))

    # Identity element.
    e = None
    for cand in range(n):
        if np.array_equal(T[cand], idx) and np.array_equal(T[:, cand], idx):
            e = cand
            break
    if e is None:
        rep.checks.append(CheckResult("Identity", False, "No element e satisfies e*x = x*e = x for all x."))
        return rep
    rep.checks.append(CheckResult("Identity", True, f"Identity is {lab(e)}.", (e,)))

    # Inverses.
    for a in range(n):
        if not np.any(T[a] == e) or not np.any((T[a] == e) & (T[:, a] == e)):
            rep.checks.append(CheckResult("Inverses", False, f"{lab(a)} has no two-sided inverse.", (a,)))
            return rep
    rep.checks.append(CheckResult("Inverses", True, "Every element has a two-sided inverse."))
    return rep
