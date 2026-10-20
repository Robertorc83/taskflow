@ops
Feature: API documentation exposure
  As someone operating the API
  I want the interactive documentation published only where it is meant to be
  So that a production deployment does not hand out a map of every endpoint

  # SPEC-008 D9 (CR-012)
  Scenario: Documentation is published outside production
    When I open the API documentation
    Then the API documentation should be available

  # SPEC-008 D9 (CR-012): fail closed
  Scenario: Documentation is hidden in production
    Given the API runs in production
    When I open the API documentation
    Then the API documentation should not be found

  # SPEC-008 D9 (CR-012)
  Scenario: Production can publish the documentation explicitly
    Given the API runs in production with documentation enabled
    When I open the API documentation
    Then the API documentation should be available
