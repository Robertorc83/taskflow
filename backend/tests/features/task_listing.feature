@US-03 @US-04
Feature: List, paginate and filter tasks
  As a user
  I want to list my tasks and filter them by status and due date
  So that I can focus on what matters now

  Background:
    Given today is "2026-10-19"
    And I am logged in as "alice@example.com"
    And I have the following tasks:
      | title          | status      | due_date   |
      | Write report   | pending     | 2026-11-01 |
      | Review PR      | in_progress | 2026-10-25 |
      | Deploy release | completed   | 2026-10-20 |
      | Plan sprint    | pending     |            |

  # SPEC-003 R1
  Scenario: List all my tasks
    When I list my tasks
    Then I should see 4 tasks
    And the total should be 4

  # SPEC-003 R3
  Scenario Outline: Filter by status
    When I list my tasks with status "<status>"
    Then I should see <count> tasks
    And every task should have status "<status>"

    Examples:
      | status      | count |
      | pending     | 2     |
      | in_progress | 1     |
      | completed   | 1     |

  # SPEC-003 R4
  Scenario: Filter by due date range
    When I list my tasks due between "2026-10-21" and "2026-10-31"
    Then I should see only "Review PR"

  # SPEC-003 R4
  Scenario: Filter by due date from
    When I list my tasks due from "2026-10-26"
    Then I should see only "Write report"

  # SPEC-003 R5
  Scenario: Combine status and due date filters
    When I list my tasks with status "pending" due until "2026-12-31"
    Then I should see only "Write report"

  # SPEC-003 R7
  Scenario: Order by due date
    When I list my tasks ordered by "due_date"
    Then the task titles should be in order "Deploy release, Review PR, Write report, Plan sprint"

  # SPEC-003 R6
  Scenario: Paginate results
    When I list my tasks with page 2 and size 3
    Then I should see 1 tasks
    And the total should be 4
    And there should be 2 pages

  # SPEC-003 R6
  Scenario: A page past the end is empty
    When I list my tasks with page 5 and size 3
    Then the response status should be 200
    And I should see 0 tasks

  # SPEC-003 R1
  Scenario: Tasks assigned to me are listed
    Given "bob@example.com" has a task titled "Bob's errand" assigned to me
    When I list my tasks
    Then I should see 5 tasks

  # SPEC-003 R2
  Scenario: Only tasks assigned to me
    Given "bob@example.com" has a task titled "Bob's errand" assigned to me
    When I list tasks with scope "assigned"
    Then I should see only "Bob's errand"

  # SPEC-003 R2
  Scenario: Only tasks I own
    Given "bob@example.com" has a task titled "Bob's errand" assigned to me
    When I list tasks with scope "owned"
    Then I should see 4 tasks

  # SPEC-003 R1
  Scenario: Other users' tasks are never listed
    Given "bob@example.com" has a task titled "Bob's secret"
    When I list my tasks
    Then I should see 4 tasks

  # SPEC-003 R3
  @validation
  Scenario: Reject an invalid status filter
    When I list my tasks with status "archived"
    Then the response status should be 422

  # SPEC-003 R4
  @validation
  Scenario: Reject an inverted date range
    When I list my tasks due between "2026-11-30" and "2026-11-01"
    Then the response status should be 422

  # SPEC-003 R6
  @validation
  Scenario: Reject a page size above the maximum
    When I list my tasks with page 1 and size 101
    Then the response status should be 422
