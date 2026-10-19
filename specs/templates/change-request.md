# CR-NNN: <short title>

| Field          | Value                                         |
|----------------|-----------------------------------------------|
| Date           | YYYY-MM-DD                                    |
| Type           | feature · bugfix · refactor · review-feedback · ai-correction |
| Specs affected | SPEC-NNN                                      |
| Status         | Proposed · Accepted · Implemented · Rejected  |

## Motivation

What happened / what is needed, and why. For bugs: observed vs. expected behavior and how to reproduce.

## Decision

The change we are making. For rejected CRs: why not.

## Behavior change (Gherkin)

```gherkin
# New or modified scenarios. Removed scenarios are listed with a reason.
```

## Implementation notes

Layers touched (domain / application / infrastructure / presentation / frontend), migrations, risks.

## Verification

- [ ] Scenario(s) failed before the change (red)
- [ ] Scenario(s) pass after the change (green)
- [ ] `make lint test` green, coverage did not drop
- [ ] Spec revision history updated
