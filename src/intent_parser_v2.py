import ast
import re
import json
from uuid import uuid4
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
import numpy as np

from src.nmo_core import NMOBasicModule

# Placeholder for IntentAnchorV2 structure
class IntentAnchorV2(BaseModel):
    uuid: str
    hash: str
    constraints: List[Dict[str, Any]]

class SemanticConstraint(BaseModel):
    text: str
    confidence: float
    type: Literal["hard", "soft"]

class ComplexityIntentProfile(BaseModel):
    cyclomatic_complexity: int = 0
    ast_density_score: float = 0.0
    external_dependency_count: int = 0
    instruction_type: Literal["create","modify","query","debug","other"] = "other"
    token_volume: int = 0
    risk_class: Literal["low","medium","high"] = "low"
    code_embedding: Optional[List[float]] = None  # from CodeBERT
    goal_hierarchy: Dict[str, Any] = Field(default_factory=dict)
    semantic_constraints: List[SemanticConstraint] = Field(default_factory=list)
    intent_anchor: IntentAnchorV2 = Field(default_factory=lambda: IntentAnchorV2(uuid="", hash="", constraints=[]))

class IntentParserV2(NMOBasicModule):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Placeholder for CodeBERT model and T5 parser
        # In a real implementation, these would be loaded here.

    def _analyze_python_code(self, code_content: str) -> Dict[str, Any]:
        complexity = 0
        dependencies = set()
        try:
            tree = ast.parse(code_content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.For, ast.While, ast.AsyncFor, ast.With, ast.AsyncWith, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    complexity += 1
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dependencies.add(alias.name.split(".")[0])
                if isinstance(node, ast.ImportFrom):
                    if node.module:
                        dependencies.add(node.module.split(".")[0])
            # Simple AST density score: ratio of AST nodes to code lines
            ast_nodes = len(list(ast.walk(tree)))
            lines = len(code_content.splitlines())
            ast_density_score = ast_nodes / lines if lines > 0 else 0.0

        except SyntaxError:
            # Handle cases where code is not valid Python
            return {"cyclomatic_complexity": 0, "ast_density_score": 0.0, "external_dependency_count": 0}
        return {
            "cyclomatic_complexity": complexity,
            "ast_density_score": round(ast_density_score, 2),
            "external_dependency_count": len(dependencies)
        }

    def _generate_code_embedding(self, code_content: str) -> List[float]:
        # Simulate CodeBERT embedding. In a real scenario, this would use a transformer model.
        # For now, return a fixed-size random vector.
        return np.random.rand(768).tolist() # Example embedding size

    def _extract_intent_from_prompt(self, prompt_text: str) -> Dict[str, Any]:
        instruction_type = "other"
        risk_class = "low"
        goal_hierarchy = {"main_goal": prompt_text.split("\n")[0]}

        lower_prompt = prompt_text.lower()

        if any(kw in lower_prompt for kw in ["create", "build", "generate", "implement"]):
            instruction_type = "create"
        elif any(kw in lower_prompt for kw in ["modify", "refactor", "update", "change"]):
            instruction_type = "modify"
        elif any(kw in lower_prompt for kw in ["query", "find", "search", "get"]):
            instruction_type = "query"
        elif any(kw in lower_prompt for kw in ["debug", "fix", "troubleshoot"]):
            instruction_type = "debug"

        if any(kw in lower_prompt for kw in ["critical", "sensitive", "production", "security"]):
            risk_class = "high"
        elif any(kw in lower_prompt for kw in ["complex", "multi-step", "architecture"]):
            risk_class = "medium"

        # Simple goal hierarchy extraction
        if "steps:" in lower_prompt:
            steps_content = prompt_text.split("steps:", 1)[1]
            goal_hierarchy["steps"] = [s.strip() for s in steps_content.split("\n") if s.strip()]

        return {"instruction_type": instruction_type, "risk_class": risk_class, "goal_hierarchy": goal_hierarchy}

    def _extract_hard_constraints(self, prompt_text: str) -> List[SemanticConstraint]:
        constraints = []
        hard_constraint_keywords = ["must", "shall", "cannot", "strictly", "forbidden"]
        for line in prompt_text.splitlines():
            lower_line = line.lower()
            if any(kw in lower_line for kw in hard_constraint_keywords):
                constraints.append(SemanticConstraint(text=line.strip(), confidence=1.0, type="hard"))
        return constraints

    def process(self, prompt_text: str, workspace_files: List[Dict]) -> ComplexityIntentProfile:
        profile = ComplexityIntentProfile()
        profile.token_volume = len(prompt_text) // 4 # Rough token estimate

        # Code Understanding
        all_code_content = ""
        for file_data in workspace_files:
            if file_data.get("language") == "python":
                code_analysis = self._analyze_python_code(file_data["content"])
                profile.cyclomatic_complexity += code_analysis["cyclomatic_complexity"]
                profile.ast_density_score = max(profile.ast_density_score, code_analysis["ast_density_score"]) # Max for simplicity
                profile.external_dependency_count += code_analysis["external_dependency_count"]
                all_code_content += file_data["content"] + "\n"
            # Add logic for other languages if needed

        if all_code_content:
            profile.code_embedding = self._generate_code_embedding(all_code_content)

        # Intent Graph Construction
        intent_data = self._extract_intent_from_prompt(prompt_text)
        profile.instruction_type = intent_data["instruction_type"]
        profile.risk_class = intent_data["risk_class"]
        profile.goal_hierarchy = intent_data["goal_hierarchy"]

        # Intent DNA v2 Anchor
        profile.semantic_constraints = self._extract_hard_constraints(prompt_text)
        # For now, generate a dummy IntentAnchorV2
        profile.intent_anchor = IntentAnchorV2(
            uuid=str(uuid4()),
            hash=str(hash(f"{prompt_text}-{json.dumps(workspace_files)}")),
            constraints=[c.dict() for c in profile.semantic_constraints]
        )

        return profile

    def update_state(self, telemetry_data: Dict[str, Any]) -> None:
        # This module is primarily stateless for processing, but could update internal models
        # if a fine-tuned T5 or CodeBERT was being actively trained.
        pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "operational",
            "code_analysis_enabled": True,
            "semantic_parsing_enabled": True
        }
