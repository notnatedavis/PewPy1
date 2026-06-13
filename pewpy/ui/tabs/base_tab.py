#   pewpy/ui/tabs/base_tab.py
#   Base class for all UI tabs – reduces boilerplate

# ----- Imports ----- #
import customtkinter as ctk
from ..utils import create_content_frame

# ----- Main Class ----- #
class BaseTab :
    # Common foundation for every tab in the main window
    # Subclasses must implement _create_widgets()
    # Optionally override update_worker_button() to respond to worker state changes
    def __init__(self, parent_tab, app, ui_queue) -> None :
        self.app = app
        self.ui_queue = ui_queue
        self.frame = create_content_frame(parent_tab)
        self._create_widgets()

    def _create_widgets(self) -> None :
        # Override in subclass to build the tab's UI
        raise NotImplementedError("Subclasses must implement _create_widgets()")

    def update_worker_button(self, worker: str, is_running: bool) -> None :
        # Called by the main window when a worker's state changes
        # The default implementation is a no-op; tabs should override
        # if they host worker toggle buttons
        pass