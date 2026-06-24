import json
import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel
from src.nmo_core import NMOBasicModule

class ValidationResult(BaseModel):
    structural_fidelity_score: float
    constraint_violations: List[str]
    validation_status: Literal["passed", "failed", "vetoed"]
    failure_trace: Optional[str] = None

class ValidatorV2(NMOBasicModule):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.min_fidelity_score = config["validation"]["min_fidelity_score"]
        self.similarity_threshold = config["validation"]["constraint_similarity_threshold"]

    def _check_schema(self, output: str, expected_type: str) -> float:
        if expected_type == "json":
            try:
                json.loads(output)
                return 1.0
            except json.JSONDecodeError:
                # Try to extract JSON from markdown blocks
                match = re.search(r'```json\n(.*?)\n```', output, re.DOTALL)
                if match:
                    try:
                        json.loads(match.group(1))
                        return 0.8 # Slightly lower for being wrapped
                    except json.JSONDecodeError:
                        pass
                return 0.0
        return 1.0 # Default pass if no specific schema

    def _check_symbolic_constraints(self, output: str, intent_anchor: Any) -> tuple[float, List[str]]:
        violations = []
        score = 1.0
        if not intent_anchor or not hasattr(intent_anchor, 'constraints'):
            return score, violations

        for constraint in intent_anchor.constraints:
            text = constraint.get("text", "").lower()
            # Simple symbolic checks
            if "no import" in text:
                lib = text.split("no import of")[-1].strip()
                if f"import {lib}" in output or f"from {lib}" in output:
                    violations.append(f"Forbidden import detected: {lib}")
            if "must include" in text:
                term = text.split("must include")[-1].strip()
                if term not in output.lower():
                    violations.append(f"Missing required term: {term}")
            
        if violations:
            score = 0.0 # Hard violation forces score to 0
        return score, violations

    def _check_semantic_consistency(self, output: str, raw_prompt: str) -> float:
        # Placeholder for cross-encoder comparison
        # In a real scenario, use sentence-transformers
        # For now, use simple word overlap as a proxy
        prompt_words = set(raw_prompt.lower().split())
        output_words = set(output.lower().split())
        if not prompt_words:
            return 1.0
        overlap = len(prompt_words.intersection(output_words)) / len(prompt_words)
        return min(1.0, overlap * 1.5) # Scale overlap

    def process(self, output: str, intent_profile: Any) -> Dict[str, Any]:
        # 1. Schema Validator
        schema_score = self._check_schema(output, "json" if intent_profile.instruction_type == "query" else "text")
        
        # 2. Symbolic Constraint Solver
        symbolic_score, violations = self._check_symbolic_constraints(output, intent_profile.intent_anchor)
        
        # 3. Semantic Consistency Check
        semantic_score = self._check_semantic_consistency(output, intent_profile.goal_hierarchy.get("main_goal", ""))
        
        # Score fusion: 0.3*schema + 0.3*symbolic + 0.4*semantic
        fidelity_score = 0.3 * schema_score + 0.3 * symbolic_score + 0.4 * semantic_score
        
        # Hard violation of any constraint → score forced to 0.0
        if violations:
            fidelity_score = 0.0
            status = "vetoed"
        elif fidelity_score >= self.min_fidelity_score:
            status = "passed"
        else:
            status = "failed"

        failure_trace = None
        if status != "passed":
            failure_trace = f"Validation failed. Score: {fidelity_score:.2f}. Violations: {', '.join(violations)}"

        return {
            "structural_fidelity_score": round(fidelity_score, 2),
            "constraint_violations": violations,
            "validation_status": status,
            "failure_trace": failure_trace
        }

    def update_state(self, telemetry_data: Dict[str, Any]) -> None:
        pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "operational",
            "min_fidelity_score": self.min_fidelity_score
        }
