#   src/core/config.py
#   Configuration loader and manager

# ----- Imports ----- #
import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# ----- Main Class ----- #
class Config:
    # Central configuration manager with hot-reload capability
    
    def __init__(self, config_dir: Optional[str] = None) :
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self.config: Dict[str, Any] = {}
        self._loaded_files: set = set()
        self.load()
        
    def load(self) -> None :
        # Load configuration from YAML files
        default_path = self.config_dir / "default.yaml"
        perf_path = self.config_dir / "performance.yaml"
        
        # Start with empty config
        new_config = {}
        
        # Load default
        if default_path.exists() :
            with open(default_path, 'r') as f :
                default = yaml.safe_load(f) or {}
            new_config.update(default)
            self._loaded_files.add(str(default_path))
        else :
            logging.warning(f"Default config not found: {default_path}")
            
        # Override with performance (user) config
        if perf_path.exists() :
            with open(perf_path, 'r') as f :
                perf = yaml.safe_load(f) or {}
            self._merge_dict(new_config, perf)
            self._loaded_files.add(str(perf_path))
            
        self.config = new_config
        logging.info(f"Configuration loaded from: {', '.join(self._loaded_files)}")
        
    def reload(self) -> None :
        # Reload configuration from disk
        self.load()
        logging.info("Configuration reloaded")
        
    def get(self, key: str, default: Any = None) -> Any :
        # Get a configuration value using dot notation (e.g., 'workers.aimbot.target_fps')
        keys = key.split('.')
        value = self.config
        for k in keys :
            if isinstance(value, dict) :
                value = value.get(k)
                if value is None :
                    return default
            else :
                return default
        return value if value is not None else default
    
    def _merge_dict(self, base: Dict, override: Dict) -> None :
        # Recursively merge override dict into base
        for key, value in override.items() :
            if key in base and isinstance(base[key], dict) and isinstance(value, dict) :
                self._merge_dict(base[key], value)
            else :
                base[key] = value