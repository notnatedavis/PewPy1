#   src/core/frame_pipeline.py
#   src/core/frame_pipeline.py
#   Frame processing pipeline with optional parallel executor

# ----- Imports ----- #
import threading
import queue
import time
import logging
from typing import Optional, Callable, Any, Tuple, List
import cv2
import numpy as np

# ----- Main Class ----- #
class FramePipeline:
    # Frame processing pipeline with parallel stages and performance tracking
    
    def __init__(self, max_queue_size: int = 10, processor_executor: Optional['ExecutorBackend'] = None) :
        self.frame_queue = queue.Queue(maxsize=max_queue_size)
        self.processed_queue = queue.Queue(maxsize=max_queue_size)
        self.running = False
        self.processor_thread = None
        self.consumer_thread = None
        
        # pipeline stages
        self.preprocessors: List[Callable] = []
        self.processors: List[Callable] = []
        self.postprocessors: List[Callable] = []
        
        # optional parallel executor for main processing stage
        self.processor_executor = processor_executor
        
        # performance tracking
        self.frames_processed = 0
        self.processing_times = []
        
        logging.info(f"Frame pipeline initialized (max_queue={max_queue_size}, executor={bool(processor_executor)})")
    
    def add_preprocessor(self, func: Callable) -> None :
        self.preprocessors.append(func)
        logging.debug(f"Preprocessor added: {func.__name__}")
    
    def add_processor(self, func: Callable) -> None :
        self.processors.append(func)
        logging.debug(f"Processor added: {func.__name__}")
    
    def add_postprocessor(self, func: Callable) -> None :  
        self.postprocessors.append(func)
        logging.debug(f"Postprocessor added: {func.__name__}")
    
    def start(self) -> None :
        self.running = True
        self.processor_thread = threading.Thread(target=self._processing_worker, daemon=True)
        self.consumer_thread = threading.Thread(target=self._consumer_worker, daemon=True)
        self.processor_thread.start()
        self.consumer_thread.start()
        logging.info("Frame pipeline started")
    
    def stop(self) -> None :
        self.running = False
        if self.processor_thread :
            self.processor_thread.join(timeout=1.0)
        if self.consumer_thread :
            self.consumer_thread.join(timeout=1.0)
        if self.processor_executor :
            self.processor_executor.shutdown(wait=False)
        logging.info("Frame pipeline stopped")
    
    def submit_frame(self, frame: np.ndarray) -> bool :
        if self.frame_queue.full() :
            return False
        try :
            self.frame_queue.put(frame, block=False)
            return True
        except queue.Full :
            return False
    
    def get_processed_frame(self) -> Optional[Tuple[Any, dict]] :
        try :
            return self.processed_queue.get_nowait()
        except queue.Empty :
            return None
    
    def _processing_worker(self) -> None :
        while self.running :
            try :
                frame = self.frame_queue.get(timeout=0.1)
                start_time = time.time()
                
                # preprocessing (always sequential)
                processed_frame = frame.copy()
                for pre in self.preprocessors :
                    processed_frame = pre(processed_frame)
                
                # main processing (maybe parallel)
                results = {}
                if self.processor_executor and self.processors :
                    # Submit all processors to executor and collect futures
                    futures = []
                    for proc in self.processors :
                        future = self.processor_executor.submit(proc, processed_frame)
                        futures.append((proc.__name__, future))
                    for name, future in futures :
                        try :
                            result = future.result(timeout=1.0)
                            if result is not None :
                                if isinstance(result, dict) :
                                    results.update(result)
                                else :
                                    results[name] = result
                        except Exception as e :
                            logging.error(f"Processor {name} error: {e}")
                else :
                    # sequential
                    for proc in self.processors :
                        try :
                            result = proc(processed_frame)
                            if result is not None :
                                if isinstance(result, dict) :
                                    results.update(result)
                                else :
                                    results[proc.__name__] = result
                        except Exception as e :
                            logging.error(f"Processor {proc.__name__} error: {e}")
                
                # postprocessing (sequential)
                for post in self.postprocessors :
                    try :
                        post_result = post(processed_frame, results)
                        if post_result is not None :
                            processed_frame = post_result
                    except Exception as e : 
                        logging.error(f"Postprocessor {post.__name__} error: {e}")
                
                # output
                if not self.processed_queue.full() :
                    self.processed_queue.put((processed_frame, results))
                
                # metrics
                self.frames_processed += 1
                self.processing_times.append(time.time() - start_time)
                if len(self.processing_times) > 100 :
                    self.processing_times.pop(0)
                    
            except queue.Empty :
                continue
            except Exception as e :
                logging.error(f"Pipeline processing error: {e}")
    
    def _consumer_worker(self) -> None :
        while self.running :
            try :
                _ = self.processed_queue.get(timeout=0.1)
                # future: could dispatch to overlay or other consumers
            except queue.Empty :
                continue
    
    def get_performance_stats(self) -> dict :
        avg_time = np.mean(self.processing_times) if self.processing_times else 0
        fps = 1.0 / avg_time if avg_time > 0 else 0
        return {
            'frames_processed': self.frames_processed,
            'avg_processing_time': avg_time,
            'estimated_fps': fps,
            'input_queue_size': self.frame_queue.qsize(),
            'output_queue_size': self.processed_queue.qsize()
        }