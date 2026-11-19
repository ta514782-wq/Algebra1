import group_engine as ge
from group_engine import InvalidGroupError, GroupTooLargeError, Group
from group_validation import validate_table


def raises(exc, fn, *a, **k):
    try:
        fn(*a, **k)
    except exc:
        return True
    return False


def test_orders_of_standard_groups():
    assert ge.cyclic(7).order == 7
    assert ge.symmetric(3).order == 6
    assert ge.symmetric(4).order == 24
    assert ge.symmetric(5).order == 120
    assert ge.alternating(4).order == 12
    assert ge.alternating(5).order == 60
    assert ge.dihedral(4).order == 8
    assert ge.dihedral(6).order == 12
    assert ge.direct_product(ge.cyclic(2), ge.cyclic(6)).order == 12


def test_constructed_groups_pass_full_axiom_check():
    for G in [ge.cyclic(6), ge.symmetric(4), ge.alternating(4), ge.dihedral(5),
              ge.direct_product(ge.cyclic(2), ge.cyclic(6)), ge.dihedral(4)]:
        rep = validate_table(G.table, G.labels)
        assert rep.is_group, (G.name, rep.explain())
        assert G.labels[G.identity] in ("e", "0", "(0, 0)")
        assert G.identity == 0


def test_abelian_flags():
    assert ge.cyclic(8).is_abelian()
    assert ge.direct_product(ge.cyclic(2), ge.cyclic(3)).is_abelian()
    assert not ge.symmetric(3).is_abelian()
    assert not ge.dihedral(4).is_abelian()
    assert not ge.alternating(4).is_abelian()
    assert ge.alternating(3).is_abelian()


def test_element_orders_dihedral_d4():
    G = ge.dihedral(4)
    orders = sorted(G.element_order(a) for a in G.elements)
    assert orders == [1, 2, 2, 2, 2, 2, 4, 4]
    assert G.element_order(G.index("r")) == 4
    assert G.element_order(G.index("r^2")) == 2


def test_dihedral_relation_sr_equals_r_inverse_s():
    G = ge.dihedral(5)
    s, r = G.index("s"), G.index("r")
    assert G.mul(s, r) == G.mul(G.inv(r), s)
    assert G.mul(G.index("r^2"), G.index("r^3")) == G.identity


def test_permutation_convention_and_cycles():
    S3 = ge.symmetric(3)
    a, b = S3.index("(1 2)"), S3.index("(2 3)")
    # right-to-left: (1 2)(2 3) sends 3 -> 2 -> 1, 1 -> 1 -> 2, 2 -> 3 -> 3  i.e. (1 2 3)
    assert S3.label(S3.mul(a, b)) == "(1 2 3)"
    assert ge.parse_cycles("(1 2)(2 3)", 3) == (1, 2, 0)
    assert ge.parse_cycles("e", 3) == (0, 1, 2)
    assert ge.perm_to_cycles((1, 0, 3, 2)) == "(1 2)(3 4)"
    assert raises(ValueError, ge.parse_cycles, "(1 5)", 3)


def test_power_inverse_and_conjugate():
    G = ge.symmetric(4)
    for a in G.elements:
        assert G.mul(a, G.inv(a)) == G.identity
        assert G.power(a, G.element_order(a)) == G.identity
        assert G.power(a, -1) == G.inv(a)
    g, x = G.index("(1 2)"), G.index("(1 2 3)")
    assert G.label(G.conjugate(g, x)) == "(1 3 2)"


def test_from_table_valid_klein_four():
    labels = ["e", "a", "b", "c"]
    t = [["e", "a", "b", "c"], ["a", "e", "c", "b"], ["b", "c", "e", "a"], ["c", "b", "a", "e"]]
    G = ge.from_table("V4", labels, t)
    assert G.order == 4 and G.is_abelian()


def test_invalid_tables_are_rejected_with_reasons():
    # not associative: subtraction mod 3 has a right identity 0 but is not associative
    t = [[(a - b) % 3 for b in range(3)] for a in range(3)]
    assert raises(InvalidGroupError, ge.from_table, "bad", "012", t, by_label=False)
    rep = validate_table(t)
    assert not rep.is_group and not rep.get("Associativity").passed

    # missing identity (multiplication of {2,4} mod 6 has identity 4, so use a constant table)
    t = [[1, 1], [1, 1]]
    rep = validate_table(t)
    assert not rep.is_group and not rep.get("Identity").passed

    # not closed
    rep = validate_table([[0, 1], [1, 2]])
    assert not rep.get("Closure").passed

    # identity exists but 0 has no inverse: {0..3} under multiplication mod 4... use mod 3
    t = [[(a * b) % 3 for b in range(3)] for a in range(3)]
    rep = validate_table(t)
    assert rep.get("Identity").passed and not rep.get("Inverses").passed

    # label that is not an element -> closure failure
    assert raises(ValueError, ge.from_table, "bad", ["e", "a"], [["e", "a"], ["a", "z"]])

    # ragged table
    assert not validate_table([[0, 1], [1]]).is_group


def test_size_limits():
    assert raises(GroupTooLargeError, ge.symmetric, 7)
    assert raises(GroupTooLargeError, ge.alternating, 7)
    assert raises(GroupTooLargeError, ge.direct_product, ge.cyclic(30), ge.cyclic(30))
    assert any("Large group" in w for w in ge.symmetric(6).warnings)
    assert ge.alternating(5).warnings == []
    assert ge.symmetric(4).warnings == []


def test_parse_group_spec():
    assert ge.parse_group_spec("Z_2 x Z_6").order == 12
    assert ge.parse_group_spec("S_4").order == 24
    assert ge.parse_group_spec("D_4").order == 8
    assert raises(ValueError, ge.parse_group_spec, "Q_8")
    assert raises(ValueError, ge.parse_group_spec, "banana")
