@US-09
Feature: Rate limiting
  As the API operator
  I want clients to be throttled when they send too many requests
  So that the API is protected from abuse

  # SPEC-006 R1, R3
  Scenario: Too many login attempts are throttled
    Given a user "alice@example.com" exists with password "Alice123!"
    And the auth rate limit is 3 requests per minute
    When I attempt to log in as "alice@example.com" with password "wrong-password" 4 times
    Then the last response status should be 429
    And the response should tell me when to retry

  # SPEC-006 R1
  Scenario: Requests under the limit are not throttled
    Given a user "alice@example.com" exists with password "Alice123!"
    And the auth rate limit is 3 requests per minute
    When I attempt to log in as "alice@example.com" with password "wrong-password" 3 times
    Then every response status should be 401

  # SPEC-006 R2, R3
  Scenario: Authenticated API usage is limited per user
    Given I am logged in as "alice@example.com"
    And the API rate limit is 5 requests per minute
    When I list my tasks 6 times
    Then the last response status should be 429

  # SPEC-006 R2
  Scenario: Limits are tracked per user
    Given I am logged in as "bob@example.com"
    And I am logged in as "alice@example.com"
    And the API rate limit is 5 requests per minute
    And I have listed my tasks 5 times
    When "bob@example.com" lists their tasks
    Then the response status should be 200
