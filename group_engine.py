"""Core finite-group representation and constructors for AlgebraLab.

A ``Group`` is stored as a full multiplication table of element indices.
The identity is always validated; constructors put it at index 0.

Conventions
-----------
* Permutations compose right-to-left: (p*q)(x) = p(q(x)).
* Cycle notation is 1-indexed, e.g. (1 2 3).
* D_n is the dihedral group of order 2n (D_4 has order 8), with
  r^n = s^2 = e and s r = r^-1 s. Elements are r^k s^f.
* Z_n is written additively; direct product elements are tuples.
"""
from __future__ import annotations

import itertools
from math import gcd
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from group_validation import GroupReport, validate_table

WARN_ORDER = 120      # warn above this order
MAX_ORDER = 720       # hard limit (S_6): table has 518,400 entries


class InvalidGroupError(ValueError):
    """Raised when a supplied structure fails a group axiom."""

    def __init__(self, report: GroupReport):
        self.report = report
        super().__init__("Not a group.\n" + report.explain())


class GroupTooLargeError(ValueError):
    pass


class Group:
    def __init__(self, name: str, labels: Sequence[str], table, *, verify: bool = True,
                 description: str = "", warnings: Optional[List[str]] = None):
        n = len(labels)
        if n > MAX_ORDER:
            raise GroupTooLargeError(f"Order {n} exceeds the limit of {MAX_ORDER} elements.")
        if len(set(labels)) != n:
            raise ValueError("Element labels must be distinct.")
        self.name = name
        self.labels: List[str] = [str(l) for l in labels]
        self.table = np.array(table, dtype=np.int64)
        self.description = description
        self.warnings: List[str] = list(warnings or [])
        if n > WARN_ORDER:
            self.warnings.append(f"Large group (order {n}); some operations (e.g. subgroup search) may be slow.")
        if verify:
            report = validate_table(self.table, self.labels)
            if not report.is_group:
                raise InvalidGroupError(report)
            self.report: Optional[GroupReport] = report
        else:
            self.report = None
        self._label_index: Dict[str, int] = {l: i for i, l in enumerate(self.labels)}
        self.identity: int = self._find_identity()
        self._inv: List[int] = [int(np.where(self.table[a] == self.identity)[0][0]) for a in range(n)]

    # ---- basic structure -------------------------------------------------
    def _find_identity(self) -> int:
        idx = np.arange(self.order)
        for e in range(self.order):
            if np.array_equal(self.table[e], idx) and np.array_equal(self.table[:, e], idx):
                return e
        raise InvalidGroupError(validate_table(self.table, self.labels))

    @property
    def order(self) -> int:
        return len(self.labels)

    @property
    def elements(self) -> range:
        return range(self.order)

    def mul(self, a: int, b: int) -> int:
        return int(self.table[a, b])

    def inv(self, a: int) -> int:
        return self._inv[a]

    def index(self, label: str) -> int:
        try:
            return self._label_index[str(label)]
        except KeyError:
            raise KeyError(f"'{label}' is not an element of {self.name}.")

    def label(self, a: int) -> str:
        return self.labels[a]

    def power(self, a: int, k: int) -> int:
        if k < 0:
            a, k = self.inv(a), -k
        result, base = self.identity, a
        while k:
            if k & 1:
                result = self.mul(result, base)
            base = self.mul(base, base)
            k >>= 1
        return result

    def element_order(self, a: int) -> int:
        k, x = 1, a
        while x != self.identity:
            x = self.mul(x, a)
            k += 1
        return k

    def element_orders(self) -> Dict[int, int]:
        return {a: self.element_order(a) for a in self.elements}

    def is_abelian(self) -> bool:
        return bool(np.array_equal(self.table, self.table.T))

    def conjugate(self, g: int, x: int) -> int:
        """g x g^-1"""
        return self.mul(self.mul(g, x), self.inv(g))

    # ---- subset helpers --------------------------------------------------
    def left_translate(self, g: int, S: Iterable[int]) -> FrozenSet[int]:
        return frozenset(self.mul(g, s) for s in S)

    def right_translate(self, S: Iterable[int], g: int) -> FrozenSet[int]:
        return frozenset(self.mul(s, g) for s in S)

    def labels_of(self, S: Iterable[int]) -> List[str]:
        return [self.labels[i] for i in sorted(S)]

    def __repr__(self) -> str:
        return f"Group({self.name}, order={self.order})"


