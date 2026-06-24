"""
NEXUS-MEOS OMEGA ULTIMATE v∞
The definitive, fully autonomous optimization operating layer for Manus AI.
"""
__version__ = "ultimate"
__author__ = "Manus AI"

from .nmo_core import INMOOptimizationModule, NMOBasicModule
from .orchestrator import NMOUltimateOrchestrator

__all__ = [
    "INMOOptimizationModule",
    "NMOBasicModule",
    "NMOUltimateOrchestrator"
]
