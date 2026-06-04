# pewpy/common/constants.py
# Shared enums and dataclasses used across the application

# ----- Imports ----- #
from enum import Enum
from dataclasses import dataclass

# ----- Enums ----- #
class WorkerState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"

WorkerStatus = WorkerState  # alias for backward compatibility

# ----- Dataclasses ----- #
@dataclass
class WorkerMetrics:
    start_time: float = 0.0
    total_cycles: int = 0
    error_count: int = 0
    avg_cycle_time: float = 0.0
    last_cycle_time: float = 0.0