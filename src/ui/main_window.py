#   src/ui/main_window.py
#   Tkinter UI implementation main window for PewPy

# ----- Imports ----- #
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import TYPE_CHECKING
if TYPE_CHECKING :
    from core.app_manager import PewPyApplication

# ----- Main Class Application ----- #
class MainWindow :
    # main application window using Tkinter

    def __init__(self, app: 'PewPyApplication') :
        self.app = app
        self.root = tk.Tk()
        self.setup_ui()
        
    def setup_ui(self) :
        # Setup the user interface
        self.root.title("PewPy Control Panel")
        self.root.geometry("400x300")
        self.root.resizable(True, True)
        
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="PewPy Function Controller", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Auto-clicker section
        self.setup_auto_clicker_section(main_frame, row=1)
        
        # Add more function sections here as needed
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=10, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(20, 0))
        
    def setup_auto_clicker_section(self, parent, row: int) :
        # Setup auto-clicker controls
        # Section label
        ttk.Label(parent, text="Auto Clicker", font=('Arial', 12, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
            
        # Toggle button
        self.auto_clicker_btn = ttk.Button(
            parent, 
            text="Enable Auto Clicker", 
            command=self.toggle_auto_clicker
        )
        self.auto_clicker_btn.grid(row=row+1, column=0, sticky=tk.W, pady=5)
        
        # Interval control
        ttk.Label(parent, text="Interval (s):").grid(row=row+2, column=0, sticky=tk.W)
        self.interval_var = tk.DoubleVar(value=0.1)
        interval_spin = ttk.Spinbox(
            parent, 
            from_=0.01, 
            to=10.0, 
            increment=0.05,
            textvariable=self.interval_var,
            width=8
        )
        interval_spin.grid(row=row+2, column=1, sticky=tk.W, padx=(5, 0))
        
    def toggle_auto_clicker(self) :
        # Toggle auto-clicker on/off
        if self.app.is_worker_running('auto_clicker') :
            # Stop auto-clicker
            self.app.stop_worker('auto_clicker')
            self.auto_clicker_btn.config(text="Enable Auto Clicker")
            self.status_var.set("Auto-clicker stopped")
            logging.info("Auto-clicker disabled via UI")
        else :
            # Start auto-clicker
            if self.app.start_worker('auto_clicker') :
                self.auto_clicker_btn.config(text="Disable Auto Clicker")
                self.status_var.set("Auto-clicker running")
                logging.info("Auto-clicker enabled via UI")
            else:
                messagebox.showerror("Error", "Failed to start auto-clicker")
                
    def run(self) :
        # Start the UI main loop
        try :
            self.root.mainloop()
        except KeyboardInterrupt:
            self.shutdown()
        except Exception as e :
            logging.error(f"UI error: {e}")
            self.shutdown()
            
    def shutdown(self) :
        # Cleanup and shutdown
        logging.info("Shutting down application...")
        self.app.stop_all()
        self.root.quit()
        self.root.destroy()