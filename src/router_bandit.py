import numpy as np
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from collections import deque
from src.nmo_core import NMOBasicModule

class ModelTrackState(BaseModel):
    id: str
    cost_per_m_input: float
    cost_per_m_output: float
    features: np.ndarray  # latent representation of track capabilities
    A: np.ndarray  # covariance matrix for LinUCB
    b: np.ndarray  # reward vector
    quality_history: deque = Field(default_factory=lambda: deque(maxlen=50)) # (score, success) tuples

    class Config:
        arbitrary_types_allowed = True

class RouterBandit(NMOBasicModule):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.alpha = config["genome"]["ucb_alpha"]
        self.tracks: Dict[str, ModelTrackState] = {}
        self._initialize_tracks()

    def _initialize_tracks(self) -> None:
        for track_cfg in self.config["model_tracks"]:
            track_id = track_cfg["id"]
            # Latent features: [cost_norm, priority_norm, code_cap, reasoning_cap, multi_cap]
            features = np.array([
                track_cfg["cost_per_million_input"] / 10.0,
                track_cfg["priority"] / 2.0,
                1.0 if "code" in track_cfg["capabilities"] else 0.0,
                1.0 if "reasoning" in track_cfg["capabilities"] else 0.0,
                1.0 if "multilingual" in track_cfg["capabilities"] else 0.0
            ])
            # For LinUCB, context vector size must match features size (or be derived from it)
            # Here we assume context vector is derived from ComplexityIntentProfile
            # Context size: [complexity, density, deps, token_vol, risk_low, risk_med, risk_high]
            context_dim = 7 
            self.tracks[track_id] = ModelTrackState(
                id=track_id,
                cost_per_m_input=track_cfg["cost_per_million_input"],
                cost_per_m_output=track_cfg["cost_per_million_output"],
                features=features,
                A=np.identity(context_dim),
                b=np.zeros(context_dim)
            )

    def _get_context_vector(self, intent_profile: Any) -> np.ndarray:
        # Context size: [complexity, density, deps, token_vol, risk_low, risk_med, risk_high]
        risk_map = {"low": [1, 0, 0], "medium": [0, 1, 0], "high": [0, 0, 1]}
        risk_vec = risk_map.get(intent_profile.risk_class, [0, 0, 0])
        
        ctx = np.array([
            intent_profile.cyclomatic_complexity / 50.0,
            intent_profile.ast_density_score / 10.0,
            intent_profile.external_dependency_count / 10.0,
            intent_profile.token_volume / 10000.0,
            risk_vec[0],
            risk_vec[1],
            risk_vec[2]
        ])
        return ctx

    def process(self, intent_profile: Any) -> str:
        x_t = self._get_context_vector(intent_profile)
        best_track_id = ""
        max_ucb = -float('inf')

        # Safety override: Exclude tracks with high failure rate
        available_tracks = []
        for tid, track in self.tracks.items():
            if len(track.quality_history) >= 10:
                success_rate = sum(1 for _, success in track.quality_history if success) / len(track.quality_history)
                if success_rate < 0.8: # Failure rate > 20%
                    continue
            available_tracks.append(tid)
        
        if not available_tracks:
            # Fallback to ultra-fidelity if all failing
            return "ultra-fidelity-model-v3"

        for tid in available_tracks:
            track = self.tracks[tid]
            A_inv = np.linalg.inv(track.A)
            theta = A_inv @ track.b
            p_t = theta.T @ x_t + self.alpha * np.sqrt(x_t.T @ A_inv @ x_t)
            
            if p_t > max_ucb:
                max_ucb = p_t
                best_track_id = tid
        
        return best_track_id

    def update_state(self, telemetry_data: Dict[str, Any]) -> None:
        track_id = telemetry_data["execution_track"]
        if track_id not in self.tracks:
            return

        track = self.tracks[track_id]
        # Reward U = (Q * P) / (C + O)
        # For simplicity, use structural_fidelity_score as reward
        reward = telemetry_data["state_evaluation"]["structural_fidelity_score"]
        success = telemetry_data["state_evaluation"]["validation_status"] == "passed"
        
        # Update LinUCB A and b
        # We need the context vector used for this decision. 
        # In a real system, we'd store it or recompute it.
        # Here we recompute (assuming intent_profile is available in telemetry or re-passed)
        # For now, simulate a context vector update
        x_t = np.random.rand(7) # Placeholder
        track.A += np.outer(x_t, x_t)
        track.b += reward * x_t
        track.quality_history.append((reward, success))

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "operational",
            "tracks_count": len(self.tracks),
            "alpha": self.alpha
        }
