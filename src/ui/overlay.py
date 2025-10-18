#   src/ui/overlay.py
#   Overlay window for real-time statistics and control
#   Uses tkinter for simplicity and compatibility

# ----- Imports ----- #
import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Dict, Any, Optional
from ..core.performance_monitor import PerformanceMonitor

# ----- main Class ----- #
class OverlayWindow :
    # Configurable overlay window showing real-time performance stats
    def __init__(self, config_manager, performance_monitor: PerformanceMonitor) :
        self.config_manager = config_manager
        self.performance = performance_monitor
        self.root = None
        self.visible = False
        self.update_thread = None
        self.updating = False
        
        # UI elements
        self.stats_labels = {}
        self.control_buttons = {}
        
        self._setup_window()
    
    def _setup_window(self) :
        # Initialize the overlay window
        self.root = tk.Tk()
        self.root.title("PewPy Overlay")
        self.root.geometry("300x400")
        self.root.attributes('-topmost', True)  # Always on top
        self.root.configure(bg='#2b2b2b')  # Dark theme
        
        # Make window semi-transparent
        self.root.attributes('-alpha', 0.9)
        
        self._create_widgets()
        
        # Load initial visibility state
        self.visible = self.config_manager.get('default', 'ui.overlay_enabled', True)
        if not self.visible :
            self.root.withdraw()
    
    def _create_widgets(self) :
        # Create overlay UI elements
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = tk.Label(
            main_frame, 
            text="PewPy Stats", 
            font=('Arial', 14, 'bold'),
            fg='white',
            bg='#2b2b2b'
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Stats section
        stats_frame = ttk.LabelFrame(main_frame, text="Performance", padding="5")
        stats_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Performance stats
        stats = [
            ("FPS", "fps"),
            ("Frame Time", "frame_time_ms"),
            ("Detection Time", "detection_time_ms"),
            ("CPU Usage", "cpu_usage"),
            ("Memory Usage", "memory_usage")
        ]
        
        for i, (label, key) in enumerate(stats) :
            # Label
            tk.Label(
                stats_frame,
                text=f"{label}:",
                fg='lightgray',
                bg='#2b2b2b'
            ).grid(row=i, column=0, sticky=tk.W, padx=(0, 5))
            
            # Value
            value_label = tk.Label(
                stats_frame,
                text="0",
                fg='white',
                bg='#2b2b2b',
                font=('Arial', 10, 'bold')
            )
            value_label.grid(row=i, column=1, sticky=tk.W)
            self.stats_labels[key] = value_label
        
        # Control buttons
        controls_frame = ttk.LabelFrame(main_frame, text="Controls", padding="5")
        controls_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # Toggle overlay button
        toggle_btn = ttk.Button(
            controls_frame,
            text="Hide Overlay",
            command=self.toggle_visibility
        )
        toggle_btn.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)
        self.control_buttons['toggle'] = toggle_btn
        
        # Config buttons
        ttk.Button(
            controls_frame,
            text="Performance Mode",
            command=self._toggle_performance_mode
        ).grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        
        ttk.Button(
            controls_frame,
            text="Reset Stats",
            command=self.performance.reset_stats
        ).grid(row=2, column=0, sticky=(tk.W, tk.E), pady=2)
        
        # Configure grid weights for responsiveness
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
    
    def show(self) :
        # Show the overlay window
        if self.root:
            self.root.deiconify()
            self.visible = True
            self.config_manager.set('default', 'ui.overlay_enabled', True)
    
    def hide(self) :
        # Hide the overlay window
        if self.root:
            self.root.withdraw()
            self.visible = False
            self.config_manager.set('default', 'ui.overlay_enabled', False)
    
    def toggle_visibility(self) :
        # Toggle overlay visibility
        if self.visible :
            self.hide()
            self.control_buttons['toggle'].configure(text="Show Overlay")
        else :
            self.show()
            self.control_buttons['toggle'].configure(text="Hide Overlay")
    
    def _toggle_performance_mode(self) :
        # Toggle between performance modes
        current_mode = self.config_manager.get('performance', 'performance.mode', 'balanced')
        modes = ['balanced', 'performance', 'power_saving']
        next_mode = modes[(modes.index(current_mode) + 1) % len(modes)]
        
        self.config_manager.set('performance', 'performance.mode', next_mode)
        print(f"Switched to {next_mode} mode")
    
    def start_updates(self):
        # Start periodic UI updates
        self.updating = True
        self.update_thread = threading.Thread(target=self._update_worker)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        # Also start the tkinter main loop in a separate thread
        threading.Thread(target=self.root.mainloop, daemon=True).start()
    
    def stop_updates(self) :
        # Stop UI updates
        self.updating = False
        if self.update_thread :
            self.update_thread.join(timeout=1.0)
        if self.root :
            self.root.quit()
    
    def _update_worker(self) :
        # Background worker for updating stats
        while self.updating and self.root :
            try :
                stats = self.performance.get_stats()
                
                # Update UI in thread-safe manner
                self.root.after(0, self._update_stats_display, stats)
                time.sleep(0.5)  # Update every 500ms
            except Exception as e :
                print(f"Overlay update error: {e}")
                time.sleep(1.0)
    
    def _update_stats_display(self, stats: Dict[str, Any]) :
        # Update the stats display (called in main thread)
        try:
            # Update FPS
            if 'fps' in stats and 'fps' in self.stats_labels :
                self.stats_labels['fps'].configure(text=f"{stats['fps']:.1f}")
            
            # Update frame time
            if 'average_frame_time' in stats and 'frame_time_ms' in self.stats_labels :
                self.stats_labels['frame_time_ms'].configure(
                    text=f"{stats['average_frame_time']:.2f}ms"
                )
            
            # Update detection time
            if 'average_detection_time' in stats and 'detection_time_ms' in self.stats_labels :
                self.stats_labels['detection_time_ms'].configure(
                    text=f"{stats['average_detection_time']:.2f}ms"
                )
            
            # Update CPU usage
            if 'cpu_usage' in stats and 'cpu_usage' in self.stats_labels :
                self.stats_labels['cpu_usage'].configure(
                    text=f"{stats['cpu_usage']:.1f}%"
                )
            
            # Update memory usage
            if 'memory_usage_mb' in stats and 'memory_usage' in self.stats_labels :
                self.stats_labels['memory_usage'].configure(
                    text=f"{stats['memory_usage_mb']:.1f}MB"
                )
                
        except Exception as e :
            print(f"Stats display update error: {e}")