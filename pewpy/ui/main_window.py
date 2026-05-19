#   pewpy/ui/main_window.py
#   Modern CustomTkinter UI for PewPy – delegates tabs to separate modules

# ----- Imports ----- #
import threading
import queue
import customtkinter as ctk
import logging
from typing import Optional, Dict, Any

from .tabs import GeneralTab, AimbotTab, MouseTab, OverlaysTab
from .overlays import StatsOverlay, ScreenOverlay

# ----- Main Class ----- #
class ModernMainWindow :
    # Main application window with 4 tabs: (General, Aimbot, Mouse, Overlays)

    def __init__(self, app) -> None :
        self.app = app

        # setup appearance
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # create main window
        self.root = ctk.CTk()
        self.root.title("PewPy Control Panel")
        self.root.geometry("500x480")
        self.root.minsize(460, 380)

        # thread-safe communication
        self._ui_queue = queue.Queue(maxsize=50)
        self._update_thread: Optional[threading.Thread] = None
        self._running = True

        # Overlay data bridge (created by app_manager, passed here)
        self.overlay_data = getattr(app, 'overlay_data', None)

        # Overlay window instances (lazy)
        self.stats_overlay: Optional[StatsOverlay] = None
        self.screen_overlay: Optional[ScreenOverlay] = None
        self._stats_visible = False
        self._screen_visible = False

        # setup UI
        self._setup_layout()
        self._create_widgets()

        # start UI updater
        self._start_ui_updater()
        self._start_overlay_updates()

        # handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    def _setup_layout(self) -> None :
        # The whole window is a single CTkTabview
        self.tab_view = ctk.CTkTabview(self.root)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)

        self.general_tab = self.tab_view.add("General")
        self.aimbot_tab = self.tab_view.add("Aimbot")
        self.mouse_tab = self.tab_view.add("Mouse")
        self.overlays_tab = self.tab_view.add("Overlays") 

        # Configure each tab to allow a centered content frame (optional, but consistent)
        for tab in (self.general_tab, self.aimbot_tab, self.mouse_tab, self.overlays_tab):
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)

    def _create_widgets(self) -> None :
        # Instantiate each tab, passing main_window where needed
        self.tabs = {
            'general':    GeneralTab(self.general_tab, self.app, self._ui_queue),
            'aimbot':     AimbotTab(self.aimbot_tab, self.app, self._ui_queue),
            'mouse':      MouseTab(self.mouse_tab, self.app, self._ui_queue),
            'overlays':   OverlaysTab(self.overlays_tab, self.app, self._ui_queue, main_window=self)
        }

        # Mapping from worker names to the tab that handles their UI button state
        self._worker_tab_map = {
            'auto_clicker':   self.tabs['mouse'],
            'aimbot':         self.tabs['aimbot']
        }

    # ---------- UI updater thread ----------
    def _start_ui_updater(self) -> None :
        self._update_thread = threading.Thread(
            target=self._process_ui_updates,
            name="UI-Updater",
            daemon=True
        )
        self._update_thread.start()

    def _process_ui_updates(self) -> None :
        while self._running :
            try :
                update = self._ui_queue.get(timeout=0.5)
                self.root.after(0, self._apply_ui_update, update)
            except queue.Empty :
                continue
            except Exception as e :
                logging.error(f"UI update error: {e}")

    def _apply_ui_update(self, update: Dict[str, Any]) -> None :
        """Dispatch updates to the appropriate tab or status bar."""
        try :
            update_type = update.get('type')
            if update_type == 'status' :
                # Status messages always go to the General tab's status bar
                self.tabs['general'].set_status(update.get('message', ''))
            elif update_type == 'worker_state' :
                worker = update.get('worker')
                state = update.get('state')
                # Forward to the tab responsible for this worker
                tab = self._worker_tab_map.get(worker)
                if tab and hasattr(tab, 'update_worker_button'):
                    tab.update_worker_button(worker, state)
            elif update_type == 'overlay_visibility':
                overlay = update.get('overlay')
                visible = update.get('visible', False)
                # Notify the OverlaysTab to update button appearance
                if 'overlays' in self.tabs and hasattr(self.tabs['overlays'], 'set_overlay_button_state'):
                    self.tabs['overlays'].set_overlay_button_state(overlay, visible)
        except Exception as e :
            logging.error(f"Failed to apply UI update: {e}")

    # ---------- Overlay management ----------
    def toggle_stats_overlay(self) -> None:
        try:
            if not self.stats_overlay:
                self.stats_overlay = StatsOverlay(self.root, opacity=0.7)
            if self._stats_visible:
                self.stats_overlay.hide()
                self._stats_visible = False
                self._ui_queue.put_nowait({'type': 'overlay_visibility', 'overlay': 'stats', 'visible': False})
                self._ui_queue.put_nowait({'type': 'status', 'message': 'Stats overlay hidden'})
            else:
                self.stats_overlay.show()
                self._stats_visible = True
                self._ui_queue.put_nowait({'type': 'overlay_visibility', 'overlay': 'stats', 'visible': True})
                self._ui_queue.put_nowait({'type': 'status', 'message': 'Stats overlay shown'})
        except Exception as e:
            logging.error(f"Toggle stats overlay failed: {e}")
            self._ui_queue.put_nowait({'type': 'status', 'message': f'Error: {e}'})

    def toggle_screen_overlay(self) -> None:
        try:
            if not self.screen_overlay:
                self.screen_overlay = ScreenOverlay(self.root)
            if self._screen_visible:
                self.screen_overlay.hide()
                self._screen_visible = False
                self._ui_queue.put_nowait({'type': 'overlay_visibility', 'overlay': 'screen', 'visible': False})
                self._ui_queue.put_nowait({'type': 'status', 'message': 'Screen overlay hidden'})
            else:
                self.screen_overlay.show()
                self._screen_visible = True
                self._ui_queue.put_nowait({'type': 'overlay_visibility', 'overlay': 'screen', 'visible': True})
                self._ui_queue.put_nowait({'type': 'status', 'message': 'Screen overlay shown'})
        except Exception as e:
            logging.error(f"Toggle screen overlay failed: {e}")
            self._ui_queue.put_nowait({'type': 'status', 'message': f'Error: {e}'})

    def _start_overlay_updates(self) -> None:
        # Stats update every 1 second
        def update_stats():
            if self._stats_visible and self.stats_overlay:
                try:
                    data = self._collect_diagnostics()
                    self.stats_overlay.update(data)
                except Exception as e:
                    logging.error(f"Stats overlay update failed: {e}")
            self.root.after(1000, update_stats)

        # Screen overlay update at ~30 fps
        def update_screen():
            if self._screen_visible and self.screen_overlay and self.overlay_data:
                try:
                    drawing_data = self.overlay_data.get()
                    self.screen_overlay.update_drawings(drawing_data)
                except Exception as e:
                    logging.error(f"Screen overlay update failed: {e}")
            self.root.after(33, update_screen)

        self.root.after(1000, update_stats)
        self.root.after(33, update_screen)

    def _collect_diagnostics(self) -> Dict[str, Any]:
        data = {}
        try:
            data['workers'] = self.app.thread_manager.get_worker_stats()
            data['rm_running'] = self.app.resource_manager.running
            try:
                import psutil
                data['cpu'] = psutil.cpu_percent(interval=0.1)
                data['mem'] = psutil.virtual_memory().percent
            except ImportError:
                data['cpu'] = 'N/A'
                data['mem'] = 'N/A'
        except Exception as e:
            data['error'] = str(e)
        return data

    # ---------- Run & shutdown ----------
    def run(self) -> None :
        try :
            logging.info("Starting PewPy UI")
            self.root.mainloop()
        except Exception as e :
            logging.error(f"UI error: {e}")
            self.shutdown()

    def shutdown(self) -> None :
        logging.info("Shutting down PewPy UI")
        self._running = False
        # Destroy overlays if they exist
        if self.stats_overlay:
            self.stats_overlay.destroy()
        if self.screen_overlay:
            self.screen_overlay.destroy()
        self.app.stop_all()
        try :
            self.root.quit()
            self.root.destroy()
        except Exception as e :
            logging.debug(f"Window destruction: {e}")

# maintain backward compatibility
MainWindow = ModernMainWindow