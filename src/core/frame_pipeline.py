#   src/core/frame_pipeline.py
#   Frame processing pipeline for high-throughput image processing

# ----- Imports ----- #
import threading
import queue
import time
import logging
from typing import Optional, Callable, Any, Tuple
import cv2
import numpy as np

# ----- Main Class ----- #
class FramePipeline :
    # Optimized frame processing pipeline with parallel stages
    
    def __init__(self, max_queue_size: int = 10) :
        self.frame_queue = queue.Queue(maxsize=max_queue_size)
        self.processed_queue = queue.Queue(maxsize=max_queue_size)
        self.running = False
        self.processor_thread = None
        self.consumer_thread = None
        
        # pipeline stages
        self.preprocessors = []
        self.processors = []
        self.postprocessors = []
        
        # performance tracking
        self.frames_processed = 0
        self.processing_times = []
        
        logging.info("Frame pipeline initialized")
    
    def add_preprocessor(self, func: Callable) -> None :
        # add frame preprocessing stage
        self.preprocessors.append(func)
        logging.debug(f"Preprocessor added: {func.__name__}")
    
    def add_processor(self, func: Callable) -> None :
        # add main processing stage
        self.processors.append(func)
        logging.debug(f"Processor added: {func.__name__}")
    
    def add_postprocessor(self, func: Callable) -> None : 
        # add postprocessing stage
        self.postprocessors.append(func)
        logging.debug(f"Postprocessor added: {func.__name__}")
    
    def start(self) -> None :
        # start the pipeline
        self.running = True
        self.processor_thread = threading.Thread(target=self._processing_worker, daemon=True)
        self.consumer_thread = threading.Thread(target=self._consumer_worker, daemon=True)
        
        self.processor_thread.start()
        self.consumer_thread.start()
        
        logging.info("Frame pipeline started")
    
    def stop(self) -> None :
        # stop the pipeline
        self.running = False
        if self.processor_thread :
            self.processor_thread.join(timeout=1.0)
        if self.consumer_thread :
            self.consumer_thread.join(timeout=1.0)
        
        logging.info("Frame pipeline stopped")
    
    def submit_frame(self, frame: np.ndarray) -> bool :
        # submit frame for processing (non-blocking)
        if self.frame_queue.full() :
            return False
        
        try :
            self.frame_queue.put(frame, block=False)
            return True
        except queue.Full :
            return False
    
    def get_processed_frame(self) -> Optional[Tuple[Any, dict]] :
        # get processed frame with results (non-blocking
        try :
            return self.processed_queue.get_nowait()
        except queue.Empty :
            return None
    
    def _processing_worker(self) -> None :
        # Main processing pipeline worker
        while self.running :
            try :
                # get frame with timeout to allow graceful shutdown
                frame = self.frame_queue.get(timeout=0.1)
                start_time = time.time()
                
                # execute pipeline stages
                processed_frame = frame.copy()
                results = {}
                
                # preprocessing stage
                for preprocessor in self.preprocessors :
                    processed_frame = preprocessor(processed_frame)
                
                # Main processing stage
                for processor in self.processors :
                    result = processor(processed_frame)
                    if result is not None :
                        if isinstance(result, dict) :
                            results.update(result)
                        else :
                            results[processor.__name__] = result
                
                # postprocessing stage
                for postprocessor in self.postprocessors :
                    postprocessor_result = postprocessor(processed_frame, results)
                    if postprocessor_result is not None :
                        processed_frame = postprocessor_result
                
                # submit to output queue
                if not self.processed_queue.full() :
                    self.processed_queue.put((processed_frame, results))
                
                # update performance metrics
                self.frames_processed += 1
                self.processing_times.append(time.time() - start_time)
                # keep only recent 100 samples
                if len(self.processing_times) > 100 :
                    self.processing_times.pop(0)
                
            except queue.Empty :
                continue
            except Exception as e :
                logging.error(f"Pipeline processing error: {e}")
    
    def _consumer_worker(self) -> None :
        # consumer worker for processed frames
        while self.running :
            try :
                processed_data = self.processed_queue.get(timeout=0.1)
                # (future) handle the processed data here
                # ex: display, save, or use for further processing
                pass
            except queue.Empty :
                continue
    
    def get_performance_stats(self) -> dict :
        # get pipeline performance statistics
        avg_time = np.mean(self.processing_times) if self.processing_times else 0
        fps = 1.0 / avg_time if avg_time > 0 else 0
        
        return {
            'frames_processed': self.frames_processed,
            'avg_processing_time': avg_time,
            'estimated_fps': fps,
            'input_queue_size': self.frame_queue.qsize(),
            'output_queue_size': self.processed_queue.qsize()
        }