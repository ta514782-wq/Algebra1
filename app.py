"""AlgebraLab - Phase 1 demo: Group Explorer + subgroup tester."""
import pandas as pd
import streamlit as st

import group_engine as ge
import subgroup_engine as se
from group_validation import validate_table

st.set_page_config(page_title="AlgebraLab", page_icon="∑", layout="wide")
st.title("AlgebraLab")
st.caption("Learn. Visualize. Calculate. Practise. Master.  |  Phase 1: Group Explorer")

st.sidebar.header("Choose a group")
mode = st.sidebar.radio("Input", ["Standard group", "Type a group", "Multiplication table"])

G = None
try:
    if mode == "Standard group":
        fam = st.sidebar.selectbox("Family", ["Z_n (cyclic)", "S_n (symmetric)", "A_n (alternating)", "D_n (dihedral, order 2n)"])
        n = st.sidebar.number_input("n", min_value=1, max_value=12, value=4, step=1)
        n = int(n)
        G = {"Z": ge.cyclic, "S": ge.symmetric, "A": ge.alternating, "D": ge.dihedral}[fam[0]](n)
    elif mode == "Type a group":
        spec = st.sidebar.text_input("e.g. Z_2 x Z_6, S_4, A_4, D_4", "D_4")
        G = ge.parse_group_spec(spec)
    else:
        labels = st.sidebar.text_input("Elements (comma separated)", "e, a, b, c")
        rows = st.sidebar.text_area("Table rows (one row per line, comma separated)",
                                    "e, a, b, c\na, e, c, b\nb, c, e, a\nc, b, a, e")
        lab = [x.strip() for x in labels.split(",") if x.strip()]
        tab = [[x.strip() for x in r.split(",")] for r in rows.strip().splitlines()]
        G = ge.from_table("User group", lab, tab)
except ge.InvalidGroupError as exc:
    st.error("This is NOT a group.")
    st.code(str(exc.report.explain()))
except (ValueError, KeyError) as exc:
    st.error(str(exc))

if G is not None:
    for w in G.warnings:
        st.warning(w)
    c1, c2, c3 = st.columns(3)
    c1.metric("Group", G.name)
    c2.metric("Order |G|", G.order)
    c3.metric("Abelian", "Yes" if G.is_abelian() else "No")
    if G.description:
        st.write(G.description)

    with st.expander("Group axioms (verified)", expanded=False):
        st.code(validate_table(G.table, G.labels).explain())

    st.subheader("Elements and orders")
    st.dataframe(pd.DataFrame({
        "Element": G.labels,
        "Inverse": [G.label(G.inv(a)) for a in G.elements],
        "Order": [G.element_order(a) for a in G.elements]}), hide_index=True, use_container_width=True)

    if G.order <= 24:
        st.subheader("Cayley table")
        st.dataframe(pd.DataFrame([[G.labels[G.mul(a, b)] for b in G.elements] for a in G.elements],
                                  index=G.labels, columns=G.labels), use_container_width=True)

    st.subheader("Subgroup tester")
    chosen = st.multiselect("Pick elements for a subset H", G.labels)
    if chosen:
        H = [G.index(x) for x in chosen]
        rep = se.check_subgroup(G, H)
        (st.success if rep.is_subgroup else st.error)(
            "H is a subgroup of G." if rep.is_subgroup else "H is NOT a subgroup of G.")
        st.code(rep.explain())
        if rep.is_subgroup:
            st.write(f"|H| = {len(H)} divides |G| = {G.order}; index [G:H] = {G.order // len(H)}.")

    st.subheader("All subgroups")
    if st.button("Find all subgroups"):
        with st.spinner("Searching..."):
            res = se.all_subgroups(G, max_seconds=8)
        (st.info if res.exhaustive else st.warning)(res.note)
        st.dataframe(pd.DataFrame({
            "Order": [len(s) for s in res.subgroups],
            "Elements": [", ".join(G.labels_of(s)) for s in res.subgroups]}), hide_index=True, use_container_width=True)
