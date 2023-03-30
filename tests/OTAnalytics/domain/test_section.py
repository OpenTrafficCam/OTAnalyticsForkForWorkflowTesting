from unittest.mock import Mock

import pytest

from OTAnalytics.domain.event import EventType
from OTAnalytics.domain.geometry import Coordinate, RelativeOffsetCoordinate, X, Y
from OTAnalytics.domain.section import (
    AREA,
    COORDINATES,
    END,
    ID,
    LINE,
    PLUGIN_DATA,
    RELATIVE_OFFSET_COORDINATES,
    START,
    TYPE,
    Area,
    LineSection,
    SectionRepository,
)


class TestLineSection:
    def test_coordinates_define_point_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            LineSection(
                id="N",
                relative_offset_coordinates={
                    EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
                },
                plugin_data={},
                start=Coordinate(0, 0),
                end=Coordinate(0, 0),
            )

    def test_valid_line_section(self) -> None:
        LineSection(
            id="N",
            relative_offset_coordinates={
                EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
            },
            plugin_data={},
            start=Coordinate(0, 0),
            end=Coordinate(1, 0),
        )

    def test_to_dict(self) -> None:
        section_id = "some"
        start = Coordinate(0, 0)
        end = Coordinate(1, 1)
        section = LineSection(
            id=section_id,
            relative_offset_coordinates={
                EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
            },
            plugin_data={},
            start=start,
            end=end,
        )

        section_dict = section.to_dict()

        assert section_dict == {
            TYPE: LINE,
            ID: section_id,
            RELATIVE_OFFSET_COORDINATES: {
                EventType.SECTION_ENTER.serialize(): {X: 0, Y: 0}
            },
            START: start.to_dict(),
            END: end.to_dict(),
            PLUGIN_DATA: {},
        }

    def test_initialization_with_plugin_data(self) -> None:
        plugin_data: dict = {"key_1": "some data", "key_2": "some data"}
        id = "N"
        start = Coordinate(0, 0)
        end = Coordinate(10, 10)
        line = LineSection(
            id=id,
            relative_offset_coordinates={
                EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
            },
            plugin_data=plugin_data,
            start=start,
            end=end,
        )
        assert line.id == id
        assert line.plugin_data == plugin_data
        assert line.start == start
        assert line.end == end


class TestAreaSection:
    def test_coordinates_define_point_raises_value_error(self) -> None:
        coordinates = [Coordinate(0, 0), Coordinate(0, 0)]
        with pytest.raises(ValueError):
            Area(
                id="N",
                relative_offset_coordinates={
                    EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
                },
                plugin_data={},
                coordinates=coordinates,
            )

    def test_insufficient_coordinates_raises_value_error(self) -> None:
        coordinates = [
            Coordinate(0, 0),
            Coordinate(2, 0),
            Coordinate(0, 0),
        ]
        with pytest.raises(ValueError):
            Area(
                id="N",
                relative_offset_coordinates={
                    EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
                },
                plugin_data={},
                coordinates=coordinates,
            )

    def test_valid_area(self) -> None:
        coordinates = [
            Coordinate(0, 0),
            Coordinate(1, 0),
            Coordinate(2, 0),
            Coordinate(0, 0),
        ]
        area = Area(
            id="N",
            relative_offset_coordinates={
                EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
            },
            plugin_data={},
            coordinates=coordinates,
        )

        assert area.id == "N"
        assert area.coordinates == coordinates

    def test_to_dict(self) -> None:
        section_id = "some"
        first = Coordinate(0, 0)
        second = Coordinate(1, 0)
        third = Coordinate(1, 1)
        forth = Coordinate(0, 0)
        section = Area(
            id=section_id,
            relative_offset_coordinates={
                EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
            },
            plugin_data={},
            coordinates=[first, second, third, forth],
        )

        section_dict = section.to_dict()

        assert section_dict == {
            TYPE: AREA,
            ID: section_id,
            RELATIVE_OFFSET_COORDINATES: {
                EventType.SECTION_ENTER.serialize(): {X: 0, Y: 0}
            },
            COORDINATES: [
                first.to_dict(),
                second.to_dict(),
                third.to_dict(),
                forth.to_dict(),
            ],
            PLUGIN_DATA: {},
        }

    def test_initialization_with_plugin_data(self) -> None:
        plugin_data: dict = {"key_1": "some data", "key_2": "some data"}
        id = "N"
        coordinates = [
            Coordinate(0, 0),
            Coordinate(1, 0),
            Coordinate(2, 0),
            Coordinate(0, 0),
        ]
        line = Area(
            id=id,
            relative_offset_coordinates={
                EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
            },
            plugin_data=plugin_data,
            coordinates=coordinates,
        )
        assert line.id == id
        assert line.plugin_data == plugin_data
        assert line.coordinates == coordinates


class TestSectionRepository:
    def test_add(self) -> None:
        section = Mock()
        repository = SectionRepository()

        repository.add(section)

        assert section in repository.get_all()

    def test_add_all(self) -> None:
        first_section = Mock()
        second_section = Mock()
        repository = SectionRepository()

        repository.add_all([first_section, second_section])

        assert first_section in repository.get_all()
        assert second_section in repository.get_all()

    def test_remove(self) -> None:
        first_section = Mock()
        second_section = Mock()
        repository = SectionRepository()
        repository.add_all([first_section, second_section])

        repository.remove(first_section)

        assert first_section not in repository.get_all()
        assert second_section in repository.get_all()
