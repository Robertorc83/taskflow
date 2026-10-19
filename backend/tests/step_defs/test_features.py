"""Binds every Gherkin scenario in tests/features to the step definitions."""

from pytest_bdd import scenarios

scenarios(".")
