import pytest
import asyncio
import os
import json
from src.orchestrator import NMOUltimateOrchestrator
from src.hypervisor import TaskStateEnum

@pytest.fixture
def orchestrator():
    # Ensure config exists
    config_path = "config/production_agent_spec.json"
    if not os.path.exists(config_path):
        os.makedirs("config", exist_ok=True)
        # Write default config for testing if missing
        pass 
    return NMOUltimateOrchestrator(config_path)

@pytest.mark.asyncio
async def test_full_execution_flow(orchestrator):
    prompt = "Create a python script that calculates Fibonacci numbers. Must not use external libraries."
    result = await orchestrator.run_task(prompt)
    
    assert "task_id" in result
    assert result["status"] in ["passed", "failed", "vetoed"]
    assert "fidelity_score" in result
    assert result["fidelity_score"] >= 0.0

@pytest.mark.asyncio
async def test_overhead_short_circuit(orchestrator):
    # Very short prompt should trigger fast-pass
    prompt = "Hello"
    result = await orchestrator.run_task(prompt)
    
    # Check if it was processed as a fast-pass
    task_id = result["task_id"]
    task_context = orchestrator.hypervisor.active_tasks[task_id]
    assert task_context.structural_fidelity_score == 1.0
    assert task_context.validation_status == "passed"

@pytest.mark.asyncio
async def test_rollback_mechanism(orchestrator):
    # Mock a failure to trigger rollback
    prompt = "Complex task that might fail"
    
    # Disable overhead analyzer for this test to force full execution
    orchestrator.hypervisor.overhead_analyzer = None
    
    # Force failure in validator for this test
    class FailingValidator:
        def process(self, output, intent_profile):
            return {
                "structural_fidelity_score": 0.4,
                "constraint_violations": ["Simulated failure"],
                "validation_status": "vetoed"
            }
            
    orchestrator.hypervisor.validator = FailingValidator()
    
    # Run via hypervisor directly to ensure we catch the state change
    task_id = orchestrator.hypervisor.process(prompt, [])
    task_context = orchestrator.hypervisor.active_tasks[task_id]
    
    # Should have at least one retry/rollback
    assert task_context.retry_count > 0
    assert task_context.state == TaskStateEnum.COMPLETED

def test_config_loading(orchestrator):
    assert orchestrator.config["version"] == "ultimate"
    assert "nmo_system_profile" in orchestrator.config
    assert len(orchestrator.config["model_tracks"]) > 0

def test_telemetry_logging(orchestrator):
    log_file = "logs/runtime_trace.log"
    if os.path.exists(log_file):
        os.remove(log_file)
    
    # Run a task to generate telemetry
    asyncio.run(orchestrator.run_task("Test telemetry"))
    
    assert os.path.exists(log_file)
    with open(log_file, "r") as f:
        line = f.readline()
        data = json.loads(line)
        assert "event_id" in data
        assert "task_id" in data
        assert "metrics" in data
