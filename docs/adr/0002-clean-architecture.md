# ADR-0002: Clean Architecture with ports & adapters, enforced by import-linter

**Status:** Accepted · **Date:** 2026-10-19

## Context
The panel evaluates separation of concerns and independence of components. Conventions alone erode, so a rule nobody checks is a rule that eventually breaks.

## Decision
Four layers (domain → application → infrastructure/presentation). Ports are `typing.Protocol`s in the application layer. **import-linter contracts** in `pyproject.toml` fail CI on a layer violation or when domain/application import a framework (FastAPI, Pydantic, SQLAlchemy, Celery, …).

## Consequences
+ The domain and use cases are unit-tested with in-memory fakes in milliseconds.
+ The API and the Celery worker are two composition roots over the same use cases.
− More files and explicit mapping (entity ↔ ORM row ↔ DTO ↔ schema) than a "fat model" design.
