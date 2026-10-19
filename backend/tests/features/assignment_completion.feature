@US-06 @US-07
Feature: Assign and complete tasks
  As a task owner
  I want to delegate tasks and mark them as completed
  So that work is shared and progress is visible

  Background:
    Given today is "2026-10-19"
    And a user "bob@example.com" exists
    And I am logged in as "alice@example.com"
    And I have a task titled "Prepare demo"

  # SPEC-004 R7
  Scenario: Assign a task to another user
    When I assign the task to "bob@example.com"
    Then the response status should be 200
    And the task should be assigned to "bob@example.com"
    And a "TaskAssigned" event should be published for "bob@example.com"

  # SPEC-004 R8
  Scenario: Create a task already assigned to someone
    When I create a task titled "Delegated" assigned to "bob@example.com"
    Then the response status should be 201
    And the task should be assigned to "bob@example.com"
    And a "TaskAssigned" event should be published for "bob@example.com"

  # SPEC-004 R3
  Scenario: Unassign a task
    Given the task is assigned to "bob@example.com"
    When I unassign the task
    Then the response status should be 200
    And the task should have no assignee

  # SPEC-004 R2
  @validation
  Scenario: Assigning to a user that does not exist
    When I assign the task to an unknown user
    Then the response status should be 422

  # SPEC-004 R2
  @validation
  Scenario: Assigning to a deactivated user
    Given the user "bob@example.com" is deactivated
    When I assign the task to "bob@example.com"
    Then the response status should be 422

  # SPEC-004 R1
  @authorization
  Scenario: Only the owner can reassign a task
    Given the task is assigned to "bob@example.com"
    And I am logged in as "bob@example.com"
    When I assign the task to "bob@example.com"
    Then the response status should be 403

  # SPEC-004 R4, R6
  Scenario: The owner completes a task
    When I complete the task
    Then the response status should be 200
    And the task should have status "completed"
    And the task should have a completion time

  # SPEC-004 R4, R7
  Scenario: The assignee completes a task
    Given the task is assigned to "bob@example.com"
    And I am logged in as "bob@example.com"
    When I complete the task
    Then the response status should be 200
    And the task should have status "completed"
    And a "TaskCompleted" event should be published

  # SPEC-004 R5
  @validation
  Scenario: A completed task cannot be completed again
    Given the task is completed
    When I complete the task
    Then the response status should be 409

  # SPEC-004 R4
  @authorization
  Scenario: A stranger cannot complete a task
    Given I am logged in as "mallory@example.com"
    When I complete the task
    Then the response status should be 404

  # SPEC-004 R5, SPEC-002 R5
  Scenario: Reopen a completed task
    Given the task is completed
    When I update the task with status "pending"
    Then the response status should be 200
    And the task should have status "pending"
    And the task should have no completion time
