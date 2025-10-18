#   src/main.py
#   PewPy Main Application
#   High-performance Python aimbot with modern concurrency

# ----- Imports ----- #
import sys
import os
import signal
import logging
from pathlib import Path

# ----- Setup ----- #
# Add the project root to Python path to allow proper imports
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

# import modules
from src.core import FramePipeline, PerformanceMonitor, ResourceManager, AdaptiveTaskDispatcher
from src.workers import HighPerformanceScreenCapturer, GPUTargetDetector, LowLatencyInputController, SafetyMonitor
from src.ui import ConfigManager, OverlayWindow, UIHotkeyHandler

# ----- main Class ----- #
class PewPyApplication :
    # Main application class coordinating all components
    def __init__(self) :
        self.running = False
        self.components = {}
        
        # Initialize configuration
        self.config = ConfigManager()
        
        # Initialize core components
        self.performance = PerformanceMonitor()
        self.resources = ResourceManager()
        self.dispatcher = AdaptiveTaskDispatcher()
        self.pipeline = FramePipeline()
        
        # Initialize workers
        self.capturer = HighPerformanceScreenCapturer(
            region=self.config.get('default', 'capture.region')
        )
        self.detector = GPUTargetDetector(
            self.config.get('default', 'detection.lower_hsv'),
            self.config.get('default', 'detection.upper_hsv')
        )
        self.input_controller = LowLatencyInputController()
        self.safety_monitor = SafetyMonitor()
        
        # Initialize UI
        self.overlay = OverlayWindow(self.config, self.performance)
        self.ui_hotkeys = UIHotkeyHandler()
        
        # Register components for easy access
        self.components = {
            'config': self.config,
            'performance': self.performance,
            'resources': self.resources,
            'dispatcher': self.dispatcher,
            'pipeline': self.pipeline,
            'capturer': self.capturer,
            'detector': self.detector,
            'input_controller': self.input_controller,
            'safety_monitor': self.safety_monitor,
            'overlay': self.overlay,
            'ui_hotkeys': self.ui_hotkeys
        }
        
        self._setup_signal_handlers()
        self._setup_callbacks()
    
    def _setup_signal_handlers(self) :
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_callbacks(self) :
        # Setup inter-component callbacks
        # Safety monitor callbacks
        self.safety_monitor.register_toggle_callback(self._on_aimbot_toggle)
        self.safety_monitor.register_emergency_callback(self._on_emergency_stop)
        
        # UI hotkeys
        self.ui_hotkeys.register_hotkey('<ctrl>+<alt>+o', self._toggle_overlay, "Toggle Overlay")
        self.ui_hotkeys.register_hotkey('<ctrl>+<alt>+p', self._toggle_performance_mode, "Toggle Performance Mode")
        
        # Config change callbacks
        self.config.add_callback(self._on_config_changed)
    
    def _on_aimbot_toggle(self, enabled: bool) :
        # Handle aimbot toggle
        logging.info(f"Aimbot {'enabled' if enabled else 'disabled'}")
        # Update UI or other components as needed
    
    def _on_emergency_stop(self) :
        # Handle emergency stop
        logging.warning("Emergency stop activated")
        # Stop all processing immediately
    
    def _toggle_overlay(self) :
        # Toggle overlay visibility
        if self.overlay.visible:
            self.overlay.hide()
        else:
            self.overlay.show()
    
    def _toggle_performance_mode(self) :
        # Toggle performance mode
        current_mode = self.config.get('performance', 'performance.mode', 'balanced')
        modes = ['balanced', 'performance', 'power_saving']
        next_mode = modes[(modes.index(current_mode) + 1) % len(modes)]
        self.config.set('performance', 'performance.mode', next_mode)
        logging.info(f"Performance mode changed to: {next_mode}")
    
    def _on_config_changed(self, config_name: str, data: dict) :
        # Handle configuration changes
        logging.info(f"Configuration '{config_name}' updated")
        # Apply configuration changes to relevant components
    
    def _signal_handler(self, signum, frame) :
        # Handle shutdown signals
        logging.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def initialize(self) -> bool :
        # Initialize all application components
        try:
            logging.info("Initializing PewPy Application...")
            
            # Start resource monitoring
            self.resources.start_monitoring()
            
            # Start safety monitoring
            self.safety_monitor.start()
            
            # Start UI hotkeys
            self.ui_hotkeys.start()
            
            # Start frame capture
            self.capturer.start_capture_loop()
            
            # Start overlay
            self.overlay.start_updates()
            
            # Start configuration watching
            self.config.start_watching()
            
            # Apply Python 3.13 optimizations
            self.performance.apply_optimizations()
            
            logging.info("PewPy Application initialized successfully")
            return True
            
        except Exception as e : 
            logging.error(f"Failed to initialize application: {e}")
            return False
    
    def run(self) :
        # Main application loop
        if not self.initialize():
            return
        
        self.running = True
        logging.info("Starting PewPy main loop...")
        
        try :
            while self.running :
                # Main application logic here
                # This would typically coordinate between components
                
                # Check safety state
                if not self.safety_monitor.is_safe() :
                    logging.warning("Safety violation detected, stopping...")
                    break
                
                # Process frames if aimbot is enabled
                if self.safety_monitor.is_aimbot_enabled() :
                    self._process_frame()
                
                # Brief sleep to prevent CPU spinning
                self.performance.sleep_optimized(0.001)  # 1ms
                
        except KeyboardInterrupt :
            logging.info("Keyboard interrupt received")
        except Exception as e :
            logging.error(f"Main loop error: {e}")
        finally :
            self.stop()
    
    def _process_frame(self) :
        # Process a single frame for target detection
        try :
            # Get latest frame
            frame = self.capturer.get_latest_frame()
            if frame is None :
                return 
            
            # Detect targets
            target_position = self.detector.detect_targets(frame)
            
            # Move mouse if target found
            if target_position and target_position != (-1, -1):
                self.input_controller.move_mouse_smooth(
                    target_position[0], 
                    target_position[1]
                )
                
        except Exception as e :
            logging.error(f"Frame processing error: {e}")
    
    def stop(self) :
        # Stop the application and cleanup resources
        if not self.running :
            return
        
        self.running = False
        logging.info("Shutting down PewPy Application...")
        
        # Stop components in reverse initialization order
        self.config.stop_watching()
        self.overlay.stop_updates()
        self.capturer.running = False  # Stop capture loop
        self.ui_hotkeys.stop()
        self.safety_monitor.stop()
        self.resources.stop_monitoring()
        
        logging.info("PewPy Application shutdown complete")

def setup_logging() :
    # Setup application logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('pewpy.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main() :
    # Main entry point
    setup_logging()
    
    app = PewPyApplication()
    
    try :
        app.run()
    except Exception as e :
        logging.critical(f"Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__" :
    sys.exit(main())