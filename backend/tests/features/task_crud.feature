@US-02 @US-05
Feature: Manage tasks
  As a user
  I want to create, view, update and delete my tasks
  So that I can keep track of my work

  Background:
    Given today is "2026-10-19"
    And I am logged in as "alice@example.com"

  # SPEC-002 R1
  Scenario: Create a task
    When I create a task titled "Write report" due on "2026-11-01"
    Then the response status should be 201
    And the task should have status "pending"
    And I should be the owner of the task
    And the task should not be overdue

  # SPEC-002 R1
  Scenario: Create a task with only a title
    When I create a task titled "Buy milk"
    Then the response status should be 201
    And the task should have no due date

  # SPEC-002 R2
  @validation
  Scenario: A task title is required
    When I create a task titled ""
    Then the response status should be 422

  # SPEC-002 R2
  @validation
  Scenario: A blank task title is rejected
    When I create a task with a whitespace-only title
    Then the response status should be 422

  # SPEC-002 R2
  @validation
  Scenario: A title longer than 200 characters is rejected
    When I create a task with a title of 201 characters
    Then the response status should be 422

  # SPEC-002 R3
  @validation
  Scenario: A task cannot be created with a due date in the past
    When I create a task titled "Time travel" due on "2026-10-18"
    Then the response status should be 422

  # SPEC-002 R3
  @validation
  Scenario: A due date cannot be moved into the past
    Given I have a task titled "Write report" due on "2026-11-01"
    When I change the task's due date to "2026-10-01"
    Then the response status should be 422

  Scenario: View a task I own
    Given I have a task titled "Write report"
    When I view the task
    Then the response status should be 200
    And the task title should be "Write report"

  # SPEC-002 R6
  Scenario: Update a task
    Given I have a task titled "Write report" due on "2026-11-01"
    When I update the task with title "Write final report" and status "in_progress"
    Then the response status should be 200
    And the task title should be "Write final report"
    And the task should have status "in_progress"
    And the task should be due on "2026-11-01"

  # SPEC-002 R6
  Scenario: Clear a task's due date
    Given I have a task titled "Write report" due on "2026-11-01"
    When I clear the task's due date
    Then the response status should be 200
    And the task should have no due date

  # SPEC-002 R5
  @validation
  Scenario: A task cannot be completed through an update
    Given I have a task titled "Write report"
    When I update the task with status "completed"
    Then the response status should be 422

  Scenario: Delete a task
    Given I have a task titled "Write report"
    When I delete the task
    Then the response status should be 204
    And the task should no longer exist

  Scenario: Requesting a task that does not exist
    When I view a task that does not exist
    Then the response status should be 404

  # SPEC-002 R4
  @authorization
  Scenario: Other users cannot see my tasks
    Given I have a task titled "Private plan"
    And I am logged in as "mallory@example.com"
    When I view the task
    Then the response status should be 404

  # SPEC-002 R4
  @authorization
  Scenario: Other users cannot update my tasks
    Given I have a task titled "Private plan"
    And I am logged in as "mallory@example.com"
    When I update the task with title "Hacked"
    Then the response status should be 404

  # SPEC-002 R4
  @authorization
  Scenario: Other users cannot delete my tasks
    Given I have a task titled "Private plan"
    And I am logged in as "mallory@example.com"
    When I delete the task
    Then the response status should be 404

  # SPEC-002 R4
  @authorization
  Scenario: An assignee can view a task
    Given I have a task titled "Shared work"
    And the task is assigned to "bob@example.com"
    And I am logged in as "bob@example.com"
    When I view the task
    Then the response status should be 200

  # SPEC-002 R4
  @authorization
  Scenario: An assignee cannot edit a task
    Given I have a task titled "Shared work"
    And the task is assigned to "bob@example.com"
    And I am logged in as "bob@example.com"
    When I update the task with title "Bob's work"
    Then the response status should be 403

  # SPEC-000 time zones, SPEC-002 R3, R8 (CR-005)
  Scenario: "Today" is the user's local date
    Given the current time is "2026-10-20T02:00:00Z"
    And my time zone is "America/New_York"
    When I create a task titled "Evening task" due on "2026-10-19"
    Then the response status should be 201
    And the task should not be overdue

  # SPEC-000 time zones (CR-005)
  Scenario: Without a time zone, "today" is the UTC date
    Given the current time is "2026-10-20T02:00:00Z"
    When I create a task titled "Evening task" due on "2026-10-19"
    Then the response status should be 422

  # SPEC-000 time zones (CR-005)
  @validation
  Scenario: An unknown time zone is rejected
    Given my time zone is "Mars/Olympus_Mons"
    When I create a task titled "Anything"
    Then the response status should be 422
    And the error should be about "X-Timezone"

  # SPEC-002 R6 (CR-006)
  @validation
  Scenario: The title cannot be cleared
    Given I have a task titled "Write report"
    When I update the task with a null title
    Then the response status should be 422
    And the error should be about "title"
