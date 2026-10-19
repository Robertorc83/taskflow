# ADR-0001: FastAPI over Django REST Framework

**Status:** Accepted · **Date:** 2026-10-19

## Context
The exercise allows Django/DRF, Flask or FastAPI and requires Swagger docs, JWT, pagination and validation.

## Decision
Use **FastAPI**. OpenAPI/Swagger is generated from the type hints (no drf-yasg layer). Pydantic validates requests, async I/O suits a DB+Redis-bound API, and `Depends` gives us explicit dependency injection for wiring use cases.

## Consequences
+ Typed end to end; the OpenAPI schema can generate the frontend types.
+ No ORM coupling: SQLAlchemy stays an infrastructure detail.
− No admin site or batteries (auth, migrations); we add PyJWT, Argon2 and Alembic ourselves.
