from pathlib import Path
from typing import Iterable, TypedDict

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from OTAnalytics.application.analysis.intersect import TracksIntersectingSections
from OTAnalytics.application.application import OTAnalyticsApplication
from OTAnalytics.application.datastore import VideoParser, TrackToVideoRepository, TrackParser, FlowParser
from OTAnalytics.application.state import TrackViewState
from OTAnalytics.application.use_cases.clear_repositories import ClearRepositories
from OTAnalytics.application.use_cases.create_events import CreateEvents
from OTAnalytics.application.use_cases.event_repository import AddEvents, ClearAllEvents
from OTAnalytics.application.use_cases.flow_repository import AddFlow, ClearAllFlows
from OTAnalytics.application.use_cases.load_otflow import LoadOtflow
from OTAnalytics.application.use_cases.load_track_files import LoadTrackFiles
from OTAnalytics.application.use_cases.reset_project_config import ResetProjectConfig
from OTAnalytics.application.use_cases.section_repository import GetSectionsById, AddSection, ClearAllSections
from OTAnalytics.application.use_cases.start_new_project import StartNewProject
from OTAnalytics.application.use_cases.track_repository import (
    GetAllTrackFiles,
    GetAllTracks,
    GetTracksWithoutSingleDetections,
)
from OTAnalytics.application.use_cases.update_project import ProjectUpdater
from OTAnalytics.domain.event import EventRepository
from OTAnalytics.domain.flow import FlowRepository
from OTAnalytics.domain.progress import NoProgressbarBuilder
from OTAnalytics.domain.section import SectionRepository
from OTAnalytics.domain.track import Track, TrackFileRepository, TrackRepository, ByMaxConfidence
from OTAnalytics.domain.video import VideoRepository, VideoReader
from OTAnalytics.plugin_datastore.track_store import PandasTrackClassificationCalculator, PandasByMaxConfidence
from OTAnalytics.plugin_intersect.shapely.intersect import ShapelyIntersector
from OTAnalytics.plugin_parser.otvision_parser import SimpleVideoParser, OttrkParser, PythonDetectionParser, \
    OtFlowParser
from OTAnalytics.plugin_parser.pandas_parser import PandasDetectionParser
from OTAnalytics.plugin_ui.main_application import ApplicationStarter


@pytest.fixture
def ottrk_file(test_data_dir: Path) -> Path:
    return Path(test_data_dir / "OTCamera19_FR20_2023-05-24_00-30-00.ottrk")

@pytest.fixture
def otflow_file(test_data_dir: Path) -> Path:
    return test_data_dir / Path("OTCamera19_FR20_2023-05-24.otflow")


@pytest.fixture
def track_repository() -> TrackRepository:
    return TrackRepository()


@pytest.fixture
def section_repository() -> SectionRepository:
    return SectionRepository()


@pytest.fixture
def video_reader() -> VideoReader:
    return VideoReader()


@pytest.fixture
def video_parser() -> VideoParser:
    return SimpleVideoParser(video_reader)


@pytest.fixture
def video_repository() -> VideoRepository:
    return VideoRepository()


@pytest.fixture
def track_to_video_repository() -> TrackToVideoRepository:
    return TrackToVideoRepository()


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
def get_sections_by_id() -> GetSectionsById:
    return GetSectionsById(section_repository)


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
        clear_events: ClearAllEvents,
        get_tracks_without_single_detections: GetTracksWithoutSingleDetections,
        add_events: AddEvents,
) -> CreateEvents:
    return starter._create_use_case_create_events(
        section_repository,
        clear_events,
        get_tracks_without_single_detections,
        add_events,
        num_processes=1
    )


@pytest.fixture()
def track_file_repository() -> TrackFileRepository:
    return TrackFileRepository()

@pytest.fixture
def python_ottrk_parser(track_repository: TrackRepository) -> TrackParser:
    detection_parser = PythonDetectionParser(ByMaxConfidence(), track_repository)
    return OttrkParser(detection_parser)

@pytest.fixture
def panda_ottrk_parser(track_repository: TrackRepository) -> TrackParser:
    calculator = PandasByMaxConfidence()
    detection_parser = PandasDetectionParser(calculator)
    return OttrkParser(detection_parser)

@pytest.fixture
def otflow_parser() -> FlowParser:
    return OtFlowParser()

