from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple

from OTAnalytics.domain.event import Event, EventRepository
from OTAnalytics.domain.section import (
    Section,
    SectionChangedObserver,
    SectionId,
    SectionListObserver,
    SectionRepository,
)
from OTAnalytics.domain.track import (
    Track,
    TrackClassificationCalculator,
    TrackId,
    TrackImage,
    TrackListObserver,
    TrackRepository,
)


class TrackParser(ABC):
    def __init__(
        self,
        track_classification_calculator: TrackClassificationCalculator,
        track_repository: TrackRepository,
    ) -> None:
        self._track_classification_calculator = track_classification_calculator
        self._track_repository = track_repository

    @abstractmethod
    def parse(self, file: Path) -> list[Track]:
        pass


class SectionParser(ABC):
    @abstractmethod
    def parse(self, file: Path) -> list[Section]:
        pass

    @abstractmethod
    def parse_section(self, entry: dict) -> Section:
        pass

    @abstractmethod
    def serialize(self, sections: Iterable[Section], file: Path) -> None:
        pass


class EventListParser(ABC):
    @abstractmethod
    def serialize(
        self, events: Iterable[Event], sections: Iterable[Section], file: Path
    ) -> None:
        pass


class VideoReader(ABC):
    @abstractmethod
    def get_frame(self, video: Path, index: int) -> TrackImage:
        """Get frame of `video` at `index`.

        Args:
            video (Path): the path to the video file.
            index (int): the index of the frame to get.

        Returns:
            TrackImage: the frame.
        """
        pass


@dataclass(frozen=True)
class Video:
    """Represents a video file.

    Args:
        video_reader (VideoReader): A video reader used to get frames.
        path (Path): the video file path.

    Raises:
        ValueError: if video file path does not exist.
    """

    video_reader: VideoReader
    path: Path

    def __post_init__(self) -> None:
        self.check_path_exists()

    def check_path_exists(self) -> None:
        if not self.path.exists():
            raise ValueError("must be an existing path")

    def get_frame(self, index: int) -> TrackImage:
        """Returns the frame of the video at `index`.

        Args:
            index (int): the index of the frame to get.

        Returns:
            TrackImage: the frame.
        """
        return self.video_reader.get_frame(self.path, index)


class VideoListObserver(ABC):
    """
    Interface to listen to changes to a list of tracks.
    """

    @abstractmethod
    def notify_videos(self, videos: list[Video]) -> None:
        """
        Notifies that the given videos have been added.

        Args:
            tracks (list[Video]): list of added videos
        """
        pass


class VideoListSubject:
    """
    Helper class to handle and notify observers
    """

    def __init__(self) -> None:
        self.observers: set[VideoListObserver] = set()

    def register(self, observer: VideoListObserver) -> None:
        """
        Listen to events.

        Args:
            observer (VideoListObserver): listener to add
        """
        self.observers.add(observer)

    def notify(self, videos: list[Video]) -> None:
        """
        Notifies observers about the list of videos.

        Args:
            videos (list[Video]): list of added videos
        """
        [observer.notify_videos(videos) for observer in self.observers]


class VideoParser(ABC):
    @abstractmethod
    def parse(self, file: Path) -> Video:
        pass


class VideoRepository:
    def __init__(self) -> None:
        self._videos: dict[Path, Video] = {}
        self._observers = VideoListSubject()

    def register_videos_observer(self, observer: VideoListObserver) -> None:
        """
        Listen to changes of the repository.

        Args:
            observer (VideoListObserver): listener to be notifed about changes
        """
        self._observers.register(observer)

    def add(self, video: Video) -> None:
        self._videos[video.path] = video
        self._observers.notify([video])

    def get_all(self) -> list[Video]:
        return list(self._videos.values())


class TrackToVideoRepository:
    """
    Repository containing the videos per track.
    """

    def __init__(self) -> None:
        self._videos: dict[TrackId, Video] = {}

    def add(self, track_id: TrackId, video: Video) -> None:
        """
        Add a video for a track id.

        Args:
            track_id (TrackId): id of the track
            video (Video): video containing the track
        """
        self._videos[track_id] = video

    def add_all(self, track_ids: Iterable[TrackId], videos: Iterable[Video]) -> None:
        """
        Add all videos for all tracks.

        Args:
            track_ids (Iterable[TrackId]): track ids to be added
            videos (Iterable[Video]): videos per track id to be added
        """
        for track_id, video in zip(track_ids, videos):
            self.add(track_id, video)

    def get_video_for(self, track_id: TrackId) -> Optional[Video]:
        """
        Retrieve a video for the given track id.

        Args:
            track_id (TrackId): id of the track to get a video for

        Returns:
            Optional[Video]: video of the track if a video exists for the track
        """
        return self._videos.get(track_id)


class TrackVideoParser(ABC):
    """
    Parse the information about videos from a track file
    """

    @abstractmethod
    def parse(
        self, file: Path, track_ids: list[TrackId]
    ) -> Tuple[list[TrackId], list[Video]]:
        """
        Parse the given file in ottrk format and retrieve video information from it

        Args:
            file (Path): file in ottrk format
            track_ids (list[TrackId]): track ids to get videos for

        Returns:
            Tuple[list[TrackId], list[Video]]: track ids and the corresponding videos
        """
        pass


class NoSectionsToSave(Exception):
    pass


