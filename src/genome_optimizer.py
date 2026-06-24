import json
import numpy as np
import copy
from typing import Any, Dict, List, Optional
from src.nmo_core import NMOBasicModule

class GenomeOptimizer(NMOBasicModule):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.genome = config["genome"]
        self.interval = config["learning"]["olympics_interval"]
        self.history = [] # Last 200 telemetry events
        self.task_counter = 0

    def _calculate_phi(self, telemetry_batch: List[Dict[str, Any]]) -> float:
        if not telemetry_batch:
            return 0.0
        
        utilities = []
        for t in telemetry_batch:
            q = t["state_evaluation"]["structural_fidelity_score"]
            p = 1.0 if t["state_evaluation"]["validation_status"] == "passed" else 0.0
            c = t["metrics"]["credit_consumed"]
            o = 0.0001 # Small constant for overhead
            u = (q * p) / (c + o)
            utilities.append(u)
        
        return float(np.mean(utilities))

    def _mutate_genome(self, genome: Dict[str, Any]) -> Dict[str, Any]:
        mutant = copy.deepcopy(genome)
        for key in mutant:
            if isinstance(mutant[key], (int, float)):
                # Gaussian noise perturbation
                mutant[key] *= (1 + np.random.normal(0, 0.05))
        return mutant

    def process(self, telemetry_packet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self.history.append(telemetry_packet)
        if len(self.history) > 200:
            self.history.pop(0)
        
        self.task_counter += 1
        if self.task_counter % self.interval == 0:
            return self._run_olympics()
        return None

    def _run_olympics(self) -> Dict[str, Any]:
        print("Genome Optimizer: Running Benchmark Olympics...")
        champion_phi = self._calculate_phi(self.history)
        best_mutant = self.genome
        best_phi = champion_phi
        
        for i in range(8):
            mutant = self._mutate_genome(self.genome)
            # In a real system, we'd replay the last 200 tasks with this mutant
            # Here we simulate the replay outcome
            mutant_phi = champion_phi * (1 + np.random.normal(0.01, 0.02))
            
            if mutant_phi > best_phi:
                best_phi = mutant_phi
                best_mutant = mutant
        
        improvement = (best_phi - champion_phi) / champion_phi if champion_phi > 0 else 0
        if improvement > 0.02:
            print(f"Genome Optimizer: New champion found! Improvement: {improvement:.2%}")
            self.genome = best_mutant
            # Persist new genome
            with open("config/genome.json", "w") as f:
                json.dump(self.genome, f, indent=2)
            return {"action": "GENOME_UPDATED", "improvement": improvement, "new_genome": self.genome}
        
        return {"action": "NO_CHANGE", "phi": champion_phi}

    def update_state(self, telemetry_data: Dict[str, Any]) -> None:
        pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "operational",
            "task_counter": self.task_counter,
            "current_genome": self.genome
        }
