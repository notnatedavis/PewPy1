#   src/utils/shared_memory.py
#   Shared memory management for inter-process data sharing

# ----- Imports ----- #
import multiprocessing as mp
from multiprocessing import shared_memory
import numpy as np
from typing import Optional, Tuple
import threading

# ----- main Class ----- #
class SharedMemoryManager :
    # Manages shared memory blocks for zero-copy inter-process communication

    def __init__(self) :
        self.blocks = {}
        self.lock = threading.Lock()
    
    def create_shared_array(self, name: str, shape: tuple, dtype: np.dtype) -> np.ndarray :
        # Create a shared memory array
        with self.lock :
            if name in self.blocks :
                raise ValueError(f"Shared memory block '{name}' already exists")
            
            # Calculate size
            dtype = np.dtype(dtype)
            size = int(np.prod(shape)) * dtype.itemsize
            
            # Create shared memory
            shm = shared_memory.SharedMemory(create=True, size=size, name=name)
            
            # Create numpy array on shared memory
            array = np.ndarray(shape, dtype=dtype, buffer=shm.buf)
            
            # Store reference
            self.blocks[name] = {
                'shm': shm,
                'array': array,
                'shape': shape,
                'dtype': dtype
            }
            
            return array
    
    def get_shared_array(self, name: str) -> Optional[np.ndarray] :
        # Get existing shared array
        with self.lock :
            if name in self.blocks :
                return self.blocks[name]['array']
            return None
    
    def attach_shared_array(self, name: str) -> Optional[np.ndarray] :
        # Attach to existing shared array
        with self.lock :
            if name in self.blocks :
                return self.blocks[name]['array']
            
            try :
                shm = shared_memory.SharedMemory(name=name)
                
                # We need to know shape and dtype - this is a limitation
                # In practice, you'd need to communicate this separately
                raise NotImplementedError("Shape and dtype must be known for attachment")
                
            except FileNotFoundError :
                return None
    
    def release_shared_array(self, name: str) :
        # Release shared memory array
        with self.lock :
            if name in self.blocks :
                self.blocks[name]['shm'].close()
                self.blocks[name]['shm'].unlink()
                del self.blocks[name]
    
    def cleanup(self) :
        # Cleanup all shared memory blocks
        with self.lock :
            for name in list(self.blocks.keys()) :
                self.release_shared_array(name)