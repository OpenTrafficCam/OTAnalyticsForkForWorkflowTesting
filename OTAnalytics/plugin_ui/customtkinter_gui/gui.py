from typing import Any

from customtkinter import CTk, set_appearance_mode, set_default_color_theme

from OTAnalytics.adapter_ui.view_model import ViewModel
from OTAnalytics.plugin_ui.customtkinter_gui.constants import PADX, STICKY
from OTAnalytics.plugin_ui.customtkinter_gui.frame_analysis import FrameAnalysis
from OTAnalytics.plugin_ui.customtkinter_gui.frame_canvas import FrameCanvas
from OTAnalytics.plugin_ui.customtkinter_gui.frame_configuration import (
    FrameConfiguration,
)
from OTAnalytics.plugin_ui.customtkinter_gui.frame_filter import FrameFilter
from OTAnalytics.plugin_ui.customtkinter_gui.frame_track_plotting import (
    FrameTrackPlotting,
)
from OTAnalytics.plugin_ui.customtkinter_gui.frame_tracks import TracksFrame
from OTAnalytics.plugin_ui.customtkinter_gui.helpers import get_widget_position
from OTAnalytics.plugin_ui.customtkinter_gui.messagebox import InfoBox


class ModifiedCTk(CTk):
    def __init__(
        self,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.protocol("WM_DELETE_WINDOW", self._ask_to_close)

    def _ask_to_close(self) -> None:
        infobox = InfoBox(
            title="Close application",
            message="Do you want to close the application?",
            initial_position=get_widget_position(self),
            show_cancel=True,
        )
        if infobox.canceled:
            return
        self.quit()

    def report_callback_exception(self, exc: Any, val: Any, tb: Any) -> None:
        InfoBox(
            message=str(val), title="Error", initial_position=get_widget_position(self)
        )


class OTAnalyticsGui:
    def __init__(
        self,
        view_model: ViewModel,
        app: CTk = ModifiedCTk(),
    ) -> None:
        self._view_model = view_model
        self._app: CTk = app

    def start(self) -> None:
        self._show_gui()

    def _show_gui(self) -> None:
        set_appearance_mode("System")
        set_default_color_theme("green")

        self._app.title("OTAnalytics")
        self._app.grid_rowconfigure(1, weight=1)
        self._app.grid_columnconfigure(1, weight=1)

        self._get_widgets()
        self._place_widgets()
        self._app.mainloop()

    def _get_widgets(self) -> None:
        self.frame_track_plotting = FrameTrackPlotting(
            master=self._app,
            viewmodel=self._view_model,
        )
        self.frame_filter = FrameFilter(master=self._app, viewmodel=self._view_model)
        self.frame_canvas = FrameCanvas(
            master=self._app,
            viewmodel=self._view_model,
        )
        self.frame_tracks = TracksFrame(
            master=self._app,
            viewmodel=self._view_model,
        )
        self.tabview_configuration = FrameConfiguration(
            master=self._app, viewmodel=self._view_model
        )
        self.frame_analysis = FrameAnalysis(
            master=self._app, viewmodel=self._view_model
        )

    def _place_widgets(self) -> None:
        PADY = 10
        self.frame_track_plotting.grid(
            row=0, column=0, padx=PADX, pady=PADY, sticky=STICKY
        )
        self.frame_filter.grid(row=0, column=1, padx=PADX, pady=PADY, sticky=STICKY)
        self.frame_canvas.grid(
            row=1,
            column=0,
            rowspan=3,
            columnspan=2,
            padx=PADX,
            pady=PADY,
            sticky=STICKY,
        )
        self.frame_tracks.grid(row=0, column=2, padx=PADX, pady=PADY, sticky=STICKY)
        self.tabview_configuration.grid(
            row=1, column=2, padx=PADX, pady=PADY, sticky=STICKY
        )
        self.frame_analysis.grid(row=2, column=2, padx=PADX, pady=PADY, sticky=STICKY)