# ---------------------------------------------------------------------------
# Constructors
# ---------------------------------------------------------------------------
def _table_from_product(elements: Sequence, op) -> Tuple[List[List[int]], Dict]:
    index = {e: i for i, e in enumerate(elements)}
    n = len(elements)
    table = [[index[op(elements[a], elements[b])] for b in range(n)] for a in range(n)]
    return table, index


def cyclic(n: int) -> Group:
    if n < 1:
        raise ValueError("n must be a positive integer.")
    elems = list(range(n))
    table, _ = _table_from_product(elems, lambda a, b: (a + b) % n)
    return Group(f"Z_{n}", [str(e) for e in elems], table, verify=False,
                 description=f"Integers mod {n} under addition.")


def direct_product(*factors: Group) -> Group:
    if len(factors) < 2:
        raise ValueError("A direct product needs at least two factors.")
    size = 1
    for f in factors:
        size *= f.order
    if size > MAX_ORDER:
        raise GroupTooLargeError(f"Direct product has order {size}, above the limit of {MAX_ORDER}.")
    elems = list(itertools.product(*[range(f.order) for f in factors]))
    # put identity first
    ident = tuple(f.identity for f in factors)
    elems.remove(ident)
    elems.insert(0, ident)

    def op(x, y):
        return tuple(f.mul(a, b) for f, a, b in zip(factors, x, y))

    table, _ = _table_from_product(elems, op)
    labels = ["(" + ", ".join(f.labels[i] for f, i in zip(factors, e)) + ")" for e in elems]
    name = " x ".join(f.name for f in factors)
    return Group(name, labels, table, verify=False,
                 description="External direct product with componentwise operation.")


# ---- permutations ----------------------------------------------------------
def perm_compose(p: Tuple[int, ...], q: Tuple[int, ...]) -> Tuple[int, ...]:
    """(p*q)(x) = p(q(x)); permutations are tuples of images of 0..n-1."""
    return tuple(p[q[x]] for x in range(len(p)))


def perm_to_cycles(p: Tuple[int, ...]) -> str:
    n, seen, parts = len(p), set(), []
    for start in range(n):
        if start in seen or p[start] == start:
            seen.add(start)
            continue
        cyc, x = [], start
        while x not in seen:
            seen.add(x)
            cyc.append(x + 1)
            x = p[x]
        parts.append("(" + " ".join(map(str, cyc)) + ")")
    return "".join(parts) if parts else "e"


def perm_parity(p: Tuple[int, ...]) -> int:
    """0 for even, 1 for odd."""
    seen, parity = set(), 0
    for s in range(len(p)):
        if s in seen:
            continue
        length, x = 0, s
        while x not in seen:
            seen.add(x)
            x = p[x]
            length += 1
        parity ^= (length - 1) & 1
    return parity


