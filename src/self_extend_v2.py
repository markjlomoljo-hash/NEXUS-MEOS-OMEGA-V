import os
import subprocess
from typing import Any, Dict, List, Optional
from src.nmo_core import NMOBasicModule

class SelfExtendingOptimizer(NMOBasicModule):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.generated_dir = "dsl/generated/"
        os.makedirs(self.generated_dir, exist_ok=True)
        self.regret_history = {} # (risk_class, instruction_type) -> List[bool]

    def process(self, risk_class: str, instruction_type: str, regret: bool) -> Optional[str]:
        key = (risk_class, instruction_type)
        if key not in self.regret_history:
            self.regret_history[key] = []
        
        self.regret_history[key].append(regret)
        if len(self.regret_history[key]) > 50:
            self.regret_history[key].pop(0)
            
        # Trigger if persistent regret > 20% over 30 tasks
        if len(self.regret_history[key]) >= 30:
            regret_rate = sum(self.regret_history[key]) / len(self.regret_history[key])
            if regret_rate > 0.20:
                return self._generate_override_module(risk_class, instruction_type)
        
        return None

    def _generate_override_module(self, risk_class: str, instruction_type: str) -> str:
        module_name = f"override_{risk_class}_{instruction_type}.py"
        file_path = os.path.join(self.generated_dir, module_name)
        
        print(f"Self-Extending Optimizer: Generating override for {risk_class}/{instruction_type}...")
        
        # In a real system, this would call an LLM via DSL
        dsl_code = f"""
# Auto-generated override for {risk_class}/{instruction_type}
from src.nmo_core import NMOBasicModule

class GeneratedOverride(NMOBasicModule):
    def process(self, intent_profile):
        # Specific logic to handle {risk_class} {instruction_type}
        if intent_profile.risk_class == "{risk_class}":
            return "ultra-fidelity-model-v3" # Safe default
        return None
"""
        with open(file_path, "w") as f:
            f.write(dsl_code)
            
        # Simulate static analysis and testing
        # subprocess.run(["flake8", file_path], check=True)
        
        return file_path

    def update_state(self, telemetry_data: Dict[str, Any]) -> None:
        pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "operational",
            "overrides_generated": len(os.listdir(self.generated_dir))
        }
