# GenAI Usage Log

**Tool:** Claude Code (Claude Opus 5.5), run as a terminal agent in this repository, with one
parallel sub-agent for the frontend.

**Working agreement:** the AI writes code, and nothing is accepted until it is verified.
Verification means:
- tests run red first, then green;
- `mypy --strict`, ruff and import-linter pass;
- coverage is reviewed;
- the stack is run in Docker;
- a Playwright journey passes, and the UI is checked against screenshots.

Every correction below was **caught by one of those gates or by reviewing output, not assumed**.

---

## 1. Prompts used

### 1.1 Project rules: `CLAUDE.md`
The full exercise brief was pasted as context, followed by:
> Before writing any application code, create a `CLAUDE.md` that sets the engineering standards
> for this project, written as a staff engineer would for a team that has to maintain it in
> production. Cover:
> - **Architecture:** Clean Architecture. Dependencies point inward: presentation and
>   infrastructure depend on the application layer, which depends only on the domain, and the
>   domain imports nothing but the standard library. Ports are defined in the application layer,
>   and the boundaries are enforced in CI rather than by convention.
> - **Workflow:** BDD. Each user story gets a Gherkin feature file, and outside-in TDD drives
>   the code beneath it.
> - **Domain:** the model, its invariants, and where each rule lives (entity, use case or schema).
> - **Conventions:** API design, error format, testing layers, code quality gates and a
>   Definition of Done.
> - **GenAI:** every significant AI-generated change is logged in `docs/ai-usage.md`, with how
>   it was validated and corrected.
>
> Keep modules small and cohesive, and only adopt practices you can justify in one sentence to a
> review panel. I'll review the file before implementation starts.

The output was `CLAUDE.md`. It covers layering and the dependency rule, the domain model, the BDD
workflow, API conventions, the Definition of Done, and the rule that every AI change gets logged
here. It acts as a **standing system prompt**: every later AI action is constrained by it.

### 1.2 Specs first, then implementation
> Approved. Work spec-first:
> 1. Write numbered specs under `specs/` (`SPEC-000..008`), each with its rules (R1..Rn), API
>    contracts and acceptance criteria. Add a change-request process so that every later fix or
>    behavior change is recorded against a spec before the code changes.
> 2. Write the `.feature` files **before any production code**.
> 3. Build outside-in: acceptance harness first (red), then domain and use-case unit tests, then
>    the adapters.
> 4. Iterate until every quality gate passes (tests, coverage, `mypy --strict`, ruff,
>    import-linter). Report failures exactly as they appear; don't summarize them away.
>
> Where the brief leaves a product rule open, ask me rather than guess, and record the decision
> in the relevant spec.

### 1.3 Frontend sub-agent (runs in parallel, owns `frontend/` only)
A **constrained delegation prompt**: it sets the scope, the contract, the definition of done and
what to report back.
> Implement the frontend described in SPEC-007, following the API contract in SPEC-001..004
> exactly. The backend is being built in parallel, so treat the specs as the only source of
> truth.
> - **Scope:** work only inside `frontend/`, and don't run any git commands.
> - **Stack:** React 18.3.1, TypeScript in strict mode, TanStack Query 5, React Hook Form + Zod,
>   Tailwind 3, Vitest + MSW for tests and Playwright for E2E. Pin exact versions.
> - **Behavior:** keep filters and the page number in the URL. On a 401, refresh the token once
>   and share that single refresh across concurrent requests.
> - **Quality:** zero console warnings (StrictMode on, router future flags set, no `act()`
>   warnings). Name tests in Given/When/Then form.
> - **Done when:** lint, typecheck, tests and the production build all pass.
>
> When you finish, **list every assumption you made about the API that the backend must honor**.

The last line mattered most. The report listed 10 contract assumptions (422 field names,
`Retry-After`, `size ≤ 100`, the default ordering, and so on). I checked each one against the
backend before integrating.

---

