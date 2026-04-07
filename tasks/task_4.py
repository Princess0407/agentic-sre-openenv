import random
from typing import Tuple
from mock_infra.database import MockDatabase
from mock_infra.service_mesh import MockServiceMesh
from mock_infra.telemetry import MockTelemetry

TASK_ID = "task_4"
MAX_STEPS = 30


class Task4State:
    def __init__(self):
        self.prometheus_dead = True
        self.sidecar_dead = False
        self.resolved = False

# Global state tracker for this task
STATE = Task4State()


def setup(db: MockDatabase, mesh: MockServiceMesh, rng: random.Random) -> None:
    """
    Inject the Task 4 fault scenario. 
    """
    db.reset()
    mesh.reset()
    STATE.prometheus_dead = True
    STATE.sidecar_dead = False
    STATE.resolved = False


def get_initial_alerts() -> list[str]:
    return ["API_Gateway_503_Errors_Spiking"]


def get_kubelet_logs() -> str:
    if not STATE.sidecar_dead:
        return (
            "Warning: Node memory critically low. "
            "Evicting pod: prometheus-server. "
            "High consumption detected in pod: logging-fluentd-sidecar."
        )
    return "Node memory stabilizing. Pod evictions halted."


def handle_remediation(action: dict) -> Tuple[bool, str]:
    """Returns (handled, stdout) to override normal execution."""
    operation = action.get("operation_type")
    target = action.get("target_service", "")
    
    if target == "logging-fluentd-sidecar" and operation in ["kill", "restart", "delete", "rollback"]:
        STATE.sidecar_dead = True
        return True, "Successfully terminated logging-fluentd-sidecar. Memory pressure dropping."
    
    if target == "prometheus-server" and operation == "restart":
        if STATE.sidecar_dead:
            STATE.prometheus_dead = False
            return True, "Successfully restarted prometheus-server. Telemetry restored."
        else:
            return True, "Failed to restart prometheus-server: Node memory still critically low."
            
    return False, ""


def check_resolution(action: dict, stdout: str) -> tuple[bool, str]:
    """
    Task resolved if prometheus is restarted and sidecar is killed.
    """
    if STATE.sidecar_dead and not STATE.prometheus_dead:
        STATE.resolved = True
        return True, "Root cause resolved: Telemetry restored and memory leak terminated."
    return False, ""
