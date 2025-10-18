#   src/ui/config_manager.py
#   Configuration management with hot-reload capability

# ----- Imports ----- #
import yaml
import os
import threading
import time
from typing import Dict, Any, Optional
from pathlib import Path
import logging

# ----- main Class ----- #
class ConfigManager :
    # Manages application configuration with file watching and hot-reload
    
    def __init__(self, config_dir: str = "config") :
        self.config_dir = Path(config_dir)
        self.configs = {}
        self.watcher_thread = None
        self.watching = False
        self.callbacks = []
        
        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)
        
        # Load initial configurations
        self._load_all_configs()
    
    def _load_all_configs(self) :
        # Load all YAML configuration files
        config_files = list(self.config_dir.glob("*.yaml"))
        for config_file in config_files:
            self.load_config(config_file.stem, config_file)
    
    def load_config(self, name: str, file_path: Optional[Path] = None) -> bool:
        # Load a specific configuration file
        if file_path is None :
            file_path = self.config_dir / f"{name}.yaml"
        
        try :
            with open(file_path, 'r') as f:
                self.configs[name] = yaml.safe_load(f)
            logging.info(f"Loaded configuration: {name}")
            return True
        except Exception as e :
            logging.error(f"Failed to load config {name}: {e}")
            return False
    
    def save_config(self, name: str, data: Dict[str, Any]) -> bool :
        # Save configuration to file
        file_path = self.config_dir / f"{name}.yaml"
        
        try :
            with open(file_path, 'w') as f :
                yaml.dump(data, f, default_flow_style=False)
            
            self.configs[name] = data
            self._notify_callbacks(name, data)
            return True
        except Exception as e :
            logging.error(f"Failed to save config {name}: {e}")
            return False
    
    def get(self, name: str, key: str = None, default: Any = None) -> Any :
        # Get configuration value
        if name not in self.configs :
            self.load_config(name)
        
        config = self.configs.get(name, {})
        if key is None :
            return config
        
        # Support nested keys with dot notation
        keys = key.split('.')
        value = config
        for k in keys :
            value = value.get(k, {})
        
        return value if value != {} else default
    
    def set(self, name: str, key: str, value: Any) -> bool :
        # Set configuration value
        if name not in self.configs :
            self.configs[name] = {}
        
        # Support nested keys with dot notation
        keys = key.split('.')
        config = self.configs[name]
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        return self.save_config(name, self.configs[name])
    
    def add_callback(self, callback) :
        # Add configuration change callback
        self.callbacks.append(callback)
    
    def _notify_callbacks(self, name: str, data: Dict[str, Any]) :
        # Notify all callbacks of configuration changes
        for callback in self.callbacks :
            try :
                callback(name, data)
            except Exception as e :
                logging.error(f"Config callback error: {e}")
    
    def start_watching(self) :
        # Start file watching for config changes
        self.watching = True
        self.watcher_thread = threading.Thread(target=self._file_watcher)
        self.watcher_thread.daemon = True
        self.watcher_thread.start()
    
    def stop_watching(self) :
        # Stop file watching
        self.watching = False
        if self.watcher_thread :
            self.watcher_thread.join(timeout=1.0)
    
    def _file_watcher(self) :
        # Monitor config files for changes
        last_modified = {}
        
        while self.watching :
            try :
                for config_file in self.config_dir.glob("*.yaml") :
                    current_mtime = config_file.stat().st_mtime
                    file_name = config_file.stem
                    
                    if file_name not in last_modified :
                        last_modified[file_name] = current_mtime
                    elif current_mtime > last_modified[file_name] :
                        # File changed, reload it
                        self.load_config(file_name, config_file)
                        last_modified[file_name] = current_mtime
                        logging.info(f"Config file updated: {file_name}")
                
                time.sleep(2.0)  # Check every 2 seconds
            except Exception as e :
                logging.error(f"Config watcher error: {e}")
                time.sleep(5.0)