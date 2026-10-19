from datetime import date

import pytest

from taskmanager.application.dto import Page, PageRequest, TaskFilters
from taskmanager.application.exceptions import InvalidInputError


@pytest.mark.parametrize(("page", "size"), [(0, 20), (1, 0), (1, 101)])
def test_page_request_bounds(page: int, size: int) -> None:
    with pytest.raises(InvalidInputError):
        PageRequest(page=page, size=size)


def test_page_request_offset() -> None:
    assert PageRequest(page=3, size=10).offset == 20


@pytest.mark.parametrize(("total", "pages"), [(0, 0), (1, 1), (20, 1), (21, 2)])
def test_page_count(total: int, pages: int) -> None:
    assert Page(items=[], total=total, page=1, size=20).pages == pages


def test_filters_reject_an_inverted_date_range() -> None:
    with pytest.raises(InvalidInputError):
        TaskFilters(due_from=date(2026, 11, 30), due_to=date(2026, 11, 1))


def test_filters_accept_a_single_day_range() -> None:
    day = date(2026, 11, 1)
    assert TaskFilters(due_from=day, due_to=day).due_from == day
