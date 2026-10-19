# ADR-0007: Celery + Redis for notifications; events published after commit

**Status:** Accepted · **Date:** 2026-10-19

## Context
Notifications are slow and failure-prone and must not affect API latency or correctness.

## Decision
Use cases emit domain events, published **after** commit by `CeleryEventPublisher` (on a thread, with a bounded wait — CR-001). Celery tasks are thin adapters running application use cases (`NotifyTaskAssigned/Completed`) that reload fresh state by ID and retry with backoff.

## Consequences
+ A rolled-back transaction never notifies; deleted tasks make jobs no-ops.
− An event can be lost if the broker is down after commit. **Future work:** transactional outbox (events table written in the same transaction + relay).