## 2. Representative output

The spec rule (SPEC-004 R4/R5) became a scenario:

```gherkin
Scenario: A completed task cannot be completed again
  Given the task is completed
  When I complete the task
  Then the response status should be 409
```

The invariant lives in the entity (`domain/entities/task.py`):

```python
def complete(self, *, completed_by: UUID, now: datetime) -> None:
    if self.status is TaskStatus.COMPLETED:
        raise TaskAlreadyCompletedError("Task is already completed")
    self.status = TaskStatus.COMPLETED
    self.completed_at = now
    self._touch(now)
    self._events.append(TaskCompleted(task_id=self.id, completed_by=completed_by))
```

Authorization and transaction live in the use case, and events are published **after** commit
(`application/use_cases/tasks.py`):

```python
class CompleteTask(_PublishingTaskUseCase):
    async def execute(self, actor_id: UUID, task_id: UUID) -> TaskDTO:
        async with self._uow as uow:
            task = await self._visible_task(uow, task_id, actor_id)  # 404 if not owner/assignee
            task.complete(completed_by=actor_id, now=self._clock.now())
            await uow.tasks.save(task)
            result = await self._to_dto(uow, task)
            await uow.commit()
        await self._publish_events_of(task)
        return result
```

The HTTP mapping (`TaskAlreadyCompletedError → 409`) is declared once, in `presentation/errors.py`.

---

## 3. How the AI's output was validated

| Gate | What it proves |
|------|----------------|
| Feature files written first, run **red** | The tests can fail, and they fail for the right reason |
| 71 Gherkin scenario runs (incl. outline examples) against real HTTP + real Postgres | Behavior matches the spec |
| Unit tests with hand-written fakes | Domain invariants and authorization, in milliseconds |
| `mypy --strict` on src **and** tests | Type-level correctness of ports and adapters |
| import-linter contracts | Clean Architecture holds (no framework in domain/application) |
| `filterwarnings = error` | Deprecated APIs surface immediately |
| Coverage report **read**, not just thresholded | Uncovered lines show untested paths, or untested assumptions |
| `docker compose up` + curl smoke + worker logs | Wiring, migrations, seed, Celery via Redis all work |
| Playwright (desktop + mobile) with a console-error assertion | Full user journey; no browser warnings |
| Screenshots reviewed by eye | Things tests don't catch: layout and alignment |

---

## 4. What was wrong and how it was corrected

Each of these was a real defect in AI-generated code or tests, found during this session.

