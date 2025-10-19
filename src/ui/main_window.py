#   src/ui/main_window.py
#   Modern CustomTkinter UI implementation for PewPy
#   Sleek, elegant interface with condensed controls

# ----- Imports ----- #
import customtkinter as ctk
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.app_manager import PewPyApplication
# ----- Main Class Application ----- #
class ModernMainWindow:
    # main application window using Tkinter

    def __init__(self, app: 'PewPyApplication'):
        self.app = app
        
        # Configure CustomTkinter appearance
        ctk.set_appearance_mode("Dark")  # Options: "Dark", "Light", "System"
        ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"
        
        # Create main window
        self.root = ctk.CTk()
        self.setup_ui()
        
    def setup_ui(self):
        # Setup the modern user interface
        self.root.title("PewPy Control Panel")
        self.root.geometry("380x200")  # More compact size
        self.root.minsize(350, 180)
        
        # Configure grid layout (2x2 for responsive design)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        
        # Main title
        self.title_label = ctk.CTkLabel(
            self.root,
            text="PewPy",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=0, column=0, columnspan=2, pady=(20, 30))
        
        # Auto-clicker section - condensed into two boxes
        self.setup_auto_clicker_section(row=1)
        
        # Status bar
        self.status_var = ctk.StringVar(value="Ready - System Online")
        self.status_bar = ctk.CTkLabel(
            self.root,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 10))
        
    def setup_auto_clicker_section(self, row: int):
        # Setup condensed auto-clicker controls - just toggle and interval
        
        # Auto-clicker toggle button (Left side)
        self.auto_clicker_btn = ctk.CTkButton(
            self.root,
            text="Auto-Clicker: OFF",
            command=self.toggle_auto_clicker,
            width=160,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#dc3545",  # Red color for off state
            hover_color="#c82333"
        )
        self.auto_clicker_btn.grid(row=row, column=0, padx=(20, 10), pady=10, sticky="ew")
        
        # Interval control (Right side)
        interval_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        interval_frame.grid(row=row, column=1, padx=(10, 20), pady=10, sticky="ew")
        
        # Interval label
        ctk.CTkLabel(
            interval_frame,
            text="Click Interval (s):",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", pady=(0, 5))
        
        # Interval spinner with button-like appearance
        self.interval_var = ctk.DoubleVar(value=0.1)
        self.interval_spinner = ctk.CTkEntry(
            interval_frame,
            textvariable=self.interval_var,
            width=120,
            height=35,
            justify="center",
            font=ctk.CTkFont(size=12)
        )
        self.interval_spinner.pack(anchor="w")
        
        # Bind interval change event
        self.interval_spinner.bind("<FocusOut>", self.update_auto_clicker_interval)
        self.interval_spinner.bind("<Return>", self.update_auto_clicker_interval)
        
    def toggle_auto_clicker(self):
        # Toggle auto-clicker on/off with visual feedback
        try:
            if self.app.is_worker_running('auto_clicker'):
                # Stop auto-clicker
                self.app.stop_worker('auto_clicker')
                self.auto_clicker_btn.configure(
                    text="Auto-Clicker: OFF",
                    fg_color="#dc3545",  # Red
                    hover_color="#c82333"
                )
                self.status_var.set("Auto-clicker: STOPPED")
                logging.info("Auto-clicker disabled via UI")
            else:
                # Start auto-clicker
                if self.app.start_worker('auto_clicker'):
                    self.auto_clicker_btn.configure(
                        text="Auto-Clicker: ON", 
                        fg_color="#28a745",  # Green
                        hover_color="#218838"
                    )
                    self.status_var.set("Auto-clicker: RUNNING")
                    logging.info("Auto-clicker enabled via UI")
                else:
                    self.show_error("Failed to start auto-clicker")
                    
        except Exception as e:
            logging.error(f"Toggle auto-clicker error: {e}")
            self.show_error(f"Toggle failed: {e}")
    
    def update_auto_clicker_interval(self, event=None):
        # Update auto-clicker interval in real-time"""
        try:
            interval = self.interval_var.get()
            # Validate interval
            if interval < 0.01:
                interval = 0.01
                self.interval_var.set(0.01)
            elif interval > 10.0:
                interval = 10.0
                self.interval_var.set(10.0)
            
            # Update worker interval if available
            if hasattr(self.app.workers['auto_clicker'], 'set_interval'):
                self.app.workers['auto_clicker'].set_interval(interval)
                logging.info(f"Auto-clicker interval updated to {interval}s")
                
                # Update status if running
                if self.app.is_worker_running('auto_clicker'):
                    self.status_var.set(f"Auto-clicker: {interval}s interval")
                    
        except Exception as e:
            logging.error(f"Update interval error: {e}")
    
    def show_error(self, message: str):
        # Show error message with modern dialog
        # For now, just update status - you could use CTkMessagebox for better UX
        self.status_var.set(f"ERROR: {message}")
        logging.error(f"UI Error: {message}")
    
    def run(self):
        # Start the UI main loop
        try:
            logging.info("Starting PewPy Modern UI")
            self.root.mainloop()
        except KeyboardInterrupt:
            self.shutdown()
        except Exception as e:
            logging.error(f"UI error: {e}")
            self.shutdown()
    
    def shutdown(self):
        # clean shutdown
        logging.info("Shutting down PewPy Modern UI")
        self.app.stop_all()
        try:
            self.root.quit()
            self.root.destroy()
        except Exception as e:
            logging.debug(f"Window destruction error: {e}")

# Maintain backward compatibility
MainWindow = ModernMainWindow