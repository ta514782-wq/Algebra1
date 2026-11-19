# AlgebraLab
Interactive abstract-algebra platform (Algebra II, Artifact 2: Cosets, Normal Subgroups & Quotient Group Visualizer).

## Status (honest progress log)
| Phase | Scope | State |
|---|---|---|
| 1 | Structure, database, group representation, validation, subgroup engine, tests | **Done, tested** |
| 2 | Cosets, Lagrange, normality, normalizer, centralizer, centre, quotient, classification, conjugacy | Not started |
| 3-7 | Notes, MCQ banks, auth, teacher panel, AI tutor, visualisations, Streamlit UI, deployment | Not started |

The Streamlit pages, `app.py`, notes, question banks and PDFs do not exist yet.

## Setup
    pip install -r requirements.txt
    python seed.py          # creates tables; admin only if env vars are set
    pytest

## Conventions
Permutations compose right-to-left. D_n has order 2n (D_4 has order 8). Z_n is additive.
Engine limits: order <= 720 (S_6); warning above 120.
