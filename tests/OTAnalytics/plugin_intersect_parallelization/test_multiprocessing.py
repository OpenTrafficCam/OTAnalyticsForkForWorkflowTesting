from unittest.mock import Mock, patch

import pytest

from OTAnalytics.domain.event import Event
from OTAnalytics.domain.section import Section
from OTAnalytics.domain.track import Track
from OTAnalytics.plugin_intersect_parallelization.multiprocessing import (
    MultiprocessingIntersectParallelization,
)


class TestMultiprocessingIntersectParallelization:
    @patch("OTAnalytics.plugin_intersect_parallelization.multiprocessing.Pool")
    def test_execute(self, mock_pool_init: Mock) -> None:
        event_1 = Mock(spec=Event)
        event_2 = Mock(spec=Event)
        sections = [Mock(spec=Section)]

        mock_pool_instance = mock_pool_init.return_value.__enter__.return_value
        mock_pool_instance.starmap.return_value = [[event_1], [event_2]]

        mock_intersect = Mock()
        tracks = [Mock(spec=Track), Mock(spec=Track)]

        intersect = MultiprocessingIntersectParallelization()
        result = intersect.execute(mock_intersect, tracks, sections)

        assert result == [event_1, event_2]
        mock_pool_instance.starmap.assert_called_once()

    def test_flatten_events(self) -> None:
        intersect = MultiprocessingIntersectParallelization()
        event_1 = Mock(spec=Event)
        event_2 = Mock(spec=Event)
        events_to_flatten = [[event_1], [event_2]]

        result = intersect._flatten_events(events_to_flatten)
        assert result == [event_1, event_2]

    def test_set_num_processes(self) -> None:
        intersect = MultiprocessingIntersectParallelization(4)
        assert intersect._num_processes == 4
        intersect.set_num_processes(2)
        assert intersect._num_processes == 2

    @pytest.mark.parametrize("num_processes", [-1, 0])
    def test_set_num_processes_invalid_args(self, num_processes: int) -> None:
        intersect = MultiprocessingIntersectParallelization(1)
        with pytest.raises(ValueError):
            intersect.set_num_processes(num_processes)

    @pytest.mark.parametrize("num_processes", [-1, 0])
    def test_set_init_invalid_args(self, num_processes: int) -> None:
        with pytest.raises(ValueError):
            MultiprocessingIntersectParallelization(num_processes)
