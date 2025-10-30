#   src/ui/main_window.py
#   Modern CustomTkinter UI implementation for PewPy
#   Sleek, elegant interface with condensed controls

# ----- Imports ----- #
import customtkinter as ctk
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING :
    from core.app_manager import PewPyApplication

# ----- Main Class Application ----- #
class ModernMainWindow :
    # main application window using Tkinter

    def __init__(self, app: 'PewPyApplication') -> None :
        self.app = app
        self._setup_appearance()
        self.root = ctk.CTk()
        self.setup_ui()
        
    def _setup_appearance(self) -> None :
        # configure UI appearance settings
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
    def setup_ui(self) -> None : 
        # initialize and configure all UI components
        self.root.title("PewPy Control Panel")
        self.root.geometry("310x200")
        self.root.minsize(310, 200) # update this

        self._setup_layout()
        self._create_title()
        self._create_auto_clicker_section()
        self._create_overlay_section()
        self._create_status_bar()
        
    def _setup_layout(self) -> None :
        # configure grid layout for responsive design

        # 3 rows: title, controls (2 rows), status (bottom)
        self.root.grid_rowconfigure(0, weight=0)  # Title
        self.root.grid_rowconfigure(1, weight=1)  # Auto-clicker row
        self.root.grid_rowconfigure(2, weight=1)  # Overlay row  
        self.root.grid_rowconfigure(3, weight=0)  # Status bar
        
        # 2 columns: button + control
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        
    # ----- Title ----- #
    def _create_title(self) -> None :
        # create main application title
        self.title_label = ctk.CTkLabel(
            self.root,
            text="PewPy",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=0, column=0, columnspan=2, pady=(10, 5))
        
    # ----- 1st Row : Auto Clicker ----- #
    def _create_auto_clicker_section(self) -> None :
        # create auto-clicker controls section
        # toggle button - fixed width and centered
        self.auto_clicker_btn = ctk.CTkButton(
            self.root,
            text="Auto-Clicker", # OFF default
            command=self.toggle_auto_clicker,
            width=140,
            height=35,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#dc3545",
            hover_color="#c82333"
        )
        self.auto_clicker_btn.grid(row=1, column=0, padx=(20, 10), pady=5, sticky="ew")
        
        # interval controls
        self._create_interval_controls()
        
    def _create_interval_controls(self) -> None :
        # create interval input controls
        self.interval_var = ctk.StringVar(value="Interval (sec)")
        self.interval_spinner = ctk.CTkEntry(
            self.root,
            textvariable=self.interval_var,
            width=140,
            height=35,
            justify="center",
            font=ctk.CTkFont(size=12),
            placeholder_text="Interval (sec)"
        )
        self.interval_spinner.grid(row=1, column=1, padx=(10, 20), pady=5, sticky="ew")
        
        self._bind_interval_events()
    
    def toggle_auto_clicker(self) -> None :
        # toggle auto-clicker state with visual feedback
        try :
            if self.app.is_worker_running('auto_clicker'):
                self._stop_auto_clicker()
            else :
                self._start_auto_clicker()
        except Exception as e :
            logging.error(f"Toggle auto-clicker error: {e}")
            self._show_error(f"Toggle failed: {e}")
    
    def _stop_auto_clicker(self) -> None :
        # stop auto-clicker and update UI
        self.app.stop_worker('auto_clicker')
        self.auto_clicker_btn.configure(
            text="Auto-Clicker", # OFF
            fg_color="#dc3545",
            hover_color="#c82333"
        )
        self.status_var.set("Auto-clicker: STOPPED")
        logging.info("Auto-clicker disabled via UI")
    
    def _start_auto_clicker(self) -> None :
        # start auto-clicker and update UI
        if self.app.start_worker('auto_clicker') :
            self.auto_clicker_btn.configure(
                text="Auto-Clicker", # ON 
                fg_color="#28a745",
                hover_color="#218838"
            )
            self.status_var.set("Auto-clicker: RUNNING")
            logging.info("Auto-clicker enabled via UI")
        else :
            self._show_error("Failed to start auto-clicker")
    
    # ----- 2nd Row : Overlay ----- #
    def _create_overlay_section(self) -> None :
        # create overlay controls section
        # overlay toggle button - same size as auto-clicker
        self.overlay_btn = ctk.CTkButton(
            self.root,
            text="Overlay: OFF", # OFF
            command=self.toggle_overlay,
            width=140,
            height=35,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6c757d",  # Gray color to indicate disabled/placeholder
            hover_color="#5a6268",
            state="disabled"  # Disable until overlay worker is implemented
        )
        self.overlay_btn.grid(row=2, column=0, padx=(20, 10), pady=5, sticky="ew")
        
    def toggle_overlay(self) -> None :
        # toggle overlay state
        # currently disabled
        logging.info("Overlay functionality not yet implemented")
        self.status_var.set("Overlay: Feature coming soon")

    # ----- bottom row : status bar ----- #
    def _create_status_bar(self) -> None :
        # create status bar display
        self.status_var = ctk.StringVar(value="Ready - System Online")
        self.status_bar = ctk.CTkLabel(
            self.root,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.status_bar.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 10))

    # ----- Helper Methods ----- #
    def _bind_interval_events(self) -> None :
        # bind validation events to interval input
        self.interval_spinner.bind("<FocusOut>", self._validate_and_update_interval)
        self.interval_spinner.bind("<Return>", self._validate_and_update_interval)
        self.interval_spinner.bind("<KeyRelease>", self._validate_interval_input)

    def _validate_interval_input(self, event=None) -> None :
        # validate interval input in real-time
        try :
            value = self.interval_var.get().strip()
            if value and value != ".":
                float(value)
        except ValueError :
            self._clean_interval_input()
    
    def _clean_interval_input(self) -> None :
        # remove invalid characters from interval input
        current = self.interval_var.get()
        cleaned = ''.join(c for c in current if c in '0123456789.')

        if cleaned.count('.') > 1 :
            parts = cleaned.split('.')
            cleaned = parts[0] + '.' + ''.join(parts[1:])
        self.interval_var.set(cleaned)

    def _validate_and_update_interval(self, event=None) -> None :
        # validate and update auto-clicker interval
        try :
            value = self.interval_var.get().strip()
            if not value :
                value = "0.1"
                self.interval_var.set(value)

            interval = float(value)
            interval = self._clamp_interval(interval)
            
            if self._can_update_interval() :
                self.app.workers['auto_clicker'].set_interval(interval)
                logging.info(f"Auto-clicker interval updated to {interval}s")
                self._update_interval_status(interval)
                
        except ValueError as e :
            logging.error(f"Invalid interval value: {e}")
            self._reset_interval_default()

    def _clamp_interval(self, interval: float) -> float :
        # clamp interval to valid range and update display
        if interval < 0.01 :
            self.interval_var.set("0.01")
            return 0.01
        elif interval > 10.0 :
            self.interval_var.set("10.0")
            return 10.0
        
        return interval

    def _can_update_interval(self) -> bool :
        # check if interval can be updated
        return (hasattr(self.app.workers['auto_clicker'], 'set_interval') and 
                self.app.workers['auto_clicker'] is not None)

    def _update_interval_status(self, interval: float) -> None :
        # update status display with current interval
        if self.app.is_worker_running('auto_clicker') :
            self.status_var.set(f"Auto-clicker: {interval}s interval")

    def _reset_interval_default(self) -> None :
        # reset interval to default value
        self.interval_var.set("0.1")
        if self._can_update_interval() :
            self.app.workers['auto_clicker'].set_interval(0.1)

    def _show_error(self, message: str) -> None :
        # display error message in status bar
        self.status_var.set(f"ERROR: {message}")
        logging.error(f"UI Error: {message}")
    
    def run(self) -> None :
        # start the UI main loop
        try :
            logging.info("Starting PewPy Modern UI")
            self.root.mainloop()
        except (KeyboardInterrupt, Exception) as e :
            logging.error(f"UI error: {e}")
            self.shutdown()
    
    def shutdown(self) -> None :
        # perform clean shutdown of application
        logging.info("Shutting down PewPy Modern UI")
        self.app.stop_all()
        try :
            self.root.quit()
            self.root.destroy()
        except Exception as e :
            logging.debug(f"Window destruction error: {e}")

# maintain backward compatibility
MainWindow = ModernMainWindow