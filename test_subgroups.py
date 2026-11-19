import group_engine as ge
import subgroup_engine as se


def idx(G, *labels):
    return [G.index(l) for l in labels]


def test_valid_subgroup_accepted():
    G = ge.dihedral(4)
    H = idx(G, "e", "r^2")
    rep = se.check_subgroup(G, H)
    assert rep.is_subgroup, rep.explain()


def test_non_subgroups_rejected_with_witness():
    G = ge.symmetric(3)
    # missing identity
    assert not se.is_subgroup(G, idx(G, "(1 2)"))
    # not closed: (1 2),(2 3) generate more
    H = idx(G, "e", "(1 2)", "(2 3)")
    rep = se.check_subgroup(G, H)
    assert not rep.is_subgroup
    closure = [c for c in rep.checks if c.name == "Closure"][0]
    assert not closure.passed and closure.witness is not None
    # empty
    assert not se.is_subgroup(G, [])
    # out of range
    assert not se.is_subgroup(G, [0, 99])


def test_subgroup_missing_inverse_detected_when_closed_but_infinite_style_set():
    # In a finite group closure implies inverses, but the checker still verifies inverses explicitly.
    G = ge.cyclic(6)
    rep = se.check_subgroup(G, [0, 2, 4])
    assert rep.is_subgroup
    assert [c.name for c in rep.checks][-1] == "Inverses"


def test_generate_subgroup():
    G = ge.symmetric(3)
    assert len(se.generate_subgroup(G, idx(G, "(1 2)", "(2 3)"))) == 6
    assert len(se.generate_subgroup(G, idx(G, "(1 2 3)"))) == 3
    assert se.generate_subgroup(G, []) == frozenset({G.identity})
    Z12 = ge.cyclic(12)
    assert len(se.generate_subgroup(Z12, [4, 6])) == 6   # <gcd(4,6,12)=2>


def test_generated_sets_are_always_subgroups():
    for G in [ge.symmetric(4), ge.dihedral(6), ge.direct_product(ge.cyclic(2), ge.cyclic(6))]:
        for g in G.elements:
            assert se.is_subgroup(G, se.cyclic_subgroup(G, g))
            assert len(se.cyclic_subgroup(G, g)) == G.element_order(g)


def test_known_subgroup_counts():
    expected = {"Z_6": 4, "Z_12": 6, "S_3": 6, "D_4": 10, "A_4": 10, "S_4": 30, "Z_2 x Z_2": 5}
    for spec, count in expected.items():
        G = ge.parse_group_spec(spec)
        res = se.all_subgroups(G)
        assert res.exhaustive
        assert len(res.subgroups) == count, (spec, len(res.subgroups))
        for H in res.subgroups:
            assert se.is_subgroup(G, H)
            assert G.order % len(H) == 0      # Lagrange sanity check


def test_a4_has_no_subgroup_of_order_6_exhaustively():
    G = ge.alternating(4)
    res = se.subgroups_of_order(G, 6)
    assert res.exhaustive and res.subgroups == []
    assert "NO subgroup of order 6" in res.note
    # but orders 1,2,3,4,12 all occur
    for k in (1, 2, 3, 4, 12):
        assert se.subgroups_of_order(G, k).subgroups


def test_s4_has_subgroup_of_order_6_and_d4_order_8():
    assert len(se.subgroups_of_order(ge.symmetric(4), 6).subgroups) == 4
    assert len(se.subgroups_of_order(ge.symmetric(4), 8).subgroups) == 3


def test_resource_limited_search_is_flagged():
    G = ge.symmetric(4)
    res = se.all_subgroups(G, max_subgroups=5)
    assert not res.exhaustive
    assert "NOT proven" in res.note
    assert "incomplete" in se.subgroups_of_order(G, 6, max_subgroups=5).note


def test_s5_subgroup_count():
    res = se.all_subgroups(ge.symmetric(5), max_seconds=60, max_subgroups=5000)
    assert res.exhaustive and len(res.subgroups) == 156
