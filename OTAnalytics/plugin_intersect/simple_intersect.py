from functools import partial
from typing import Iterable

from OTAnalytics.application.analysis.intersect import (
    RunIntersect,
    TracksIntersectingSections,
)
from OTAnalytics.application.eventlist import SectionActionDetector
from OTAnalytics.application.geometry import (
    SectionGeometryBuilder,
    TrackGeometryBuilder,
)
from OTAnalytics.application.use_cases.track_repository import (
    GetTracksWithoutSingleDetections,
)
from OTAnalytics.domain.event import Event, EventBuilder, EventType, SectionEventBuilder
from OTAnalytics.domain.geometry import (
    Coordinate,
    Line,
    Polygon,
    RelativeOffsetCoordinate,
)
from OTAnalytics.domain.intersect import (
    AreaIntersector,
    IntersectImplementation,
    IntersectParallelizationStrategy,
    LineSectionIntersector,
)
from OTAnalytics.domain.section import Area, LineSection, Section
from OTAnalytics.domain.track import Track, TrackId


class SimpleIntersectBySmallestTrackSegments(LineSectionIntersector[Track]):
    """
    Implements the intersection strategy by splitting up the track in its smallest
    segments and intersecting each of them with the section.

    The smallest segment of a track is to generate a Line with the coordinates of
    two neighboring detections in the track.

    Args:
        implementation (IntersectorImplementation): the intersection implementation
        line (LineSection): the line to intersect with
    """

    def __init__(
        self, implementation: IntersectImplementation, line_section: LineSection
    ) -> None:
        super().__init__(implementation, line_section)

    def intersect(self, track: Track, event_builder: EventBuilder) -> list[Event]:
        events: list[Event] = []

        line_section_as_geometry = Line(self._line_section.get_coordinates())

        event_builder.add_road_user_type(track.classification)
        offset = self._line_section.get_offset(EventType.SECTION_ENTER)

        if not self._track_line_intersects_section(
            track, line_section_as_geometry, offset
        ):
            return events

        for current_detection, next_detection in zip(
            track.detections[0:-1], track.detections[1:]
        ):
            current_detection_coordinate = self._select_coordinate_in_detection(
                current_detection, offset
            )
            next_detection_coordinate = self._select_coordinate_in_detection(
                next_detection, offset
            )
            detection_as_geometry = Line(
                [current_detection_coordinate, next_detection_coordinate]
            )
            intersects = self.implementation.line_intersects_line(
                line_section_as_geometry, detection_as_geometry
            )
            if intersects:
                event_builder.add_direction_vector(
                    self._calculate_direction_vector(
                        current_detection_coordinate, next_detection_coordinate
                    )
                )
                event_builder.add_event_coordinate(
                    next_detection_coordinate.x, next_detection_coordinate.y
                )
                events.append(event_builder.create_event(next_detection))
        return events

    def _track_line_intersects_section(
        self, track: Track, line_section: Line, offset: RelativeOffsetCoordinate
    ) -> bool:
        """Whether a track line defined by all its detections intersects the section"""
        track_as_geometry = Line(
            [
                self._select_coordinate_in_detection(detection, offset)
                for detection in track.detections
            ]
        )
        return self.implementation.line_intersects_line(line_section, track_as_geometry)


class SimpleIntersectAreaByTrackPoints(AreaIntersector[Track]):
    def __init__(self, implementation: IntersectImplementation, area: Area) -> None:
        super().__init__(implementation, area)

    def intersect(self, track: Track, event_builder: EventBuilder) -> list[Event]:
        """Intersect area with a detection.

        Returns:
            bool: `True` if area intersects detection. Otherwise `False`.
        """
        area_as_polygon = Polygon(self._area.coordinates)
        offset = self._area.get_offset(EventType.SECTION_ENTER)

        track_coordinates: list[Coordinate] = [
            self._select_coordinate_in_detection(detection, offset)
            for detection in track.detections
        ]
        section_entered_mask = self.implementation.are_coordinates_within_polygon(
            track_coordinates, area_as_polygon
        )
        events: list[Event] = []

        event_builder.add_road_user_type(track.classification)
        track_starts_inside_area = section_entered_mask[0]

        if track_starts_inside_area:
            first_detection = track.detections[0]
            first_detection_coordinate = track_coordinates[0]
            second_detection_coordinate = track_coordinates[1]

            event_builder.add_event_type(EventType.SECTION_ENTER)
            event_builder.add_road_user_type(first_detection.classification)
            event_builder.add_direction_vector(
                self._calculate_direction_vector(
                    first_detection_coordinate, second_detection_coordinate
                )
            )
            event_builder.add_event_coordinate(
                first_detection_coordinate.x, first_detection_coordinate.y
            )
            event = event_builder.create_event(first_detection)
            events.append(event)

        section_currently_entered = track_starts_inside_area

        for current_index, current_detection in enumerate(
            track.detections[1:], start=1
        ):
            entered = section_entered_mask[current_index]
            if section_currently_entered == entered:
                continue
            current_detection_coordinate = track_coordinates[current_index]
            prev_detection_coordinate = track_coordinates[current_index - 1]

            event_builder.add_direction_vector(
                self._calculate_direction_vector(
                    prev_detection_coordinate, current_detection_coordinate
                )
            )

            current_coordinate = track_coordinates[current_index]
            event_builder.add_event_coordinate(
                current_coordinate.x, current_coordinate.y
            )

            if entered:
                event_builder.add_event_type(EventType.SECTION_ENTER)
            else:
                event_builder.add_event_type(EventType.SECTION_LEAVE)

            event = event_builder.create_event(current_detection)
            events.append(event)
            section_currently_entered = entered

        return events


