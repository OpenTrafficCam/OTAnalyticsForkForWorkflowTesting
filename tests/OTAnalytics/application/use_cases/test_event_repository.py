from unittest.mock import Mock

import pytest

from OTAnalytics.application.use_cases.event_repository import AddEvents, ClearAllEvents
from OTAnalytics.domain.event import Event, EventRepository


@pytest.fixture
def events() -> list[Mock]:
    return [Mock(spec=Event), Mock(spec=Event)]


@pytest.fixture
def event_repository() -> Mock:
    return Mock(spec=EventRepository)


class TestAddEvents:
    def test_add(self, event_repository: Mock, events: list[Event]) -> None:
        add_events = AddEvents(event_repository)
        add_events(events)
        event_repository.add_all.assert_called_once_with(events)


class TestClearAllEvents:
    def test_clear(self) -> None:
        repository = Mock(spec=EventRepository)
        clear_all_events = ClearAllEvents(repository)
        clear_all_events()
        repository.clear.assert_called_once()
