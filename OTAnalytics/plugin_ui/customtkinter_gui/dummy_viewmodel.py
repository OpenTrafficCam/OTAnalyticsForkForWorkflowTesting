from dataclasses import dataclass
from pathlib import Path
from tkinter.filedialog import askopenfilename, askopenfilenames, asksaveasfilename
from typing import Iterable, Optional

from OTAnalytics.adapter_ui.abstract_canvas import AbstractCanvas
from OTAnalytics.adapter_ui.abstract_frame_canvas import AbstractFrameCanvas
from OTAnalytics.adapter_ui.abstract_frame_tracks import AbstractFrameTracks
from OTAnalytics.adapter_ui.abstract_stateful_widget import AbstractStatefulWidget
from OTAnalytics.adapter_ui.abstract_treeview_interface import AbstractTreeviewInterface
from OTAnalytics.adapter_ui.view_model import DISTANCES, ViewModel
from OTAnalytics.application.application import OTAnalyticsApplication
from OTAnalytics.application.datastore import NoSectionsToSave, SectionParser
from OTAnalytics.domain import geometry
from OTAnalytics.domain.section import (
    COORDINATES,
    ID,
    MissingSection,
    Section,
    SectionId,
    SectionListObserver,
)
from OTAnalytics.domain.track import TrackImage
from OTAnalytics.plugin_ui.customtkinter_gui.helpers import get_widget_position
from OTAnalytics.plugin_ui.customtkinter_gui.line_section import (
    CanvasElementDeleter,
    CanvasElementPainter,
    SectionBuilder,
)
from OTAnalytics.plugin_ui.customtkinter_gui.messagebox import InfoBox
from OTAnalytics.plugin_ui.customtkinter_gui.style import (
    DEFAULT_SECTION_STYLE,
    EDITED_SECTION_STYLE,
    SELECTED_SECTION_STYLE,
)
from OTAnalytics.plugin_ui.customtkinter_gui.toplevel_flows import (
    DISTANCE,
    END_SECTION,
    START_SECTION,
    ToplevelFlows,
)
from OTAnalytics.plugin_ui.customtkinter_gui.toplevel_sections import ToplevelSections

LINE_SECTION: str = "line_section"
TO_SECTION = "to_section"
FROM_SECTION = "from_section"


class MissingInjectedInstanceError(Exception):
    """Raise when no instance of an object was injected before referencing it"""

    def __init__(self, injected_object: str):
        message = (
            f"An instance of {injected_object} has to be injected before referencing it"
        )
        super().__init__(message)


def flow_id(from_section: str, to_section: str) -> str:
    return f"{from_section} -> {to_section}"


@dataclass(frozen=True)
class FlowId:
    from_section: str
    to_section: str


def parse_flow_id(id: str) -> FlowId:
    parts = id.split(" -> ")
    return FlowId(from_section=parts[0], to_section=parts[1])