| # | Problem | Caught by | Fix |
|---|---------|-----------|-----|
| 1 | The feature examples meant to test "whitespace-only" names came out as **duplicate empty rows**, because Gherkin trims table cells | Reviewing the generated `.feature` | Explicit scenarios ("a whitespace-only title") |
| 2 | `Task._events` was an `init=True` dataclass field, so `dataclasses.replace()` copies **shared one event list** | Self-review of the entity | `field(init=False)` |
| 3 | `MAX_SIZE: Final = 100` inside a `slots=True` dataclass becomes an *instance field* | Self-review | `ClassVar[int]` |
| 4 | `HTTPStatus.UNPROCESSABLE_CONTENT` only exists from Python **3.13**; the project targets 3.12 | First test run (AttributeError) | `UNPROCESSABLE_ENTITY` |
| 5 | Deprecated imports: `testcontainers.postgres`, Alembic `path_separator`, Starlette TestClient with `httpx` | `filterwarnings = error` | New import paths. **`httpx2` was adopted only after checking its PyPI provenance** (Pydantic org, Tom Christie), not because the warning suggested it |
| 6 | Coverage marked lines after `await` as missed (e.g. `login`'s return), even though they ran | Reading the coverage report | SQLAlchemy async uses greenlets: `concurrency = ["greenlet", "thread"]` |
| 7 | **The broker-outage scenario passed, but each request hung ~6 s.** redis-py retries the connection inside kombu | Test timing + coverage gap on the `except` branch | **CR-001**: new rule SPEC-005 R7, scenario updated (red at 6.1 s), `asyncio.wait_for` bound, green |
| 8 | Adding a user and their tasks in **one transaction violated the FK**: without ORM relationships, SQLAlchemy didn't order the inserts. API flows never hit it | Seed integration test | `relationship(..., lazy="raise")` declares the dependency without allowing implicit lazy loads |
| 9 | `UnitOfWork` Protocol declared repositories as mutable attributes (invariant), so the concrete UoWs didn't conform | mypy strict | Read-only `@property` members |
| 10 | Celery options passed as `**dict` defeated its typed overloads; SQLAlchemy 2.1 changed `Select[...]` generics | mypy strict | Explicit kwargs; `Select[M]` |
| 11 | `assert` used for control flow in production code (stripped under `-O`) | ruff `S101` | Explicit guard (`_active_session()`), typed exception handlers |
| 12 | A clumsy type-alias workaround in the repository module | Self-review | Plain `Callable[[M], E]` |
| 13 | Playwright created the task **twice**: desktop and mobile run in parallel and built the same `Date.now()` title | Inspecting the DB rows + API logs (the app was fine) | Title includes the project name |
| 14 | Mobile "New task" button wrapped onto two lines; filter labels misaligned (date inputs are taller) | Screenshot review | `whitespace-nowrap`, uniform `h-10` controls |

**Pattern:** most AI mistakes were **version drift**: APIs newer or older than the model's
defaults (Python 3.12 vs 3.13, SQLAlchemy 2.1, pytest-bdd 9, Starlette 1.x). The fix was
procedural: read the installed library's source before using it (as was done for pytest-bdd's
`fullmatch` and the `limits` async API), and treat warnings as errors.

---

## 5. Edge cases, auth and validation (deliberately covered)

- **User enumeration:** unknown email and wrong password return the same 401, and the unknown-email
  path still hashes, so timing doesn't reveal accounts.
- **Existence leaks:** a task you can't see returns 404, not 403. 403 is only for a visible task
  you can't modify.
- **Tokens:**
  - a refresh token can't be used as an access token, or the other way round (`type` claim);
  - tampered tokens are rejected;
  - deactivated users lose access on their next request;
  - production refuses to start with a weak JWT secret.
- **PATCH semantics:**
  - omitted fields are left alone and `null` clears them (`UNSET` sentinel);
  - re-sending an overdue task's unchanged due date is allowed;
  - moving a due date into the past is rejected.
- **Filters:**
  - an inverted date range gives 422;
  - an unknown status or ordering gives 422;
  - `size > 100` gives 422;
  - a page past the end gives an empty list;
  - tasks with no due date never match a date filter and sort last.
- **Concurrency:** a duplicate-email race is caught by the unique index and mapped to 409.
- **Notifications:**
  - no self-notifications;
  - jobs reload state, so a task deleted in the meantime makes the job a no-op;
  - a broker outage is bounded and logged.
- **Database-level invariant:** `CHECK ((status = 'completed') = (completed_at IS NOT NULL))`.

---

## 6. Assessing performance and idiomatic quality

**Performance**
- **List queries:** each page is one `COUNT` plus one `SELECT … LIMIT/OFFSET`. Composite indexes
  match the filters (`owner_id, status`, `assignee_id, status`, `due_date`).
- **No N+1:** owner and assignee summaries are batch-loaded with a single `IN` query per page.
- **Event loop:**
  - Argon2 runs only on login and register;
  - publishing to the broker happens on a worker thread with a time bound;
  - Celery jobs use unpooled engines, which suits their short-lived loops.
- **Known limits (written up in the ADRs):** offset pagination on deep pages, no outbox, and tokens
  stored in `localStorage`.

**Idiomatic quality**
- Modern Python 3.12: `typing.Protocol` ports, PEP 695 generics (`Page[T]`), `StrEnum`, frozen
  slotted dataclasses for DTOs, `match` on event types, `Self`.