def parse_cycles(text: str, n: int) -> Tuple[int, ...]:
    """Parse e.g. '(1 2)(3 4)' (1-indexed, disjoint or not; applied right-to-left)."""
    text = text.strip()
    if text in ("e", "()", ""):
        return tuple(range(n))
    result = tuple(range(n))
    for chunk in text.replace(")", ")|").split("|"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if not (chunk.startswith("(") and chunk.endswith(")")):
            raise ValueError(f"Cannot parse cycle '{chunk}'.")
        pts = [int(t) - 1 for t in chunk[1:-1].replace(",", " ").split()]
        if len(set(pts)) != len(pts) or any(not 0 <= x < n for x in pts):
            raise ValueError(f"Invalid cycle '{chunk}' for S_{n}.")
        cyc = list(range(n))
        for i, x in enumerate(pts):
            cyc[x] = pts[(i + 1) % len(pts)]
        result = perm_compose(result, tuple(cyc))   # leftmost cycle is applied last
    return result


def _permutation_group(name: str, perms: List[Tuple[int, ...]], description: str) -> Group:
    n = len(perms[0])
    ident = tuple(range(n))
    perms = sorted(perms, key=lambda p: (p != ident, p))
    table, _ = _table_from_product(perms, perm_compose)
    return Group(name, [perm_to_cycles(p) for p in perms], table, verify=False, description=description)


def symmetric(n: int) -> Group:
    if n < 1:
        raise ValueError("n must be a positive integer.")
    import math
    if math.factorial(n) > MAX_ORDER:
        raise GroupTooLargeError(f"S_{n} has order {math.factorial(n)}; the limit is S_6 (order {MAX_ORDER}).")
    perms = list(itertools.permutations(range(n)))
    return _permutation_group(f"S_{n}", perms, f"All permutations of {{1..{n}}}; composition right-to-left.")


def alternating(n: int) -> Group:
    if n < 1:
        raise ValueError("n must be a positive integer.")
    import math
    if math.factorial(n) // (1 if n == 1 else 2) > MAX_ORDER:
        raise GroupTooLargeError(f"A_{n} is too large for the table-based engine (limit {MAX_ORDER}).")
    perms = [p for p in itertools.permutations(range(n)) if perm_parity(p) == 0]
    return _permutation_group(f"A_{n}", perms, f"Even permutations of {{1..{n}}}.")


def dihedral(n: int) -> Group:
    """Dihedral group D_n of order 2n (symmetries of a regular n-gon), n >= 3."""
    if n < 3:
        raise ValueError("Dihedral groups D_n require n >= 3.")
    elems = [(k, f) for f in (0, 1) for k in range(n)]   # r^k s^f; (0,0) first

    def op(x, y):
        (a, f), (b, g) = x, y
        return ((a + (b if f == 0 else -b)) % n, (f + g) % 2)

    def lab(k, f):
        if k == 0 and f == 0:
            return "e"
        r = "" if k == 0 else ("r" if k == 1 else f"r^{k}")
        return r + ("s" if f else "")

    table, _ = _table_from_product(elems, op)
    return Group(f"D_{n}", [lab(*e) for e in elems], table, verify=False,
                 description=f"Symmetries of a regular {n}-gon (order {2*n}); r^{n}=s^2=e, sr=r^-1 s.")


def from_table(name: str, labels: Sequence[str], table: Sequence[Sequence], *, by_label: bool = True) -> Group:
    """Build a group from a user-supplied table.

    ``table`` entries are element labels (by_label=True) or indices. The table is
    fully validated; ``InvalidGroupError`` explains the first failing axiom.
    """
    labels = [str(l) for l in labels]
    if len(set(labels)) != len(labels):
        raise ValueError("Element labels must be distinct.")
    n = len(labels)
    if n > MAX_ORDER:
        raise GroupTooLargeError(f"Order {n} exceeds the limit of {MAX_ORDER}.")
    if by_label:
        pos = {l: i for i, l in enumerate(labels)}
        try:
            idx = [[pos[str(x)] for x in row] for row in table]
        except KeyError as exc:
            raise ValueError(f"Table entry {exc} is not one of the declared elements (closure fails).")
    else:
        idx = [list(row) for row in table]
    return Group(name, labels, idx, verify=True, description="User-defined group from a multiplication table.")


_FAMILIES = {"Z": cyclic, "C": cyclic, "S": symmetric, "A": alternating, "D": dihedral}


def parse_group_spec(spec: str) -> Group:
    """Parse strings like 'Z_6', 'Z_2xZ_6', 'S_4', 'A_4', 'D_4'."""
    s = spec.replace(" ", "").replace("\u00d7", "x").replace("*", "x")
    built = []
    for part in s.split("x"):
        kind, _, num = part.partition("_")
        if not num.isdigit():
            raise ValueError(f"Cannot parse group '{part}'. Use forms like Z_6, S_4, A_4, D_4.")
        if kind.upper() not in _FAMILIES:
            raise ValueError(f"Unknown group family '{kind}'. Use Z, S, A or D.")
        built.append(_FAMILIES[kind.upper()](int(num)))
    return built[0] if len(built) == 1 else direct_product(*built)