class DummyViewModel(ViewModel, SectionListObserver):
    def __init__(
        self,
        application: OTAnalyticsApplication,
        section_parser: SectionParser,
    ) -> None:
        self._application = application
        self._section_parser: SectionParser = section_parser
        self._frame_tracks: Optional[AbstractFrameTracks] = None
        self._frame_canvas: Optional[AbstractFrameCanvas] = None
        self._canvas: Optional[AbstractCanvas] = None
        self._treeview_sections: Optional[AbstractTreeviewInterface]
        self._treeview_flows: Optional[AbstractTreeviewInterface]
        self._button_edit_section_geometry: Optional[AbstractStatefulWidget]
        self._button_edit_section_metadata: Optional[AbstractStatefulWidget]
        self._button_remove_section: Optional[AbstractStatefulWidget]
        self._button_edit_flow_metadata: Optional[AbstractStatefulWidget]
        self._button_remove_flow: Optional[AbstractStatefulWidget]
        self._new_section: dict = {}
        self._selected_section_ids: list[str] = []
        self.register_to_subjects()

    def register_to_subjects(self) -> None:
        self._application.register_sections_observer(self)
        self._application.register_section_changed_observer(self._on_section_changed)

        self._application.track_view_state.show_tracks.register(
            self._on_show_tracks_state_updated
        )
        self._application.section_state.selected_section.register(
            self._update_selected_sections
        )
        self._application.section_state.selected_flow.register(
            self._update_selected_flows
        )
        self._application.track_view_state.background_image.register(
            self._on_background_updated
        )
        self._application.track_view_state.track_offset.register(self._update_offset)

    def _on_section_changed(self, section_id: SectionId) -> None:
        self.notify_sections([section_id])

    def _on_show_tracks_state_updated(self, value: Optional[bool]) -> None:
        if self._frame_canvas is None:
            raise MissingInjectedInstanceError(AbstractFrameCanvas.__name__)

        new_value = value or False
        self._frame_canvas.update_show_tracks(new_value)

    def _on_background_updated(self, image: Optional[TrackImage]) -> None:
        if self._frame_canvas is None:
            raise MissingInjectedInstanceError(AbstractFrameCanvas.__name__)

        if image:
            self._frame_canvas.update_background(image)

    def update_show_tracks_state(self, value: bool) -> None:
        self._application.track_view_state.show_tracks.set(value)

    def notify_sections(self, sections: list[SectionId]) -> None:
        if self._treeview_sections is None:
            raise MissingInjectedInstanceError(type(self._treeview_sections).__name__)
        if self._treeview_flows is None:
            raise MissingInjectedInstanceError(type(self._treeview_flows).__name__)
        self.refresh_sections_on_gui()
        self._treeview_sections.update_items()
        self._treeview_flows.update_items()

    def set_tracks_frame(self, tracks_frame: AbstractFrameTracks) -> None:
        self._frame_tracks = tracks_frame

    def set_canvas(self, canvas: AbstractCanvas) -> None:
        self._canvas = canvas

    def set_tracks_canvas(self, tracks_canvas: AbstractFrameCanvas) -> None:
        self._frame_canvas = tracks_canvas

    def set_treeview_sections(self, treeview: AbstractTreeviewInterface) -> None:
        self._treeview_sections = treeview

    def set_treeview_flows(self, treeview: AbstractTreeviewInterface) -> None:
        self._treeview_flows = treeview

    def set_button_edit_section_geometry(self, button: AbstractStatefulWidget) -> None:
        self._button_edit_section_geometry = button

    def set_button_edit_section_metadata(self, button: AbstractStatefulWidget) -> None:
        self._button_edit_section_metadata = button

    def set_button_remove_section(self, button: AbstractStatefulWidget) -> None:
        self._button_remove_section = button

    def set_button_edit_flow_metadata(self, button: AbstractStatefulWidget) -> None:
        self._button_edit_flow_metadata = button

    def set_button_remove_flow(self, button: AbstractStatefulWidget) -> None:
        self._button_remove_flow = button

    # TODO: @randyseng take list of id´s as parameter and remove first line
    def _update_selected_sections(self, section_id: Optional[SectionId]) -> None:
        section_ids = [section_id] if section_id is not None else []
        current_ids = [id.id for id in section_ids]
        self._selected_section_ids = current_ids

        if self._treeview_sections is None:
            raise MissingInjectedInstanceError(type(self._treeview_sections).__name__)
        self.refresh_sections_on_gui()
        self._treeview_sections.update_selected_items(self._selected_section_ids)

        if self._button_edit_section_geometry is None:
            raise MissingInjectedInstanceError(
                type(self._button_edit_section_geometry).__name__
            )
        if self._button_edit_section_metadata is None:
            raise MissingInjectedInstanceError(
                type(self._button_edit_section_metadata).__name__
            )
        if self._button_remove_section is None:
            raise MissingInjectedInstanceError(
                type(self._button_remove_section).__name__
            )
        if len(self._selected_section_ids) == 1:
            self._button_edit_section_geometry.activate()
            self._button_edit_section_metadata.activate()
        else:
            self._button_edit_section_geometry.deactivate()
            self._button_edit_section_metadata.deactivate()
        if self._selected_section_ids:
            self._button_remove_section.activate()
        else:
            self._button_remove_section.deactivate()

    # TODO: @randyseng take list of id´s as parameter and remove first line
    def _update_selected_flows(self, flow_id: Optional[str]) -> None:
        flow_ids = [flow_id] if flow_id is not None else []
        if self._button_edit_flow_metadata is None:
            raise MissingInjectedInstanceError(
                type(self._button_edit_flow_metadata).__name__
            )
        if self._button_remove_flow is None:
            raise MissingInjectedInstanceError(type(self._button_remove_flow).__name__)
        if len(flow_ids) == 1:
            self._button_edit_flow_metadata.activate()
        else:
            self._button_edit_flow_metadata.deactivate()
        if self._selected_section_ids:
            self._button_remove_flow.activate()
        else:
            self._button_remove_flow.deactivate()

    # TODO: @randyseng return list of flow id´s from get method and modify this method
    def get_selected_flows(self) -> list[str]:
        flow_id = self._application.section_state.selected_flow.get()
        return [flow_id] if flow_id is not None else []

    # TODO: @randyseng pass list of flow id´s to set method and modify this method
    def set_selected_flow_ids(self, ids: list[str]) -> None:
        flow_id = ids[0] if ids else None
        self._application.section_state.selected_flow.set(flow_id)
        self.refresh_sections_on_gui()

    def set_selected_section_ids(self, ids: list[str]) -> None:
        self._selected_section_ids = ids
        # TODO: @randyseng pass list of sections_ids to set_selected_section
        self._application.set_selected_section(ids[0] if ids else None)

        print(f"Line sections selected in treeview: ids={ids}")

    def load_tracks(self) -> None:
        track_files = askopenfilenames(
            title="Load track files", filetypes=[("tracks file", "*.ottrk")]
        )
        if not track_files:
            return
        print(f"Tracks files to load: {track_files}")
        track_paths = [Path(file) for file in track_files]
        self._application.add_tracks_of_files(track_files=track_paths)

    def load_sections(self) -> None:  # sourcery skip: avoid-builtin-shadow
        # INFO: Current behavior: Overwrites existing sections
        sections_file = askopenfilename(
            title="Load sections file", filetypes=[("otflow file", "*.otflow")]
        )
        if not sections_file:
            return
        print(f"Sections file to load: {sections_file}")
        self._application.add_sections_of_file(sections_file=Path(sections_file))
        self.refresh_sections_on_gui()

    def save_sections(self) -> None:
        sections_file = asksaveasfilename(
            title="Save sections file as", filetypes=[("sections file", "*.otflow")]
        )
        if not sections_file:
            return
        print(f"Sections file to save: {sections_file}")
        try:
            self._application.save_sections(Path(sections_file))
        except NoSectionsToSave as cause:
            if self._treeview_sections is None:
                raise MissingInjectedInstanceError(
                    type(self._treeview_sections).__name__
                ) from cause
            position = self._treeview_sections.get_position()
            InfoBox(
                message="No sections to save, please add new sections first",
                initial_position=position,
            )
            return

    def add_section(self) -> None:
        self.set_selected_section_ids([])
        if self._canvas is None:
            raise MissingInjectedInstanceError(AbstractCanvas.__name__)
        SectionBuilder(viewmodel=self, canvas=self._canvas, style=EDITED_SECTION_STYLE)

    def set_new_section(self, section: Section) -> None:
        self._application.add_section(section)
        print(f"New line_section created: {section}")
        # TODO: @randyseng give "[section.id]" to _update_selected_sections
        self._update_selected_sections(section.id)

    def edit_section_geometry(self) -> None:
        if len(self._selected_section_ids) != 1:
            return
        selected_section_id = self._selected_section_ids[0]
        if self._canvas is None:
            raise MissingInjectedInstanceError(AbstractCanvas.__name__)
        CanvasElementDeleter(canvas=self._canvas).delete(tag_or_id=selected_section_id)
        current_section = None
        if self._selected_section_ids:
            current_section = self._application.get_section_for(
                SectionId(selected_section_id)
            )
        SectionBuilder(
            viewmodel=self,
            canvas=self._canvas,
            section=current_section,
            style=EDITED_SECTION_STYLE,
        )
        self.refresh_sections_on_gui()

    def edit_section_metadata(self) -> None:
        if self._treeview_sections is None:
            raise MissingInjectedInstanceError(type(self._treeview_sections).__name__)
        if len(self._selected_section_ids) != 1:
            position = self._treeview_sections.get_position()
            InfoBox(
                message="Please select a single section to edit",
                initial_position=position,
            )
            return
        selected_section_id = self._selected_section_ids[0]
        section_id = SectionId(selected_section_id)
        if selected_section := self._application.get_section_for(section_id):
            self._update_metadata(selected_section)

    def _update_metadata(self, selected_section: Section) -> None:
        current_data = selected_section.to_dict()
        if self._canvas is None:
            raise MissingInjectedInstanceError(AbstractCanvas.__name__)
        position = get_widget_position(widget=self._canvas)
        updated_section_data = ToplevelSections(
            title="Edit section",
            initial_position=position,
            input_values=current_data,
        ).get_metadata()
        self._set_section_data(
            id=selected_section.id,
            data=updated_section_data,
        )
        self.refresh_sections_on_gui()
        print(f"Updated line_section Metadata: {updated_section_data}")

    def _set_section_data(self, id: SectionId, data: dict) -> None:
        section = self._section_parser.parse_section(data)
        self._application.remove_section(id)
        self._application.add_section(section)

    def remove_sections(self) -> None:
        if self._treeview_sections is None:
            raise MissingInjectedInstanceError(type(self._treeview_sections).__name__)
        if len(self._selected_section_ids) == 0:
            position = self._treeview_sections.get_position()
            InfoBox(
                message="Please select one or more sections to remove",
                initial_position=position,
            )
            return
        # TODO: @randyseng pass list to remove_section method like in comment below
        # self._application.remove_section(
        #     [SectionId(id) for id in self._selected_section_ids]
        # )
        self._application.remove_section(SectionId(self._selected_section_ids[0]))
        self.refresh_sections_on_gui()

    def refresh_sections_on_gui(self) -> None:
        self._remove_all_sections_from_canvas()
        self._draw_all_sections_on_canvas()

    def _draw_all_sections_on_canvas(self) -> None:
        if self._canvas is None:
            raise MissingInjectedInstanceError(AbstractCanvas.__name__)
        painter = CanvasElementPainter(canvas=self._canvas)
        for section in self._get_sections():
            if section[ID] in self._selected_section_ids:
                style = SELECTED_SECTION_STYLE
            else:
                style = DEFAULT_SECTION_STYLE
            painter.draw(
                tags=[LINE_SECTION],
                id=section[ID],
                coordinates=section[COORDINATES],
                style=style,
            )

    def _get_sections(self) -> Iterable[dict]:
        return map(
            lambda section: self._transform_coordinates(section),
            map(
                lambda section: section.to_dict(),
                self._application.get_all_sections(),
            ),
        )

    def _transform_coordinates(self, section: dict) -> dict:
        section[COORDINATES] = [
            self._to_coordinate_tuple(coordinate) for coordinate in section[COORDINATES]
        ]
        return section

    def _to_coordinate_tuple(self, coordinate: dict) -> tuple[int, int]:
        return (coordinate[geometry.X], coordinate[geometry.Y])

    def _remove_all_sections_from_canvas(self) -> None:
        if self._canvas is None:
            raise MissingInjectedInstanceError(AbstractCanvas.__name__)
        CanvasElementDeleter(canvas=self._canvas).delete(tag_or_id=LINE_SECTION)

    def get_all_sections(self) -> Iterable[Section]:
        return self._application.get_all_sections()

    def get_all_flows(self) -> list[str]:
        flows: list[str] = []
        for section in self.get_all_sections():
            distances = section.plugin_data.get(DISTANCES, {})
            flows.extend(
                flow_id(section.id.id, other_section)
                for other_section in distances.keys()
            )
        return flows

    def add_flow(self) -> None:
        if flow_data := self._show_distances_window():
            self.__update_flow_data(flow_data)
            print(f"Added new flow: {flow_data}")

    def _show_distances_window(
        self,
        input_values: dict = {},
        title: str = "Add flow",
    ) -> dict | None:
        if self._treeview_flows is None:
            raise MissingInjectedInstanceError(type(self._treeview_flows).__name__)
        position = self._treeview_flows.get_position()
        section_ids = [section.id.id for section in self.get_all_sections()]
        if len(section_ids) < 2:
            InfoBox(
                message="To add a flow, at least two sections are needed",
                initial_position=position,
            )
            return {}
        return ToplevelFlows(
            title=title,
            initial_position=position,
            section_ids=section_ids,
            input_values=input_values,
        ).get_data()

    def __update_flow_data(self, new_flow: dict, old_flow: dict = {}) -> None:
        new_section_id = SectionId(new_flow[START_SECTION])
        if section := self._application.get_section_for(section_id=new_section_id):
            self.__clear_flow_data(flow=old_flow)
            self._set_new_flow_data(section=section, flow=new_flow)
        else:
            raise MissingSection(f"Could not find section for id {new_section_id}")

    def _set_new_flow_data(self, section: Section, flow: dict) -> None:
        plugin_data = section.plugin_data.copy()
        distance_data = plugin_data.get(DISTANCES, {})
        new_data = {flow[END_SECTION]: flow[DISTANCE]}
        distance_data.update(new_data)
        plugin_data[DISTANCES] = distance_data
        self._application.set_section_plugin_data(section.id, plugin_data)

    def __clear_flow_data(self, flow: dict = {}) -> None:
        if flow:
            section_id = SectionId(flow[START_SECTION])
            if section := self._application.get_section_for(section_id=section_id):
                end_section = flow[END_SECTION]
                plugin_data = section.plugin_data.copy()
                distance_data = plugin_data.get(DISTANCES, {})
                del distance_data[end_section]
                plugin_data[DISTANCES] = distance_data
                self._application.set_section_plugin_data(section_id, plugin_data)

    def edit_flow(self) -> None:
        selected_flows = self.get_selected_flows()
        if selected_flows != 1:
            if self._treeview_flows is None:
                raise MissingInjectedInstanceError(type(self._treeview_flows).__name__)
            position = position = self._treeview_flows.get_position()
            InfoBox(message="Please select a flow to edit", initial_position=position)
            return
        flow = parse_flow_id(selected_flows[0])
        if from_section := self._application.get_section_for(
            SectionId(flow.from_section)
        ):
            self._edit_flow(flow, from_section)

    def _edit_flow(self, flow: FlowId, from_section: Section) -> None:
        distances = from_section.plugin_data.get(DISTANCES, {})
        distance: str = distances.get(flow.to_section, {})
        input_data = {
            START_SECTION: flow.from_section,
            END_SECTION: flow.to_section,
            DISTANCE: distance,
        }
        old_flow_data = input_data.copy()

        if flow_data := self._show_distances_window(
            input_values=input_data,
            title="Edit flow",
        ):
            self.__update_flow_data(new_flow=flow_data, old_flow=old_flow_data)

    def remove_flows(self) -> None:
        if self._treeview_flows is None:
            raise MissingInjectedInstanceError(type(self._treeview_flows).__name__)
        selected_flows = self.get_selected_flows()
        if len(selected_flows) == 0:
            position = self._treeview_flows.get_position()
            InfoBox(
                message="Please select one or more flows to remove",
                initial_position=position,
            )
            return
        for selected_flow in selected_flows:
            flow = parse_flow_id(selected_flow)
            data = {
                START_SECTION: flow.from_section,
                END_SECTION: flow.to_section,
            }
            self.__clear_flow_data(data)

    def start_analysis(self) -> None:
        self._application.start_analysis()

    def save_events(self, file: str) -> None:
        print(f"Eventlist file to save: {file}")
        self._application.save_events(Path(file))

    def set_track_offset(self, offset_x: float, offset_y: float) -> None:
        offset = geometry.RelativeOffsetCoordinate(offset_x, offset_y)
        self._application.track_view_state.track_offset.set(offset)

    def get_track_offset(self) -> Optional[tuple[float, float]]:
        if current_offset := self._application.get_current_track_offset():
            return (current_offset.x, current_offset.y)
        return None

    def _update_offset(
        self, offset: Optional[geometry.RelativeOffsetCoordinate]
    ) -> None:
        if self._frame_tracks is None:
            raise MissingInjectedInstanceError(AbstractFrameTracks.__name__)

        if offset:
            self._frame_tracks.update_offset(offset.x, offset.y)

    def change_track_offset_to_section_offset(self) -> None:
        return self._application.change_track_offset_to_section_offset()
