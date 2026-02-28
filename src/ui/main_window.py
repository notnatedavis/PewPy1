#   src/ui/main_window.py
#   Modern CustomTkinter UI for PewPy - Fixed imports

# ----- Imports ----- #
import threading
import time
import queue
import customtkinter as ctk
import logging
from typing import Optional, Dict, Any

# ----- Main Class ----- #
class ModernMainWindow :
    # Main application window
    
    def __init__(self, app) -> None :
        self.app = app
        
        # setup appearance
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        # create main window
        self.root = ctk.CTk()
        self.root.title("PewPy Control Panel")
        self.root.geometry("310x200")
        self.root.minsize(310, 200)
        
        # thread-safe communication
        self._ui_queue = queue.Queue(maxsize=50)
        self._update_thread: Optional[threading.Thread] = None
        self._running = True
        
        # setup UI
        self._setup_layout()
        self._create_widgets()
        
        # start UI updater
        self._start_ui_updater()
        
        # handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
    
    def _setup_layout(self) -> None :
        # configure grid layout
        # 4 rows
        self.root.grid_rowconfigure(0, weight=0)  # Title
        self.root.grid_rowconfigure(1, weight=1)  # Auto-clicker
        self.root.grid_rowconfigure(2, weight=1)  # Overlay
        self.root.grid_rowconfigure(3, weight=0)  # Status
        
        # 2 columns
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
    
    def _create_widgets(self) -> None :
        # create all UI widgets
        # Title
        self.title_label = ctk.CTkLabel(
            self.root,
            text="PewPy",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=0, column=0, columnspan=2, pady=(10, 5))
        
        # auto-clicker section
        self._create_auto_clicker_section()
        
        # overlay section
        self._create_overlay_section()
        
        # status bar
        self._create_status_bar()
    
    def _create_auto_clicker_section(self) -> None :
        # create auto-clicker controls
        # toggle button
        self.auto_clicker_btn = ctk.CTkButton(
            self.root,
            text="Auto-Clicker: OFF",
            command=self.toggle_auto_clicker,
            width=140,
            height=35,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#dc3545",
            hover_color="#c82333"
        )
        self.auto_clicker_btn.grid(row=1, column=0, padx=(20, 10), pady=5, sticky="ew")
        
        # interval input
        self.interval_var = ctk.StringVar(value="0.1")
        self.interval_entry = ctk.CTkEntry(
            self.root,
            textvariable=self.interval_var,
            width=140,
            height=35,
            justify="center",
            font=ctk.CTkFont(size=12),
            placeholder_text="Interval (sec)"
        )
        self.interval_entry.grid(row=1, column=1, padx=(10, 20), pady=5, sticky="ew")
        
        # bind events
        self.interval_entry.bind("<FocusOut>", self._update_interval)
        self.interval_entry.bind("<Return>", self._update_interval)
    
    def _create_overlay_section(self) -> None :
        # create overlay controls
        self.overlay_btn = ctk.CTkButton(
            self.root,
            text="Overlay: OFF",
            command=self.toggle_overlay,
            width=140,
            height=35,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        self.overlay_btn.grid(row=2, column=0, padx=(20, 10), pady=5, sticky="ew")
    
    def _create_status_bar(self) -> None :
        # create status bar
        self.status_var = ctk.StringVar(value="Ready - PewPy Online")
        self.status_bar = ctk.CTkLabel(
            self.root,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.status_bar.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 10))
    
    def _start_ui_updater(self) -> None :
        # start UI update thread
        self._update_thread = threading.Thread(
            target=self._process_ui_updates,
            name="UI-Updater",
            daemon=True
        )
        self._update_thread.start()
    
    def _process_ui_updates(self) -> None :
        # process UI updates from queue
        while self._running :
            try :
                update = self._ui_queue.get(timeout=0.5)
                self.root.after(0, self._apply_ui_update, update)
            except queue.Empty :
                continue
            except Exception as e :
                logging.error(f"UI update error: {e}")
    
    def _apply_ui_update(self, update: Dict[str, Any]) -> None :
        # apply UI update on main thread
        try :
            update_type = update.get('type')
            
            if update_type == 'status' :
                self.status_var.set(update.get('message', ''))
            elif update_type == 'worker_state' :
                worker = update.get('worker')
                state = update.get('state')
                self._update_worker_button(worker, state)
                
        except Exception as e :
            logging.error(f"Failed to apply UI update: {e}")
    
    def toggle_auto_clicker(self) -> None :
        # toggle auto-clicker
        try :
            worker_name = 'auto_clicker'
            
            # immediate feedback
            self._ui_queue.put_nowait({
                'type': 'status',
                'message': 'Processing auto-clicker...'
            })
            
            if self.app.is_worker_running(worker_name) :
                # stop worker
                success = self.app.stop_worker(worker_name)
                if success :
                    self._ui_queue.put_nowait({
                        'type': 'worker_state',
                        'worker': 'auto_clicker',
                        'state': False
                    })
                    self._ui_queue.put_nowait({
                        'type': 'status',
                        'message': 'Auto-clicker: STOPPED'
                    })
                else :
                    self._ui_queue.put_nowait({
                        'type': 'status',
                        'message': 'Error: Failed to stop auto-clicker'
                    })
            else :
                # start worker
                success = self.app.start_worker(worker_name)
                if success :
                    self._ui_queue.put_nowait({
                        'type': 'worker_state',
                        'worker': 'auto_clicker',
                        'state': True
                    })
                    interval = self.interval_var.get()
                    self._ui_queue.put_nowait({
                        'type': 'status',
                        'message': f'Auto-clicker: RUNNING ({interval}s interval)'
                    })
                else :
                    self._ui_queue.put_nowait({
                        'type': 'status',
                        'message': 'Error: Failed to start auto-clicker'
                    })
                    
        except Exception as e :
            logging.error(f"Toggle auto-clicker error: {e}")
            self._ui_queue.put_nowait({
                'type': 'status',
                'message': f'Error: {str(e)[:50]}'
            })
    
    def toggle_overlay(self) -> None :
        # toggle overlay
        try :
            worker_name = 'overlay'
            
            self._ui_queue.put_nowait({
                'type': 'status',
                'message': 'Processing overlay...'
            })
            
            if self.app.is_worker_running(worker_name) :
                # stop overlay
                success = self.app.stop_worker(worker_name)
                if success :
                    self._ui_queue.put_nowait({
                        'type': 'worker_state',
                        'worker': 'overlay',
                        'state': False
                    })
                    self._ui_queue.put_nowait({
                        'type': 'status',
                        'message': 'Overlay: STOPPED'
                    })
                else :
                    self._ui_queue.put_nowait({
                        'type': 'status',
                        'message': 'Error: Failed to stop overlay'
                    })
            else :
                # start overlay
                success = self.app.start_worker(worker_name)
                if success :
                    self._ui_queue.put_nowait({
                        'type': 'worker_state',
                        'worker': 'overlay',
                        'state': True
                    })
                    self._ui_queue.put_nowait({
                        'type': 'status',
                        'message': 'Overlay: RUNNING'
                    })
                else :
                    self._ui_queue.put_nowait({
                        'type': 'status',
                        'message': 'Error: Failed to start overlay'
                    })
                    
        except Exception as e :
            logging.error(f"Toggle overlay error: {e}")
            self._ui_queue.put_nowait({
                'type': 'status',
                'message': f'Error: {str(e)[:50]}'
            })
    
    def _update_worker_button(self, worker: str, is_running: bool) -> None:
        # update button appearance based on worker state
        try :
            if worker == 'auto_clicker' :
                if is_running :
                    self.auto_clicker_btn.configure(
                        text="Auto-Clicker: ON",
                        fg_color="#28a745",
                        hover_color="#218838"
                    )
                else :
                    self.auto_clicker_btn.configure(
                        text="Auto-Clicker: OFF",
                        fg_color="#dc3545",
                        hover_color="#c82333"
                    )
            elif worker == 'overlay' :
                if is_running :
                    self.overlay_btn.configure(
                        text="Overlay: ON",
                        fg_color="#28a745",
                        hover_color="#218838"
                    )
                else :
                    self.overlay_btn.configure(
                        text="Overlay: OFF",
                        fg_color="#6c757d",
                        hover_color="#5a6268"
                    )
                    
        except Exception as e :
            logging.error(f"Failed to update button: {e}")
    
    def _update_interval(self, event=None) -> None :
        # update auto-clicker interval
        try :
            value = self.interval_var.get().strip()
            if not value :
                value = "0.1"
                self.interval_var.set(value)
            
            interval = float(value)
            interval = max(0.01, min(10.0, interval))
            
            # update worker if running
            if self.app.is_worker_running('auto_clicker') :
                worker = self.app.workers['auto_clicker']
                if hasattr(worker, 'set_interval') :
                    worker.set_interval(interval)
                    self._ui_queue.put_nowait({
                        'type': 'status',
                        'message': f'Interval updated: {interval}s'
                    })
                    logging.info(f"Auto-clicker interval updated to {interval}s")
            
        except ValueError as e :
            logging.error(f"Invalid interval: {e}")
            self.interval_var.set("0.1")
            self._ui_queue.put_nowait({
                'type': 'status',
                'message': 'Invalid interval, reset to 0.1s'
            })
    
    def run(self) -> None :
        # start the UI main loop
        try :
            logging.info("Starting PewPy UI")
            self.root.mainloop()
        except Exception as e :
            logging.error(f"UI error: {e}")
            self.shutdown()
    
    def shutdown(self) -> None :
        # clean shutdown
        logging.info("Shutting down PewPy UI")
        self._running = False
        
        # stop all workers
        self.app.stop_all()
        
        # destroy window
        try :
            self.root.quit()
            self.root.destroy()
        except Exception as e :
            logging.debug(f"Window destruction: {e}")
    
    def __del__(self) -> None :
        # destructor
        self.shutdown()

# maintain backward compatibility
MainWindow = ModernMainWindow