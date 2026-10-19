# CR-005: "Today" follows the user's time zone

| Field          | Value |
|----------------|-------|
| Date           | 2026-10-19 |
| Type           | bugfix / spec gap |
| Specs affected | SPEC-000, SPEC-002 |
| Status         | Implemented |
| Source         | Multi-agent review (architecture, security, modularity, bug hunt), findings reproduced before fixing |

## Motivation

- The frontend computed "today" in the browser's local zone; the backend used the UTC date.
- After 8 pm in New York, the form accepted today's date, but the API rejected it as past (a 422
  with no field). Tasks due "today" also showed as overdue.
- No spec defined what "today" means.

## Decision (taken with the user)

- **No new library.** The backend uses stdlib `zoneinfo`; the frontend uses `Intl`.
- The client sends `X-Timezone: <IANA zone>` on every request.
- The `request_clock` dependency wraps the application clock in a `ZonedClock`: the same instant,
  expressed in that zone. The domain still derives "today" from `now().date()`, so **no domain
  change was needed**.
- A missing header means UTC. An unknown zone gives `422` with field `X-Timezone`.
- Responses always serialize timestamps in UTC (`UtcDateTime`).

## Behavior change (Gherkin)

```gherkin
  Scenario: "Today" is the user's local date                (2026-10-20T02:00Z, America/New_York → due 2026-10-19 accepted, not overdue)
  Scenario: Without a time zone, "today" is the UTC date     (same instant, no header → 422)
  Scenario: An unknown time zone is rejected                 (422, error on X-Timezone)
```

## Verification

- [x] Red, then green
- [x] Frontend `http.test.ts` checks the header is sent, and left out when no zone resolves
