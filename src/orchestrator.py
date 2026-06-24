import asyncio
import argparse
from typing import Any, Dict, List, Optional
from src.config_loader import ConfigLoader
from src.hypervisor import Hypervisor
from src.overhead_analyzer import NMOOverheadAnalyzer
from src.intent_parser_v2 import IntentParserV2
from src.router_bandit import RouterBandit
from src.validator_v2 import ValidatorV2
from src.predictor import PredictiveScheduler
from src.synergy_gnn import SynergyMesh
from src.shadow_arena import ShadowArena
from src.forensics_v2 import CreditLeakForensics
from src.genome_optimizer import GenomeOptimizer
from src.red_team import AdversarialRedTeam
from src.self_extend_v2 import SelfExtendingOptimizer
from src.dashboard import DashboardServer

class NMOUltimateOrchestrator:
    def __init__(self, config_path: str = "config/production_agent_spec.json"):
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.config
        
        # Initialize all modules
        self.hypervisor = Hypervisor(self.config)
        self.overhead_analyzer = NMOOverheadAnalyzer(self.config)
        self.intent_parser = IntentParserV2(self.config)
        self.router = RouterBandit(self.config)
        self.validator = ValidatorV2(self.config)
        self.predictor = PredictiveScheduler(self.config)
        self.synergy_mesh = SynergyMesh(self.config)
        self.shadow_arena = ShadowArena(self.config)
        self.forensics = CreditLeakForensics(self.config)
        self.genome_optimizer = GenomeOptimizer(self.config)
        self.red_team = AdversarialRedTeam(self.config)
        self.self_extender = SelfExtendingOptimizer(self.config)
        self.dashboard = DashboardServer(self.config)

        # Inject dependencies into Hypervisor
        self.hypervisor.overhead_analyzer = self.overhead_analyzer
        self.hypervisor.intent_parser = self.intent_parser
        self.hypervisor.router = self.router
        self.hypervisor.validator = self.validator

    async def run_task(self, prompt: str, context_files: List[Dict] = None) -> Dict[str, Any]:
        context_files = context_files or []
        print(f"Orchestrator: Received task - {prompt[:50]}...")
        
        # 1. Predictive pre-warming
        prediction = self.predictor.process([prompt])
        
        # 2. Hypervisor execution
        task_id = self.hypervisor.process(prompt, context_files)
        task_context = self.hypervisor.active_tasks[task_id]
        
        # 3. Post-execution optimization and learning
        telemetry_packet = self.hypervisor.telemetry_logger.create_packet(
            task_id=task_id,
            execution_track=task_context.target_execution_track or "baseline",
            metrics={"input_tokens": 100, "output_tokens": 200, "credit_consumed": 0.005, "wall_time_ms": 500},
            state_evaluation={
                "structural_fidelity_score": task_context.structural_fidelity_score,
                "constraint_violations": task_context.constraint_violations,
                "validation_status": task_context.validation_status
            }
        )
        
        # Update modules with telemetry
        self.router.update_state(telemetry_packet)
        self.synergy_mesh.update_state(telemetry_packet)
        
        # 4. Forensics if needed
        if task_context.validation_status != "passed":
            report = self.forensics.process(task_id, [telemetry_packet])
            print(f"Forensics: Regret detected! Root cause: {report.root_cause_module}")
            self.self_extender.process(
                task_context.intent_profile.risk_class if task_context.intent_profile else "low",
                task_context.intent_profile.instruction_type if task_context.intent_profile else "other",
                report.regret_detected
            )

        # 5. Meta-learning cycle
        genome_update = self.genome_optimizer.process(telemetry_packet)
        if genome_update:
            self.dashboard.process("genome", genome_update)

        # 6. Red-teaming cycle
        probes = self.red_team.process(task_id)
        if probes:
            for probe in probes:
                # Run adversarial probes in shadow mode
                print(f"Red-Team: Running probe - {probe}")
                # In a real system, this would trigger a shadow execution
                self.red_team.record_probe_outcome(success=True)

        return {
            "task_id": task_id,
            "result": task_context.result,
            "status": task_context.validation_status,
            "fidelity_score": task_context.structural_fidelity_score
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NMO Ultimate Orchestrator")
    parser.add_argument("--request", type=str, required=True, help="User request prompt")
    args = parser.parse_args()

    orchestrator = NMOUltimateOrchestrator()
    asyncio.run(orchestrator.run_task(args.request))