- No framework types cross into the inner layers, and the import contracts enforce that.
- Tests read as specifications: Gherkin for behavior, and Given/When/Then structure in unit tests.

**What I would not take from the AI without review:** dependency choices (provenance), anything
touching auth, and any "it passes" claim without reading timing and coverage. Item 7 above passed
its test and was still wrong.

---

## 7. Second pass: multi-agent review

**Prompt:**
> Run an independent review of the whole repository before submission. Launch four read-only
> sub-agents in parallel, one per dimension: Clean Architecture, security, modularity and bugs.
> None of them may modify code. For each finding, report:
> - severity, `file:line`, a concrete failure scenario and a proposed fix;
> - **CONFIRMED** (reproduced, with the evidence: a request, a test or a log) or **PLAUSIBLE**
>   (from reading the code only);
> - whether it is a real defect or a trade-off already documented in an ADR or spec.
>
> Also list what you checked and found sound, so the coverage of the review is visible. I'll
> decide which findings become change requests.

Separating real defects from documented trade-offs kept the noise down, and the "checked and
found sound" lists showed what each agent actually covered.

**How the output was handled:**
1. **Reproduce before fixing.** I re-ran the rate-limit bypass and the reopen 403 myself. Two
   findings were reported by two agents independently, which raised confidence in them.
2. **Separate decisions from defects.** The reopen permission and the meaning of "today" were
   *product decisions* the specs left open or contradicted. Those went to the user, not into a
   silent fix.
3. **Red, then green, through CRs (CR-002 to CR-009).** New scenarios and tests were written first
   and observed failing: 7 BDD scenarios, the race test (8 out of 8 completes succeeded),
   password-rule tests and publisher tests.
4. **Verify live.** Spoofed-XFF loops through nginx and directly on :8000, the fail-closed image
   started with no env, 6 parallel completes, and Playwright.

**What the review itself missed, and the fixing exposed.** While making a weak test honest (the
outage scenario now asserts the failure is *logged*), the full run failed while the isolated run
passed. Debugging showed Celery reusing a cached producer connection to the developer's **real
local Redis**: 13 leaked test jobs. The fix is architectural (send jobs by name from an API-owned
producer app, `memory://` broker in tests), not a patch to the test.

| # | Finding (source) | Fix |
|---|------------------|-----|
| 15 | Spoofed `X-Forwarded-For` bypassed the auth rate limit (security, bugs) | Trust only nginx's IP; nginx overwrites XFF (CR-002) |
| 16 | Dev JWT secret accepted; demo users seeded in every env (security) | Image defaults to production and fails closed; seed gated (CR-002) |
| 17 | Postgres published on 0.0.0.0 with default creds (security) | Loopback-only, non-default ports (CR-002) |
| 18 | Parallel completes all succeeded (bugs) | `SELECT … FOR UPDATE` in mutating use cases (CR-003) |
| 19 | Assignee Reopen always got 403; specs contradicted each other (architecture, bugs) | `POST /reopen` for owner or assignee (CR-004) |
| 20 | "Today": browser local time vs server UTC (architecture, bugs) | `X-Timezone` + `ZonedClock`, no domain change (CR-005) |
| 21 | Password rule only in Pydantic; seed violated it (architecture, modularity) | Enforced in `RegisterUser` (CR-006) |
| 22 | API imported worker code; Celery configured at import time (architecture, modularity) | Jobs by name; strict import-linter contract (CR-007) |
| 23 | Tests passing for the wrong reason (bugs) | Assert no job failed and the failure was logged; this exposed the Redis leak (CR-007) |
| 24 | Refresh failure always logged out; stale cache after a partial edit; empty last page (bugs) | CR-008 |
| 25 | Unit tests imported the whole stack (modularity) | Conftest split; verified with `-X importtime` (CR-009) |
