#   src/utils/serialization.py
#   Efficient data serialization for inter-process communication

# ----- Imports ----- #
import pickle
import zlib
import lz4.frame
from typing import Any

# ----- main Class ----- #
class EfficientSerializer :
    # High-performance serialization with compression options
    # Optimized for Python 3.13 with protocol 5

    def __init__(self, compression: str = "none") :
        self.compression = compression
        self.protocol = pickle.HIGHEST_PROTOCOL
    
    def serialize(self, data: Any) -> bytes :
        # Serialize data with optional compression
        # Serialize with highest protocol
        serialized = pickle.dumps(data, protocol=self.protocol)
        
        # Apply compression
        if self.compression == "lz4" :
            return lz4.frame.compress(serialized)
        elif self.compression == "zlib" :
            return zlib.compress(serialized)
        else:
            return serialized
    
    def deserialize(self, data: bytes) -> Any :
        # Deserialize data with decompression
        # Decompress if needed
        if self.compression == "lz4" :
            data = lz4.frame.decompress(data)
        elif self.compression == "zlib" :
            data = zlib.decompress(data)
        
        # Deserialize
        return pickle.loads(data)
    
    def set_compression(self, compression: str):
        # Change compression method
        valid_methods = ["none", "lz4", "zlib"]
        if compression in valid_methods :
            self.compression = compression
        else :
            raise ValueError(f"Compression must be one of {valid_methods}")
