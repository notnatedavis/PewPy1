#   src/core/frame_pipeline.py
#   Frame processing pipeline for high-throughput image processing

# ----- Imports ----- #
import threading
import queue
import time
from typing import Optional, Callable
import cv2
import numpy as np
from core.performance_monitor import PerformanceMonitor

# ----- main Class ----- #
class FramePipeline :
    # Optimized frame processing pipeline with parallel stages

    def __init__(self, max_queue_size: int = 10) :
        self.performance = PerformanceMonitor()
        self.frame_queue = queue.Queue(maxsize=max_queue_size)
        self.processed_queue = queue.Queue(maxsize=max_queue_size)
        self.running = False
        self.processor_thread = None
        self.consumer_thread = None
        
        # Pipeline stages
        self.preprocessors = []
        self.processors = []
        self.postprocessors = []
        
    def add_preprocessor(self, func: Callable) :
        # Add frame preprocessing stage
        self.preprocessors.append(func)
    
    def add_processor(self, func: Callable) :
        # Add main processing stage
        self.processors.append(func)
    
    def add_postprocessor(self, func: Callable) :
        # Add postprocessing stage
        self.postprocessors.append(func)
    
    def start(self) :
        # Start the pipeline
        self.running = True
        self.processor_thread = threading.Thread(target=self._processing_worker)
        self.processor_thread.daemon = True
        self.processor_thread.start()
        
        self.consumer_thread = threading.Thread(target=self._consumer_worker)
        self.consumer_thread.daemon = True
        self.consumer_thread.start()
    
    def stop(self) :
        # Stop the pipeline
        self.running = False
        if self.processor_thread :
            self.processor_thread.join(timeout=1.0)
        if self.consumer_thread :
            self.consumer_thread.join(timeout=1.0)
    
    def submit_frame(self, frame: np.ndarray) -> bool :
        # Submit frame for processing (non-blocking
        if self.frame_queue.full() :
            return False
        
        try:
            self.frame_queue.put(frame, block=False)
            self.performance.record_frame_submission()
            return True
        except queue.Full :
            return False
    
    def get_processed_frame(self) -> Optional[tuple] :
        # Get processed frame with results (non-blocking
        try :
            return self.processed_queue.get_nowait()
        except queue.Empty :
            return None
    
    def _processing_worker(self) :
        # Main processing pipeline worker
        while self.running :
            try :
                # Get frame with timeout to allow graceful shutdown
                frame = self.frame_queue.get(timeout=0.1)
                
                # Execute pipeline stages
                processed_frame = frame.copy()
                results = {}
                
                # Preprocessing
                for preprocessor in self.preprocessors :
                    processed_frame = preprocessor(processed_frame)
                
                # Main processing
                for processor in self.processors :
                    result = processor(processed_frame)
                    if result is not None :
                        results.update(result)
                
                # Postprocessing
                for postprocessor in self.postprocessors :
                    postprocessor(processed_frame, results)
                
                # Submit to output queue
                if not self.processed_queue.full() :
                    self.processed_queue.put((processed_frame, results))
                
                self.performance.record_frame_processing()
                
            except queue.Empty :
                continue
            except Exception as e :
                self.performance.record_error(f"Pipeline error: {e}")
    
    def _consumer_worker(self) :
        # Consumer worker for processed frames
        while self.running :
            try :
                processed_data = self.processed_queue.get(timeout=0.1)
                # This is where you'd handle the final processed data
                # For example, sending to UI or input controller
                self.performance.record_frame_consumption()
            except queue.Empty :
                continue