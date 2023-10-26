from pathlib import Path
from typing import Iterable, TypedDict

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from OTAnalytics.application.analysis.intersect import TracksIntersectingSections
from OTAnalytics.application.application import OTAnalyticsApplication
from OTAnalytics.application.use_cases.create_events import CreateEvents
from OTAnalytics.application.use_cases.event_repository import AddEvents, ClearAllEvents
from OTAnalytics.application.use_cases.load_otflow import LoadOtflow
from OTAnalytics.application.use_cases.track_repository import (
    GetAllTrackFiles,
    GetAllTracks,
    GetTracksWithoutSingleDetections,
)
from OTAnalytics.domain.event import EventRepository
from OTAnalytics.domain.flow import FlowRepository
from OTAnalytics.domain.progress import NoProgressbarBuilder
from OTAnalytics.domain.section import SectionRepository
from OTAnalytics.domain.track import Track, TrackFileRepository, TrackRepository
from OTAnalytics.plugin_intersect.shapely.intersect import ShapelyIntersector
from OTAnalytics.plugin_ui.main_application import ApplicationStarter


@pytest.fixture
def ottrk_file() -> Path:
    return Path(
        "/Users/rseng/dev/OpenTrafficCam/OTAnalytics/tests/data/Standard_SCUCKE_FR30_2023-04-18_08-00-00.ottrk"  # noqa
    )


@pytest.fixture
def otflow_file() -> Path:
    return Path(
        "/Users/rseng/dev/OpenTrafficCam/OTAnalytics/tests/data/sections_flows.otflow"  # noqa
    )


@pytest.fixture
def track_repository() -> TrackRepository:
    return TrackRepository()


@pytest.fixture
def section_repository() -> SectionRepository:
    return SectionRepository()


@pytest.fixture
def flow_repository() -> FlowRepository:
    return FlowRepository()


@pytest.fixture
def event_repository() -> EventRepository:
    return EventRepository()


@pytest.fixture
def starter() -> ApplicationStarter:
    return ApplicationStarter()


@pytest.fixture
def get_all_tracks(track_repository: TrackRepository) -> GetAllTracks:
    return GetAllTracks(track_repository)


@pytest.fixture
def get_tracks_without_single_detections(
    track_repository: TrackRepository,
) -> GetTracksWithoutSingleDetections:
    return GetTracksWithoutSingleDetections(track_repository)


@pytest.fixture
def add_events(event_repository: EventRepository) -> AddEvents:
    return AddEvents(event_repository)


@pytest.fixture
def clear_events(event_repository: EventRepository) -> ClearAllEvents:
    return ClearAllEvents(event_repository)


@pytest.fixture
def create_events(
    starter: ApplicationStarter,
    section_repository: SectionRepository,
    clear_all_events: ClearAllEvents,
    get_tracks_without_single_detections: GetTracksWithoutSingleDetections,
    add_events: AddEvents,
) -> CreateEvents:
    return starter._create_use_case_create_events(
        section_repository,
        clear_all_events,
        get_tracks_without_single_detections,
        add_events,
    )


@pytest.fixture()
def track_file_repository() -> TrackFileRepository:
    return TrackFileRepository()


