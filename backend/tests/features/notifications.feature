@US-08
Feature: Asynchronous notifications
  As someone involved in a task
  I want to be notified when it is delegated to me or finished
  So that I stay informed without polling

  Background:
    Given today is "2026-10-19"
    And background jobs run immediately
    And a user "bob@example.com" exists
    And I am logged in as "alice@example.com"
    And I have a task titled "Prepare demo"

  # SPEC-005 R1, R3
  Scenario: The assignee is notified when a task is assigned
    When I assign the task to "bob@example.com"
    Then "bob@example.com" should receive a notification mentioning "Prepare demo"

  # SPEC-005 R1
  Scenario: Nobody is notified when I assign a task to myself
    When I assign the task to "alice@example.com"
    Then no notification should be sent

  # SPEC-005 R2, R3
  Scenario: The owner is notified when the assignee completes the task
    Given the task is assigned to "bob@example.com"
    And I am logged in as "bob@example.com"
    When I complete the task
    Then "alice@example.com" should receive a notification mentioning "Prepare demo"
    And "bob@example.com" should not receive a notification about completion

  # SPEC-005 R2
  Scenario: Nobody is notified when I complete my own unassigned task
    When I complete the task
    Then no notification should be sent

  # SPEC-005 R4, R7 (CR-001)
  Scenario: A broker outage does not fail the request
    Given the background job broker is unavailable
    When I assign the task to "bob@example.com"
    Then the response status should be 200
    And the response should arrive within 3 seconds
