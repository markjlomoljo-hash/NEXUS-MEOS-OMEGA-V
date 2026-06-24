import json
import jsonschema
from datetime import datetime
from uuid import uuid4
from typing import Any, Dict, List, Literal, Optional

NMO_TELEMETRY_SCHEMA = {
  "$schema": "http://json-schema.org/draft-04/schema#",
  "title": "NMOTelemetryPacket",
  "type": "object",
  "required": ["event_id","timestamp","task_id","execution_track","metrics","state_evaluation"],
  "properties": {
    "event_id": {"type":"string","format":"uuid"},
    "timestamp": {"type":"string","format":"date-time"},
    "task_id": {"type":"string"},
    "parent_task_id": {"type":["string","null"]},
    "execution_track": {"type":"string","enum":["baseline","optimized_l1","optimized_l2","shadow"]},
    "metrics": {
      "type":"object",
      "required":["input_tokens","output_tokens","credit_consumed","wall_time_ms"],
      "properties":{
        "input_tokens":{"type":"integer","minimum":0},
        "output_tokens":{"type":"integer","minimum":0},
        "credit_consumed":{"type":"number","minimum":0.0},
        "wall_time_ms":{"type":"number","minimum":0.0},
        "cpu_utilization":{"type":"number","minimum":0.0}
      }
    },
    "state_evaluation": {
      "type":"object",
      "required":["structural_fidelity_score","constraint_violations","validation_status"],
      "properties":{
        "structural_fidelity_score":{"type":"number","minimum":0.0,"maximum":1.0},
        "constraint_violations":{"type":"array","items":{"type":"string"}},
        "validation_status":{"type":"string","enum":["passed","failed","vetoed"]}
      }
    }
  }
}

class TelemetryLogger:
    def __init__(self, log_file: str = "logs/runtime_trace.log"):
        self.log_file = log_file

    def log(self, data: Dict[str, Any]) -> None:
        try:
            jsonschema.validate(instance=data, schema=NMO_TELEMETRY_SCHEMA)
            with open(self.log_file, "a") as f:
                f.write(json.dumps(data) + "\n")
        except jsonschema.ValidationError as e:
            print(f"Telemetry validation error: {e.message}")
        except Exception as e:
            print(f"Error logging telemetry: {e}")

    def create_packet(self,
                      task_id: str,
                      execution_track: Literal["baseline","optimized_l1","optimized_l2","shadow"],
                      metrics: Dict[str, Any],
                      state_evaluation: Dict[str, Any],
                      parent_task_id: Optional[str] = None) -> Dict[str, Any]:
        return {
            "event_id": str(uuid4()),
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "parent_task_id": parent_task_id,
            "execution_track": execution_track,
            "metrics": metrics,
            "state_evaluation": state_evaluation
        }
