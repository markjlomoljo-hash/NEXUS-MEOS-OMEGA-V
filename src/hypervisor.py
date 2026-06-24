import json
import jsonschema
from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List, Literal, Optional
from enum import Enum
from pydantic import BaseModel, Field

from src.nmo_core import INMOOptimizationModule, NMOBasicModule
from src.config_loader import ConfigLoader
from src.telemetry_schema import TelemetryLogger, NMO_TELEMETRY_SCHEMA
from src.overhead_analyzer import OverheadContext

# Placeholder for Module 4 output
class ComplexityIntentProfile(BaseModel):
    cyclomatic_complexity: int = 0
    ast_density_score: float = 0.0
    external_dependency_count: int = 0
    instruction_type: Literal["create","modify","query","debug","other"] = "other"
    token_volume: int = 0
    risk_class: Literal["low","medium","high"] = "low"
    code_embedding: Optional[List[float]] = None
    goal_hierarchy: Dict[str, Any] = Field(default_factory=dict)
    semantic_constraints: List[Dict[str, Any]] = Field(default_factory=list) # { text, confidence, type }
    intent_anchor: Dict[str, Any] = Field(default_factory=dict) # Placeholder for IntentAnchorV2

class TaskStateEnum(str, Enum):
    PENDING = "PENDING"
    EVALUATING = "EVALUATING"
    ROUTED = "ROUTED"
    EXECUTING = "EXECUTING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    ROLLBACK = "ROLLBACK"

class TaskContext(BaseModel):
    task_id: str
    parent_task_id: Optional[str] = None
    state: TaskStateEnum = TaskStateEnum.PENDING
    raw_prompt: str
    raw_context_files: List[Dict] = Field(default_factory=list)
    intent_profile: Optional[ComplexityIntentProfile] = None
    target_execution_track: Optional[str] = None
    execution_history: List[Dict[str, Any]] = Field(default_factory=list)
    result: Optional[Any] = None
    structural_fidelity_score: float = 0.0
    constraint_violations: List[str] = Field(default_factory=list)
    validation_status: Literal["passed","failed","vetoed"] = "failed"
    retry_count: int = 0
    last_transition_time: datetime = Field(default_factory=datetime.now)

