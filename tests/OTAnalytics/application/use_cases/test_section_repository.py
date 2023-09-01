from unittest.mock import Mock, call

import pytest

from OTAnalytics.application.use_cases.section_repository import (
    AddSection,
    ClearAllSections,
    GetAllSections,
    GetSectionsById,
    SectionAlreadyExists,
    SectionIdAlreadyExists,
)
from OTAnalytics.domain.section import Section, SectionId, SectionRepository


@pytest.fixture
def section_north() -> Mock:
    section = Mock(spec=Section)
    section.name = "North"
    section.id = SectionId("1")
    return section


@pytest.fixture
def section_south() -> Mock:
    section = Mock(spec=Section)
    section.name = "South"
    section.id = SectionId("2")
    return section


@pytest.fixture
def section_repository(section_north: Mock) -> Mock:
    repository = Mock(spec=SectionRepository)
    repository.get_all.return_value = [section_north]
    repository.get_section_ids.return_value = {section_north.id}
    return repository


class TestGetAllSections:
    def test_get_all_sections(
        self, section_north: Mock, section_repository: Mock
    ) -> None:
        get_all_sections = GetAllSections(section_repository)
        sections = get_all_sections()
        assert sections == [section_north]
        section_repository.get_all.assert_called_once()


class TestGetSectionsById:
    def test_get_sections_by_id(
        self, section_repository: Mock, section_north: Section, section_south: Section
    ) -> None:
        section_repository.get.side_effect = [section_north, None]

        get_sections_by_id = GetSectionsById(section_repository)
        sections = get_sections_by_id([section_north.id, section_south.id])

        assert sections == [section_north]
        assert section_repository.get.call_args_list == [
            call(section_north.id),
            call(section_south.id),
        ]


class TestAddSection:
    def test_add_section_with_different_names(
        self, section_repository: Mock, section_south: Mock
    ) -> None:
        use_case = AddSection(section_repository)

        use_case(section_south)

        assert section_repository.add.call_args_list == [
            call(section_south),
        ]
        section_repository.get_section_ids.assert_called_once()

    def test_add_section_with_same_names(
        self,
        section_north: Mock,
        section_south: Mock,
        section_repository: Mock,
    ) -> None:
        section_south.name = section_north.name

        use_case = AddSection(section_repository)

        with pytest.raises(SectionAlreadyExists):
            use_case(section_south)

    def test_add_section_with_existing_id(
        self,
        section_north: Mock,
        section_repository: Mock,
    ) -> None:
        new_section = Mock(spec=Section)
        new_section.id = section_north.id
        new_section.name = "New"

        use_case = AddSection(section_repository)

        with pytest.raises(SectionIdAlreadyExists):
            use_case(new_section)


class TestClearAllSections:
    def test_clear_all_sections(self) -> None:
        section_repository = Mock(spec=SectionRepository)
        clear_all_sections = ClearAllSections(section_repository)
        clear_all_sections()
        section_repository.clear.assert_called_once()