def create_app(
        video_parser: VideoParser,
        video_repository: VideoRepository,
        track_repository: TrackRepository,
        track_file_repository: TrackFileRepository,
        track_to_video_repository: TrackToVideoRepository,
        section_repository: SectionRepository,
        flow_repository: FlowRepository,
        event_repository: EventRepository,
) -> OTAnalyticsApplication:
    starter = ApplicationStarter()
    progressbar = NoProgressbarBuilder()
    datastore = starter._create_datastore(
        video_parser,
        video_repository,
        track_repository,
        track_file_repository,
        track_to_video_repository,
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
    clear_all_sections = ClearAllSections(section_repository)
    clear_all_flows = ClearAllFlows(flow_repository)
    add_section = AddSection(section_repository)
    add_flow = AddFlow(flow_repository)
    load_otflow = starter._create_use_case_load_otflow(
        clear_all_sections,
        clear_all_flows,
        clear_all_events,
        datastore._flow_parser,
        add_section,
        add_flow, )
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
        num_processes=1
    )
    tracks_metadata = starter._create_tracks_metadata(track_repository)
    action_state = starter._create_action_state()
    filter_element_settings_restorer = starter._create_filter_element_setting_restorer()
    generate_flows = starter._create_flow_generator(section_repository, flow_repository)
    create_intersection_events = starter._create_use_case_create_intersection_events(
        section_repository, get_tracks_without_single_detections, add_events, num_processes=1
    )
    export_counts = starter._create_export_counts(
        event_repository, flow_repository, track_repository, get_sections_by_id, create_events
    )
    clear_repositories = starter._creater_clear_repositories()
    reset_project_config = starter._create_reset_project_config()
    track_view_state: TrackViewState()
    start_new_project = StartNewProject(clear_repositories= clear_repositories,reset_project_config= reset_project_config,track_view_state= track_view_state)
    project_updater = ProjectUpdater()
    load_track_files = LoadTrackFiles()
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
        load_otflow=load_otflow,
        add_section=add_section,
        add_flow=add_flow,
        clear_all_events=clear_all_events,
        start_new_project=start_new_project,
        project_updater=project_updater,
        load_track_files=load_track_files,
    )


@pytest.fixture
def app(
        video_parser: VideoParser,
        video_repository: VideoRepository,
        track_repository: TrackRepository,
        track_file_repository: TrackFileRepository,
        track_to_video_repository: TrackToVideoRepository,
        section_repository: SectionRepository,
        flow_repository: FlowRepository,
        event_repository: EventRepository,
) -> OTAnalyticsApplication:
    return create_app(
        video_parser, video_repository, track_repository, track_file_repository, track_to_video_repository,
        section_repository, flow_repository, event_repository
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

    def test_load_ottrks_with_python_parser(
            self,
            benchmark: BenchmarkFixture,
            python_ottrk_parser: TrackParser,
            ottrk_file: Path,
    ) -> None:
        benchmark.pedantic(python_ottrk_parser.parse, args=(ottrk_file,))

    def test_load_ottrks_with_pandas_parser(
            self,
            benchmark: BenchmarkFixture,
            panda_ottrk_parser: TrackParser,
            ottrk_file: Path,
    ) -> None:
        benchmark.pedantic(panda_ottrk_parser.parse, args=(ottrk_file,))

    def test_create_events(
            self,
            benchmark: BenchmarkFixture,
            create_events: CreateEvents,
            clear_events: ClearAllEvents,
            python_ottrk_parser: OttrkParser,
            otflow_parser: FlowParser,
            track_repository: TrackRepository,
            flow_repository: FlowRepository,
            section_repository: SectionRepository,
            ottrk_file: Path,
            otflow_file: Path,
    ) -> None:
        def setup() -> None:
            clear_events()

        track_parse_result = python_ottrk_parser.parse(ottrk_file)
        track_repository.add_all(track_parse_result.tracks)
        sections, flows = otflow_parser.parse(otflow_file)
        section_repository.add_all(sections)
        flow_repository.add_all(flows)

        benchmark.pedantic(
            create_events, setup=setup, rounds=5, iterations=1, warmup_rounds=1
        )

    def test_tracks_intersecting_sections(
            self,
            benchmark: BenchmarkFixture,
            python_ottrk_parser: TrackParser,
            otflow_parser: FlowParser,
            track_repository: TrackRepository,
            section_repository: SectionRepository,
            flow_repository: FlowRepository,
            tracks_intersecting_sections: TracksIntersectingSections,
            ottrk_file: Path,
            otflow_file: Path,
    ) -> None:
        track_parse_result = python_ottrk_parser.parse(ottrk_file)
        track_repository.add_all(track_parse_result.tracks)
        sections, _ = otflow_parser.parse(otflow_file)

        benchmark.pedantic(
            tracks_intersecting_sections,
            args=(sections,),
            rounds=2,
            iterations=4,
            warmup_rounds=1,
        )
