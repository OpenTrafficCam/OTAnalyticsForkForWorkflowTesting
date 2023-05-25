from tkinter.filedialog import asksaveasfilename
from typing import Any

from customtkinter import CTkButton, CTkFrame, CTkLabel

from OTAnalytics.adapter_ui.view_model import ViewModel
from OTAnalytics.plugin_ui.customtkinter_gui.constants import PADX, PADY, STICKY


class FrameTrafficCounting(CTkFrame):
    def __init__(self, viewmodel: ViewModel, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._viewmodel = viewmodel
        self._get_widgets()
        self._place_widgets()

    def _get_widgets(self) -> None:
        self._label_title = CTkLabel(master=self, text="Traffic Counting")
        self._button_start_counting = CTkButton(
            master=self,
            text="Count",
            command=self._start_counting,
        )
        self._button_save_counts = CTkButton(
            master=self,
            text="Save",
            command=self._save_counting,
        )

    def _place_widgets(self) -> None:
        self._label_title.grid(row=0, column=0, padx=PADX, pady=PADY, sticky=STICKY)
        self._button_start_counting.grid(
            row=1, column=0, padx=PADX, pady=PADY, sticky=STICKY
        )
        self._button_save_counts.grid(
            row=2, column=0, padx=PADX, pady=PADY, sticky=STICKY
        )

    def _start_counting(self) -> None:
        print("Start counting")
        self._viewmodel.start_counting()

    def _save_counting(self) -> None:
        file = asksaveasfilename(
            title="Save counts file as",
            filetypes=[("JSON", "*.json")],
            defaultextension=".json",
        )
        if not file:
            return
        self._viewmodel.save_counts(file)
