from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from OTAnalytics.application.eventlist import SceneActionDetector, SectionActionDetector
from OTAnalytics.domain.event import (
    Event,
    EventType,
    SceneEventBuilder,
    SectionEventBuilder,
)
from OTAnalytics.domain.geometry import (
    Coordinate,
    DirectionVector2D,
    ImageCoordinate,
    RelativeOffsetCoordinate,
)
from OTAnalytics.domain.intersect import Intersector
from OTAnalytics.domain.section import LineSection
from OTAnalytics.domain.track import Detection, Track, TrackId


@pytest.fixture
def detection() -> Detection:
    return Detection(
        classification="car",
        confidence=0.5,
        x=0.0,
        y=5.0,
        w=15.3,
        h=30.5,
        frame=1,
        occurrence=datetime(2022, 1, 1, 0, 0, 0, 0),
        input_file_path=Path("path/to/myhostname_something.otdet"),
        interpolated_detection=False,
        track_id=TrackId(1),
    )


@pytest.fixture
def track() -> Track:
    track_id = TrackId(1)

    detection_1 = Detection(
        classification="car",
        confidence=0.5,
        x=0.0,
        y=5.0,
        w=15.3,
        h=30.5,
        frame=1,
        occurrence=datetime(2022, 1, 1, 0, 0, 0, 0),
        input_file_path=Path("path/to/myhostname_something.otdet"),
        interpolated_detection=False,
        track_id=TrackId(1),
    )
    detection_2 = Detection(
        classification="car",
        confidence=0.5,
        x=10.0,
        y=5.0,
        w=15.3,
        h=30.5,
        frame=2,
        occurrence=datetime(2022, 1, 1, 0, 0, 0, 1),
        input_file_path=Path("path/to/myhostname_something.otdet"),
        interpolated_detection=False,
        track_id=TrackId(1),
    )

    return Track(track_id, "car", [detection_1, detection_2])


@pytest.fixture
def line_section() -> LineSection:
    return LineSection(
        id="N",
        relative_offset_coordinates={
            EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
        },
        plugin_data={},
        start=Coordinate(5, 0),
        end=Coordinate(5, 10),
    )


class TestSectionActionDetector:
    def test_detect_enter(self, line_section: LineSection, track: Track) -> None:
        mock_intersector = Mock(spec=Intersector)
        mock_section_event_builder = Mock(spec=SectionEventBuilder)
        mock_event = Mock(spec=Event)

        mock_intersector.intersect.return_value = mock_event

        section_action_detector = SectionActionDetector(
            mock_intersector, mock_section_event_builder
        )
        result_event = section_action_detector._detect_enter(line_section, track)

        mock_section_event_builder.add_section_id.assert_called()
        mock_section_event_builder.add_event_type.assert_called()
        mock_section_event_builder.add_direction_vector.assert_called()
        mock_intersector.intersect.assert_called()
        assert mock_event == result_event

    def test_detect_enter_actions(
        self, line_section: LineSection, track: Track
    ) -> None:
        mock_intersector = Mock(spec=Intersector)
        mock_section_event_builder = Mock(spec=SectionEventBuilder)
        mock_event = Mock(spec=Event)

        mock_intersector.intersect.return_value = [mock_event]

        section_action_detector = SectionActionDetector(
            mock_intersector, mock_section_event_builder
        )

        result_events = section_action_detector.detect_enter_actions(
            [line_section], [track]
        )
        assert result_events == [mock_event]


class TestSceneActionDetector:
    def test_detect_enter_scene(self, track: Track) -> None:
        scene_event_builder = SceneEventBuilder()
        scene_event_builder.add_event_type(EventType.ENTER_SCENE)
        scene_event_builder.add_direction_vector(
            track.detections[0], track.detections[1]
        )
        scene_action_detector = SceneActionDetector(scene_event_builder)
        event = scene_action_detector.detect_enter_scene(track)
        assert event == Event(
            road_user_id=1,
            road_user_type="car",
            hostname="myhostname",
            occurrence=datetime(2022, 1, 1, 0, 0, 0, 0),
            frame_number=1,
            section_id=None,
            event_coordinate=ImageCoordinate(0.0, 5.0),
            event_type=EventType.ENTER_SCENE,
            direction_vector=DirectionVector2D(10, 0),
            video_name="myhostname_something.otdet",
        )

    def test_detect_leave_scene(self, track: Track) -> None:
        scene_event_builder = SceneEventBuilder()
        scene_event_builder.add_event_type(EventType.LEAVE_SCENE)
        scene_event_builder.add_direction_vector(
            track.detections[0], track.detections[1]
        )
        scene_action_detector = SceneActionDetector(scene_event_builder)
        event = scene_action_detector.detect_leave_scene(track)
        assert event == Event(
            road_user_id=1,
            road_user_type="car",
            hostname="myhostname",
            occurrence=datetime(2022, 1, 1, 0, 0, 0, 1),
            frame_number=2,
            section_id=None,
            event_coordinate=ImageCoordinate(10.0, 5.0),
            event_type=EventType.LEAVE_SCENE,
            direction_vector=DirectionVector2D(10, 0),
            video_name="myhostname_something.otdet",
        )