import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import networkx as nx
from typing import Any, Dict, List, Optional
from src.nmo_core import NMOBasicModule

class SageLayer(nn.Module):
    def __init__(self, in_features, out_features):
        super().__init__()
        self.linear = nn.Linear(in_features * 2, out_features)

    def forward(self, x, adj):
        # x: [num_nodes, in_features]
        # adj: [num_nodes, num_nodes]
        neighbor_agg = torch.mm(adj, x) / (adj.sum(1, keepdim=True) + 1e-6)
        combined = torch.cat([x, neighbor_agg], dim=1)
        return F.relu(self.linear(combined))

class SynergyGNNModel(nn.Module):
    def __init__(self, num_nodes, feature_dim, hidden_dim):
        super().__init__()
        self.conv1 = SageLayer(feature_dim, hidden_dim)
        self.conv2 = SageLayer(hidden_dim, hidden_dim)
        self.predictor = nn.Linear(hidden_dim * 2, 1) # Predict quality for a pair

    def forward(self, x, adj, node_indices):
        # x: [num_nodes, feature_dim]
        # adj: [num_nodes, num_nodes]
        # node_indices: [2] indices of two nodes in the chain
        h = self.conv1(x, adj)
        h = self.conv2(h, adj)
        pair_features = torch.cat([h[node_indices[0]], h[node_indices[1]]], dim=0)
        return torch.sigmoid(self.predictor(pair_features))

class SynergyMesh(NMOBasicModule):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.num_layers = config["genome"]["gnn_layers"]
        self.skills = [] # List of skill names/slugs
        self.skill_to_idx = {}
        self.graph = nx.DiGraph()
        self.feature_dim = 32
        self.hidden_dim = 64
        self.model = None
        self.optimizer = None
        self.replay_buffer = deque(maxlen=2000) # (node_indices, actual_utility)
        
        # Initial skills from Skill Hunter (simulated)
        self._initialize_mesh(["web-scraper", "code-analyzer", "pdf-parser", "data-visualizer"])

    def _initialize_mesh(self, initial_skills: List[str]) -> None:
        self.skills = initial_skills
        self.skill_to_idx = {skill: i for i, skill in enumerate(self.skills)}
        num_nodes = len(self.skills)
        
        for i in range(num_nodes):
            for j in range(num_nodes):
                if i != j:
                    self.graph.add_edge(i, j, weight=1.0) # Initial weight

        self.node_features = torch.randn(num_nodes, self.feature_dim)
        self.model = SynergyGNNModel(num_nodes, self.feature_dim, self.hidden_dim)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.01)

    def predict_chain_utility(self, chain: List[str], context: Any) -> float:
        if len(chain) < 2:
            return 1.0
        
        # Convert chain names to indices
        indices = [self.skill_to_idx.get(s) for s in chain if s in self.skill_to_idx]
        if len(indices) < 2:
            return 0.5
        
        adj = torch.from_numpy(nx.to_numpy_array(self.graph)).float()
        
        total_utility = 0.0
        self.model.eval()
        with torch.no_grad():
            for i in range(len(indices) - 1):
                pair = [indices[i], indices[i+1]]
                utility = self.model(self.node_features, adj, pair)
                total_utility += utility.item()
        
        return total_utility / (len(indices) - 1)

    def update_state(self, telemetry_data: Dict[str, Any]) -> None:
        # telemetry_data should contain "tool_chain" and "utility"
        chain = telemetry_data.get("tool_chain", [])
        actual_utility = telemetry_data.get("state_evaluation", {}).get("structural_fidelity_score", 0.0)
        
        if len(chain) < 2:
            return

        indices = [self.skill_to_idx.get(s) for s in chain if s in self.skill_to_idx]
        if len(indices) < 2:
            return

        for i in range(len(indices) - 1):
            self.replay_buffer.append(([indices[i], indices[i+1]], actual_utility))
            # Update graph weight
            current_weight = self.graph[indices[i]][indices[i+1]]['weight']
            self.graph[indices[i]][indices[i+1]]['weight'] = 0.9 * current_weight + 0.1 * actual_utility

        # Online training every 10 updates
        if len(self.replay_buffer) % 10 == 0:
            self._train_step()

    def _train_step(self) -> None:
        if len(self.replay_buffer) < 32:
            return
            
        self.model.train()
        batch_indices = np.random.choice(len(self.replay_buffer), 32, replace=False)
        adj = torch.from_numpy(nx.to_numpy_array(self.graph)).float()
        
        total_loss = 0
        for idx in batch_indices:
            pair, target = self.replay_buffer[idx]
            self.optimizer.zero_grad()
            prediction = self.model(self.node_features, adj, pair)
            loss = F.mse_loss(prediction, torch.tensor([target]).float())
            loss.backward()
            self.optimizer.step()
            total_loss += loss.item()

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "operational",
            "nodes_count": len(self.skills),
            "replay_buffer_size": len(self.replay_buffer)
        }

from collections import deque