class SimpleIntersectBySplittingTrackLine(LineSectionIntersector[Track]):
    """
    Implements the intersection strategy by splitting a track with the section.

    Args:
        implementation (IntersectorImplementation): the intersection implementation
        line (LineSection): the line to intersect with
    """

    def __init__(
        self, implementation: IntersectImplementation, line_section: LineSection
    ) -> None:
        super().__init__(implementation, line_section)

    def intersect(self, track: Track, event_builder: EventBuilder) -> list[Event]:
        line_section_as_geometry = Line(self._line_section.get_coordinates())
        if event_builder.event_type is None:
            raise ValueError("Event type not set in section builder")

        offset = self._line_section.relative_offset_coordinates[
            event_builder.event_type
        ]

        track_as_geometry = Line(
            [
                self._select_coordinate_in_detection(detection, offset)
                for detection in track.detections
            ]
        )

        splitted_lines = self.implementation.split_line_with_line(
            track_as_geometry, line_section_as_geometry
        )
        event_builder.add_road_user_type(track.classification)

        events: list[Event] = []

        if splitted_lines:
            current_idx = len(splitted_lines[0].coordinates)
            for n, splitted_line in enumerate(splitted_lines[1:], start=1):
                # Subtract by 2n to account for intersection points
                detection_index = current_idx - 2 * n + 1
                selected_detection = track.detections[detection_index]

                selected_detection_coordinate = track_as_geometry.coordinates[
                    detection_index
                ]
                previous_detection_coordinate = track_as_geometry.coordinates[
                    detection_index - 1
                ]
                event_builder.add_direction_vector(
                    self._calculate_direction_vector(
                        previous_detection_coordinate, selected_detection_coordinate
                    )
                )

                selected_detection_coordinate = track_as_geometry.coordinates[
                    detection_index
                ]
                event_builder.add_event_coordinate(
                    selected_detection_coordinate.x, selected_detection_coordinate.y
                )

                events.append(event_builder.create_event(selected_detection))
                current_idx += len(splitted_line.coordinates)
        return events


class SimpleRunIntersect(RunIntersect):
    """
    This class defines the use case to intersect the given tracks with the given
    sections
    """

    def __init__(
        self,
        intersect_implementation: IntersectImplementation,
        intersect_parallelizer: IntersectParallelizationStrategy,
        get_tracks: GetTracksWithoutSingleDetections,
    ) -> None:
        self._intersect_implementation = intersect_implementation
        self._intersect_parallelizer = intersect_parallelizer
        self._get_tracks = get_tracks

    def __call__(self, sections: Iterable[Section]) -> list[Event]:
        return self._intersect_parallelizer.execute(
            partial(
                _run_intersect_on_single_track,
                intersect_implementation=self._intersect_implementation,
            ),
            self._get_tracks(),
            sections,
        )


def _run_intersect_on_single_track(
    track: Track,
    sections: Iterable[Section],
    intersect_implementation: IntersectImplementation,
) -> list[Event]:
    events: list[Event] = []
    for _section in sections:
        if isinstance(_section, LineSection):
            line_section_intersector = SimpleIntersectBySmallestTrackSegments(
                implementation=intersect_implementation,
                line_section=_section,
            )
            section_event_builder = SectionEventBuilder()
            section_action_detector = SectionActionDetector(
                intersector=line_section_intersector,
                section_event_builder=section_event_builder,
            )
        if isinstance(_section, Area):
            area_section_intersector = SimpleIntersectAreaByTrackPoints(
                implementation=intersect_implementation,
                area=_section,
            )
            section_event_builder = SectionEventBuilder()
            section_action_detector = SectionActionDetector(
                intersector=area_section_intersector,
                section_event_builder=section_event_builder,
            )
        events.extend(section_action_detector._detect(section=_section, track=track))
    return events


class SimpleTracksIntersectingSections(TracksIntersectingSections):
    def __init__(
        self,
        get_tracks: GetTracksWithoutSingleDetections,
        intersect_implementation: IntersectImplementation,
        track_geometry_builder: TrackGeometryBuilder = TrackGeometryBuilder(),
        section_geometry_builder: SectionGeometryBuilder = SectionGeometryBuilder(),
    ):
        self._get_tracks = get_tracks
        self._intersect_implementation = intersect_implementation
        self._track_geometry_builder = track_geometry_builder
        self._section_geometry_builder = section_geometry_builder

    def __call__(self, sections: Iterable[Section]) -> set[TrackId]:
        tracks = self._get_tracks()
        return self._intersect(tracks, sections)

    def _intersect(
        self, tracks: Iterable[Track], sections: Iterable[Section]
    ) -> set[TrackId]:
        print("Number of intersecting tracks per section")
        all_track_ids: set[TrackId] = set()
        for section in sections:
            track_ids = {
                track.id
                for track in tracks
                if self._track_intersects_section(track, section)
            }
            print(f"{section.name}: {len(track_ids)} tracks")
            all_track_ids.update(track_ids)

        print(f"All sections: {len(all_track_ids)} tracks")
        return all_track_ids

    def _track_intersects_section(self, track: Track, section: Section) -> bool:
        section_offset = section.get_offset(EventType.SECTION_ENTER)
        track_as_geom = self._track_geometry_builder.build(track, section_offset)
        section_as_geom = self._section_geometry_builder.build_as_line(section)
        return self._intersect_implementation.line_intersects_line(
            track_as_geom, section_as_geom
        )
