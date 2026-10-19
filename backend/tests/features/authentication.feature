@US-01 @auth
Feature: Registration and authentication
  As a visitor
  I want to register and log in
  So that I get a token to use the API

  # SPEC-001 R1, R2
  Scenario: Register a new account
    When I register with email "Carol@Example.com", name "Carol Diaz" and password "Secret123!"
    Then the response status should be 201
    And the response should contain the email "carol@example.com"
    And the response should not expose the password

  # SPEC-001 R1
  @validation
  Scenario: Registering with an email that is already taken
    Given a user "alice@example.com" exists with password "Alice123!"
    When I register with email "ALICE@example.com", name "Alice Again" and password "Secret123!"
    Then the response status should be 409

  # SPEC-001 R2, R3
  @validation
  Scenario Outline: Registration input is validated
    When I register with email "<email>", name "<name>" and password "<password>"
    Then the response status should be 422

    Examples:
      | email             | name  | password   |
      | not-an-email      | Carol | Secret123! |
      | carol@example.com | Carol | short      |
      | carol@example.com |       | Secret123! |

  # SPEC-001 R4
  Scenario: Log in with valid credentials
    Given a user "alice@example.com" exists with password "Alice123!"
    When I log in as "alice@example.com" with password "Alice123!"
    Then the response status should be 200
    And I should receive an access token and a refresh token

  # SPEC-001 R4
  Scenario: Log in with a wrong password
    Given a user "alice@example.com" exists with password "Alice123!"
    When I log in as "alice@example.com" with password "wrong-password"
    Then the response status should be 401

  # SPEC-001 R4
  Scenario: Log in with an unknown email
    When I log in as "ghost@example.com" with password "Whatever123!"
    Then the response status should be 401

  # SPEC-001 R5
  Scenario: An inactive user cannot log in
    Given a user "alice@example.com" exists with password "Alice123!"
    And the user "alice@example.com" is deactivated
    When I log in as "alice@example.com" with password "Alice123!"
    Then the response status should be 401

  Scenario: Access my profile with a valid token
    Given I am logged in as "alice@example.com"
    When I request my profile
    Then the response status should be 200
    And the response should contain the email "alice@example.com"

  # SPEC-001 R5
  Scenario: A deactivated user's token stops working
    Given I am logged in as "alice@example.com"
    And the user "alice@example.com" is deactivated
    When I request my profile
    Then the response status should be 401

  # SPEC-001 R7
  Scenario: Protected endpoints reject missing tokens
    When I request my profile without a token
    Then the response status should be 401

  # SPEC-001 R7
  Scenario: Protected endpoints reject a tampered token
    When I request my profile with the token "not.a.jwt"
    Then the response status should be 401

  # SPEC-001 R6
  Scenario: Refresh an access token
    Given I am logged in as "alice@example.com"
    When I refresh my tokens
    Then the response status should be 200
    And I should receive an access token and a refresh token

  # SPEC-001 R6
  Scenario: An access token cannot be used as a refresh token
    Given I am logged in as "alice@example.com"
    When I try to refresh using my access token
    Then the response status should be 401

  Scenario: List users for the assignee picker
    Given a user "bob@example.com" exists
    And I am logged in as "alice@example.com"
    When I list the users
    Then the response status should be 200
    And the user list should include "bob@example.com"
