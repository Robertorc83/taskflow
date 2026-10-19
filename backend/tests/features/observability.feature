@ops
Feature: Request tracing
  As someone operating or debugging the API
  I want every request to carry an ID that appears in the response and in every log line
  So that one user's problem can be traced end to end

  # SPEC-000 NFR-10 (CR-010)
  Scenario: Every response carries a request ID
    Given I am logged in as "alice@example.com"
    When I request my profile
    Then the response should have a request ID

  # SPEC-000 NFR-10 (CR-010)
  Scenario: A caller-supplied request ID is propagated
    Given I am logged in as "alice@example.com"
    When I request my profile with request ID "checkout-42"
    Then the response request ID should be "checkout-42"
    And the logs for this request should carry request ID "checkout-42"

  # SPEC-000 NFR-10 (CR-010): untrusted input must not be able to forge log lines
  Scenario: An unsafe request ID is replaced
    Given I am logged in as "alice@example.com"
    When I request my profile with request ID "x; level=ERROR msg=forged"
    Then the response request ID should not be "x; level=ERROR msg=forged"
    And the response should have a request ID

  # SPEC-000 cross-origin clients (CR-010)
  Scenario: Cross-origin clients may send the time zone and read the request ID
    When a browser on "http://localhost:5173" preflights a request with header "X-Timezone"
    Then the preflight should allow header "X-Timezone"
    And the request ID header should be exposed to the browser
