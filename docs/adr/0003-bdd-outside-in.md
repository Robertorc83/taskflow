# ADR-0003: BDD with pytest-bdd, outside-in TDD

**Status:** Accepted · **Date:** 2026-10-19

## Context
We want requirements that are readable by non-developers and executable, and a design driven by behavior rather than by tables.

## Decision
Each spec has a `.feature` file. Step definitions call the **real HTTP API**. Inside that loop, domain and use-case behavior is driven by unit tests. Test doubles are hand-written fakes (`tests/fakes.py`), not mocks.

## Consequences
+ Specs, tests and code can't drift: a spec change starts as a red scenario (see CR-001).
+ Fakes keep unit tests behavioral and refactor-friendly.
− Gherkin adds a layer of indirection; we keep steps reusable and regex-anchored (`fullmatch`, quoted args) to avoid ambiguous matches.