class Hypervisor(NMOBasicModule):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.active_tasks: Dict[str, TaskContext] = {}
        self.telemetry_logger = TelemetryLogger()
        self.max_orchestration_depth = self.config["nmo_system_profile"]["max_orchestration_depth"]
        self.min_fidelity_score = self.config["validation"]["min_fidelity_score"]

        # Placeholder for other modules (will be injected later)
        self.overhead_analyzer: Optional[INMOOptimizationModule] = None
        self.intent_parser: Optional[INMOOptimizationModule] = None
        self.router: Optional[INMOOptimizationModule] = None
        self.validator: Optional[Any] = None

    def _transition_state(self, task_id: str, new_state: TaskStateEnum, **kwargs: Any) -> None:
        task = self.active_tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found.")

        # Simplified state transition for robustness
        if "result" in kwargs:
            task.result = kwargs["result"]
        if "intent_profile" in kwargs:
            task.intent_profile = kwargs["intent_profile"]
        if "target_execution_track" in kwargs:
            task.target_execution_track = kwargs["target_execution_track"]
            
        task.state = new_state
        task.last_transition_time = datetime.now()

    def process(self, raw_prompt: str, raw_context_files: List[Dict]) -> str:
        task_id = str(uuid4())
        task_context = TaskContext(task_id=task_id, raw_prompt=raw_prompt, raw_context_files=raw_context_files)
        self.active_tasks[task_id] = task_context

        self._transition_state(task_id, TaskStateEnum.EVALUATING)

        # Module 0: Overhead Gate
        if self.overhead_analyzer:
            overhead_ctx = OverheadContext(prompt_text=raw_prompt, context_files=raw_context_files)
            overhead_decision = self.overhead_analyzer.process(overhead_ctx)
            if overhead_decision["action"] == "SHORT_CIRCUIT_FAST_PASS":
                self.active_tasks[task_id].result = "Fast-pass execution completed."
                self.active_tasks[task_id].structural_fidelity_score = 1.0
                self.active_tasks[task_id].validation_status = "passed"
                self._transition_state(task_id, TaskStateEnum.VALIDATING, result="Fast-pass execution completed.")
                self._transition_state(task_id, TaskStateEnum.COMPLETED)
                self._log_telemetry(task_id, "baseline", {"input_tokens": 0, "output_tokens": 0, "credit_consumed": 0.0, "wall_time_ms": 0.0}, {"structural_fidelity_score": 1.0, "constraint_violations": [], "validation_status": "passed"})
                return task_id

        # Module 4: Intent Parser
        intent_profile = self._evaluate_task_intent(task_id)
        self.active_tasks[task_id].intent_profile = intent_profile

        # Module 6: Dynamic Utility Router
        target_track = self._route_task(task_id, intent_profile)
        self._transition_state(task_id, TaskStateEnum.ROUTED, intent_profile=intent_profile, target_execution_track=target_track)

        # Module Execution
        self._transition_state(task_id, TaskStateEnum.EXECUTING)
        result = self._execute_task_on_track(task_id, target_track, raw_prompt, raw_context_files)

        # Module 8: Validation & Veto
        validation_result = self._validate_task_output(task_id, result, intent_profile)
        self.active_tasks[task_id].structural_fidelity_score = validation_result["structural_fidelity_score"]
        self.active_tasks[task_id].constraint_violations = validation_result["constraint_violations"]
        self.active_tasks[task_id].validation_status = validation_result["validation_status"]
        self._transition_state(task_id, TaskStateEnum.VALIDATING, result=result)

        if self.active_tasks[task_id].validation_status == "vetoed":
            self._handle_rollback(task_id)
            # Re-execute on high-cap track
            target_track = "ultra-fidelity-model-v3"
            self._transition_state(task_id, TaskStateEnum.EXECUTING)
            result = self._execute_task_on_track(task_id, target_track, raw_prompt, raw_context_files)
            
            # Re-validate after retry
            validation_result = self._validate_task_output(task_id, result, intent_profile)
            self.active_tasks[task_id].structural_fidelity_score = validation_result["structural_fidelity_score"]
            self.active_tasks[task_id].constraint_violations = validation_result["constraint_violations"]
            self.active_tasks[task_id].validation_status = validation_result["validation_status"]
            self._transition_state(task_id, TaskStateEnum.VALIDATING, result=result)

        self._transition_state(task_id, TaskStateEnum.COMPLETED)
        self._log_telemetry(task_id, target_track, {"input_tokens": 0, "output_tokens": 0, "credit_consumed": 0.0, "wall_time_ms": 0.0}, validation_result)
        return task_id

    def _evaluate_task_intent(self, task_id: str) -> ComplexityIntentProfile:
        task = self.active_tasks[task_id]
        if self.intent_parser:
            return self.intent_parser.process(task.raw_prompt, task.raw_context_files)
        return ComplexityIntentProfile()

    def _route_task(self, task_id: str, intent_profile: ComplexityIntentProfile) -> str:
        if self.router:
            return self.router.process(intent_profile)
        return "baseline"

    def _execute_task_on_track(self, task_id: str, track: str, prompt: str, files: List[Dict]) -> Any:
        return f"Simulated result for {prompt[:50]}... on {track}"

    def _validate_task_output(self, task_id: str, result: Any, intent_profile: ComplexityIntentProfile) -> Dict[str, Any]:
        if self.validator:
            return self.validator.process(result, intent_profile)
        return {"structural_fidelity_score": 0.0, "constraint_violations": ["No validator"], "validation_status": "failed"}

    def _handle_rollback(self, task_id: str) -> None:
        task = self.active_tasks[task_id]
        task.retry_count += 1
        print(f"DEBUG: Incrementing retry_count for {task_id} to {task.retry_count}")
        self._transition_state(task_id, TaskStateEnum.ROLLBACK)

    def _log_telemetry(self, task_id: str, execution_track: str, metrics: Dict[str, Any], state_evaluation: Dict[str, Any], parent_task_id: Optional[str] = None) -> None:
        packet = self.telemetry_logger.create_packet(
            task_id=task_id,
            execution_track=execution_track,
            metrics=metrics,
            state_evaluation=state_evaluation,
            parent_task_id=parent_task_id
        )
        self.telemetry_logger.log(packet)

    def update_state(self, telemetry_data: Dict[str, Any]) -> None:
        pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "operational",
            "active_tasks_count": len(self.active_tasks),
            "config_loaded": True,
            "max_orchestration_depth": self.max_orchestration_depth
        }

