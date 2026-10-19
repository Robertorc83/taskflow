# CR-009: Test-suite modularity (no behavior change)

| Field          | Value |
|----------------|-------|
| Date           | 2026-10-19 |
| Type           | refactor |
| Specs affected | — |
| Status         | Implemented |
| Source         | Multi-agent review (architecture, security, modularity, bug hunt), findings reproduced before fixing |

## Motivation

- **Unit tests loaded the whole stack.** The root conftest registered every BDD step module, which
  imported FastAPI, SQLAlchemy and Celery. A broken `.env` could therefore fail pure domain tests.
- **Duplicated code:** the quoted-argument regex was copied into four step modules, and the
  pagination envelope was built twice in the routers.

## Decision

- **Root `conftest.py`:** database fixtures only, with lazy imports.
- **`tests/step_defs/conftest.py`:** owns the scenario world, the settings and every step.
- **Shared pieces:** `tests/step_defs/patterns.py` holds the regex; `PageResponse.from_page()`
  builds the envelope; `TaskListQuery` extends `PaginationQuery`; the wrong `__all__` export is
  fixed.

## Verification

- [x] `python -X importtime -m pytest tests/unit` imports **no** fastapi, sqlalchemy or celery
- [x] Same test count before and after the refactor