def create_app(
    starter: ApplicationStarter,
    track_repository: TrackRepository,
    track_file_repository: TrackFileRepository,
    section_repository: SectionRepository,
    flow_repository: FlowRepository,
    event_repository: EventRepository,
) -> OTAnalyticsApplication:
    starter = ApplicationStarter()
    progressbar = NoProgressbarBuilder()
    datastore = starter._create_datastore(
        track_repository,
        track_file_repository,
        section_repository,
        flow_repository,
        event_repository,
        progressbar,
    )
    track_state = starter._create_track_state()
    track_view_state = starter._create_track_view_state()
    section_state = starter._create_section_state(section_repository)
    flow_state = starter._create_flow_state()
    clear_all_events = ClearAllEvents(event_repository)

    get_all_tracks = GetAllTracks(track_repository)
    get_tracks_without_single_detections = GetTracksWithoutSingleDetections(
        track_repository
    )
    add_events = AddEvents(event_repository)
    create_events = starter._create_use_case_create_events(
        section_repository,
        clear_all_events,
        get_tracks_without_single_detections,
        add_events,
    )
    tracks_metadata = starter._create_tracks_metadata(track_repository)
    action_state = starter._create_action_state()
    filter_element_settings_restorer = starter._create_filter_element_setting_restorer()
    generate_flows = starter._create_flow_generator(section_repository, flow_repository)
    create_intersection_events = starter._create_use_case_create_intersection_events(
        section_repository, get_tracks_without_single_detections, add_events
    )
    export_counts = starter._create_export_counts(
        event_repository, flow_repository, track_repository
    )
    return OTAnalyticsApplication(
        datastore=datastore,
        track_state=track_state,
        track_view_state=track_view_state,
        section_state=section_state,
        flow_state=flow_state,
        tracks_metadata=tracks_metadata,
        action_state=action_state,
        filter_element_setting_restorer=filter_element_settings_restorer,
        generate_flows=generate_flows,
        create_intersection_events=create_intersection_events,
        export_counts=export_counts,
        create_events=create_events,
        get_all_track_files=GetAllTrackFiles(track_file_repository),
        load_otflow=LoadOtflow(),
    )


@pytest.fixture
def app(
    starter: ApplicationStarter,
    track_repository: TrackRepository,
    section_repository: SectionRepository,
    flow_repository: FlowRepository,
    event_repository: EventRepository,
) -> OTAnalyticsApplication:
    return create_app(
        starter, track_repository, section_repository, flow_repository, event_repository
    )


@pytest.fixture
def tracks_intersecting_sections(
    starter: ApplicationStarter,
    track_repository: TrackRepository,
) -> TracksIntersectingSections:
    get_all_tracks = GetAllTracks(track_repository)
    return starter._create_tracks_intersecting_sections(
        get_all_tracks, ShapelyIntersector()
    )


class TrackCount(TypedDict):
    id: int
    det_count: int


def get_track_counts(tracks: Iterable[Track]) -> list[TrackCount]:
    counts: list[TrackCount] = []
    for track in tracks:
        counts.append(
            {"id": track.id.id, "det_count": len(track.detections)},
        )
    return sorted(counts, key=lambda count: count["det_count"])


def filter_detection_count_ge(
    counts: list[TrackCount], thresh: int
) -> list[TrackCount]:
    return [count for count in counts if count["det_count"] >= thresh]


class TestProfile:
    def fill_track_repository(self, app: OTAnalyticsApplication, ottrk: Path) -> None:
        app.add_tracks_of_files([ottrk])

    def fill_section_repository(
        self, app: OTAnalyticsApplication, otflow: Path
    ) -> None:
        app.load_otflow(otflow)

    def test_load_ottrks(
        self,
        benchmark: BenchmarkFixture,
        app: OTAnalyticsApplication,
        ottrk_file: Path,
    ) -> None:
        benchmark.pedantic(self.fill_track_repository, args=(app, ottrk_file))

    @pytest.mark.skip
    def test_create_events(
        self,
        benchmark: BenchmarkFixture,
        create_events: CreateEvents,
        app: OTAnalyticsApplication,
        ottrk_file: Path,
        otflow_file: Path,
    ) -> None:
        def setup() -> None:
            app._clear_event_repository()
            return None

        self.fill_track_repository(app, ottrk_file)
        self.fill_section_repository(app, otflow_file)
        benchmark.pedantic(
            create_events, setup=setup, rounds=5, iterations=1, warmup_rounds=1
        )

    @pytest.mark.skip
    def test_tracks_intersecting_sections(
        self,
        benchmark: BenchmarkFixture,
        tracks_intersecting_sections: TracksIntersectingSections,
        app: OTAnalyticsApplication,
        ottrk_file: Path,
        otflow_file: Path,
    ) -> None:
        self.fill_track_repository(app, ottrk_file)
        self.fill_section_repository(app, otflow_file)
        sections = app._datastore.get_all_sections()
        benchmark.pedantic(
            tracks_intersecting_sections,
            args=(sections,),
            rounds=2,
            iterations=4,
            warmup_rounds=1,
        )
