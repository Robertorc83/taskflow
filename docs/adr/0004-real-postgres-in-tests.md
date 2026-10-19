# ADR-0004: Real PostgreSQL in tests (testcontainers), migrated with Alembic

**Status:** Accepted · **Date:** 2026-10-19

## Context
SQLite differs from Postgres in date handling, `NULLS LAST`, CHECK constraints and concurrency. Testing on a different engine than production hides bugs.

## Decision
Acceptance and integration tests run against `postgres:16-alpine` started by testcontainers (or `TEST_DATABASE_URL` in CI). The schema is created by **running the Alembic migrations**, and a test asserts the migrations match the models (`compare_metadata`).

## Consequences
+ Migrations themselves are tested; schema drift fails CI.
+ Found a real bug: without ORM relationships, SQLAlchemy didn't order user/task inserts by FK.
− Needs Docker locally; ~3 s container start-up per test session.