class Datastore:
    """
    Central element to hold data in the application.
    """

    def __init__(
        self,
        track_repository: TrackRepository,
        track_parser: TrackParser,
        section_repository: SectionRepository,
        section_parser: SectionParser,
        event_list_parser: EventListParser,
        track_to_video_repository: TrackToVideoRepository,
        video_repository: VideoRepository,
        video_parser: VideoParser,
        track_video_parser: TrackVideoParser,
    ) -> None:
        self._track_parser = track_parser
        self._section_parser = section_parser
        self._event_list_parser = event_list_parser
        self._video_parser = video_parser
        self._track_video_parser = track_video_parser
        self._track_repository = track_repository
        self._section_repository = section_repository
        self._event_repository = EventRepository()
        self._video_repository = video_repository
        self._track_to_video_repository = track_to_video_repository

    def register_video_observer(self, observer: VideoListObserver) -> None:
        self._video_repository.register_videos_observer(observer)

    def register_tracks_observer(self, observer: TrackListObserver) -> None:
        """
        Listen to changes in the track repository.

        Args:
            observer (TrackListObserver): listener to be notified about changes
        """
        self._track_repository.register_tracks_observer(observer)

    def register_sections_observer(self, observer: SectionListObserver) -> None:
        """
        Listen to changes in the section repository.

        Args:
            observer (SectionListObserver): listener to be notified about changes
        """
        self._section_repository.register_sections_observer(observer)

    def load_video_file(self, file: Path) -> None:
        video = self._video_parser.parse(file)
        self._video_repository.add(video)

    def load_track_file(self, file: Path) -> None:
        """
        Load and parse the given track file together with the corresponding video file.

        Args:
            file (Path): file in ottrk format
        """
        tracks = self._track_parser.parse(file)
        track_ids = [track.id for track in tracks]
        track_ids, videos = self._track_video_parser.parse(file, track_ids)
        self._track_to_video_repository.add_all(track_ids, videos)
        self._track_repository.add_all(tracks)

    def load_track_files(self, files: list[Path]) -> None:
        """
        Load and parse the given track file together with the corresponding video file.

        Args:
            file (Path): file in ottrk format
        """
        for file in files:
            self.load_track_file(file)

    def get_all_tracks(self) -> Iterable[Track]:
        """
        Retrieve all tracks of the repository as iterable.

        Returns:
            Iterable[Track]: all tracks of the repository
        """
        return self._track_repository.get_all()

    def delete_all_tracks(self) -> None:
        """Delete all tracks in repository."""
        self._track_repository.delete_all()

    def load_section_file(self, file: Path) -> None:
        """
        Load sections from the given files and store them in the section repository.

        Args:
            file (Path): file to load sections from
        """
        sections = self._section_parser.parse(file)
        self._section_repository.add_all(sections)

    def save_section_file(self, file: Path) -> None:
        """
        Save sections from the repository in a section file.

        Args:
            file (Path): file to save sections to
        """
        if sections := self._section_repository.get_all():
            self._section_parser.serialize(
                sections,
                file=file,
            )
        else:
            raise NoSectionsToSave()

    def get_all_sections(self) -> Iterable[Section]:
        return self._section_repository.get_all()

    def get_section_for(self, section_id: SectionId) -> Optional[Section]:
        return self._section_repository.get(section_id)

    def save_event_list_file(self, file: Path) -> None:
        """
        Save events from the event list in an event file.

        Args:
            file (Path): file to save events to
        """
        self._event_list_parser.serialize(
            self._event_repository.get_all(),
            self._section_repository.get_all(),
            file=file,
        )

    def add_section(self, section: Section) -> None:
        """
        Add a single section to the repository.

        Args:
            section (Section): section to add
        """
        self._section_repository.add(section)

    def add_events(self, events: Iterable[Event]) -> None:
        """Add multiple events to the repository.

        Args:
            events (Iterable[Event]): events to add
        """
        self._event_repository.add_all(events)

    def remove_section(self, section: SectionId) -> None:
        """
        Remove the section from the repository.

        Args:
            section (SectionId): section to remove
        """
        self._section_repository.remove(section)

    def register_section_changed_observer(
        self, observer: SectionChangedObserver
    ) -> None:
        """
        Listen to changes of sections in the repository.

        Args:
            observer (SectionChangedObserver): observer to notify about changes
        """
        self._section_repository.register_section_changed_observer(observer)

    def update_section(self, section: Section) -> None:
        """
        Update the section in the repository.

        Args:
            section (Section): updated section
        """
        self._section_repository.update(section)

    def set_section_plugin_data(self, section_id: SectionId, plugin_data: dict) -> None:
        """
        Set the plugin data of the section. The data will be overridden.

        Args:
            section_id (SectionId): section id to override the plugin data at
            plugin_data (dict): value of the new plugin data
        """
        self._section_repository.set_section_plugin_data(
            section_id=section_id, plugin_data=plugin_data
        )

    def get_image_of_track(self, track_id: TrackId) -> Optional[TrackImage]:
        """
        Retrieve an image for the given track.

        Args:
            track_id (TrackId): identifier for the track

        Returns:
            Optional[TrackImage]: an image of the track if the track is available and
            the image can be loaded
        """
        if video := self._track_to_video_repository.get_video_for(track_id):
            return video.get_frame(0)
        return None
