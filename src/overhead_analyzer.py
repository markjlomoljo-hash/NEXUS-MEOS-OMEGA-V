from typing import List, Dict, Any
from dataclasses import dataclass
from src.nmo_core import NMOBasicModule

@dataclass
class OverheadContext:
    prompt_text: str
    context_files: List[Dict]  # each has 'file_name', 'content'

class NMOOverheadAnalyzer(NMOBasicModule):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.ceiling = config["nmo_system_profile"]["overhead_token_ceiling"]

    def process(self, ctx: OverheadContext) -> Dict[str, Any]:
        est_tokens = (len(ctx.prompt_text) + sum(len(f["content"]) for f in ctx.context_files)) // 4
        if est_tokens < 150:
            return {"action": "SHORT_CIRCUIT_FAST_PASS", "reason": "Micro-task"}
        if len(ctx.context_files) == 0 and est_tokens < 300:
            return {"action": "SHORT_CIRCUIT_FAST_PASS", "reason": "Small task without context"}
        triggers = {"architecture","refactor","optimize","compile","dockerfile","db_schema","orchestrate"}
        if any(kw in ctx.prompt_text.lower() for kw in triggers):
            return {"action": "ENGAGE_NMO_LAYER", "reason": "Structural complexity"}
        if est_tokens > self.ceiling * 10:
            return {"action": "ENGAGE_NMO_LAYER", "reason": "Large prompt justifies overhead"}
        return {"action": "SHORT_CIRCUIT_FAST_PASS", "reason": "Below threshold"}

