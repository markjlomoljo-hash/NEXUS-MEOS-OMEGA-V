import asyncio
import time
from typing import Any, Dict, List, Optional
from src.nmo_core import NMOBasicModule

class ShadowArena(NMOBasicModule):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.enabled = config["nmo_system_profile"]["shadow_execution_enabled"]
        self.budget = config["nmo_system_profile"]["shadow_budget_credits"]
        self.spent = 0.0

    async def run_race(self, task_id: str, prompt: str, tracks: List[str], validator: Any, intent_profile: Any) -> Optional[Dict[str, Any]]:
        if not self.enabled or self.spent >= self.budget:
            return None

        print(f"Shadow Arena: Starting race for task {task_id} with tracks {tracks}")
        
        # Simulate asynchronous execution of multiple tracks
        tasks = [self._execute_shadow_track(task_id, track, prompt, validator, intent_profile) for track in tracks]
        
        # Wait for the first one that passes validation
        for completed_task in asyncio.as_completed(tasks):
            result = await completed_task
            if result and result["validation"]["validation_status"] == "passed":
                print(f"Shadow Arena: Track {result['track']} won the race for task {task_id}")
                return result
        
        return None

    async def _execute_shadow_track(self, task_id: str, track: str, prompt: str, validator: Any, intent_profile: Any) -> Dict[str, Any]:
        # Simulate execution latency
        start_time = time.time()
        await asyncio.sleep(0.1) # Simulated network delay
        
        # Simulated result
        result_text = f"Shadow result from {track} for {prompt[:20]}"
        
        # Validation
        validation = validator.process(result_text, intent_profile)
        
        end_time = time.time()
        cost = 0.001 # Simulated cost
        self.spent += cost

        return {
            "task_id": task_id,
            "track": track,
            "result": result_text,
            "validation": validation,
            "metrics": {
                "wall_time_ms": (end_time - start_time) * 1000,
                "credit_consumed": cost
            }
        }

    def process(self, *args: Any, **kwargs: Any) -> Any:
        # Shadow Arena is primarily used via run_race async method
        pass

    def update_state(self, telemetry_data: Dict[str, Any]) -> None:
        pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "operational" if self.enabled else "disabled",
            "budget": self.budget,
            "spent": round(self.spent, 4)
        }
