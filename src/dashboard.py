from fastapi import FastAPI, WebSocket
from typing import List, Dict, Any
import asyncio
import json
from src.nmo_core import NMOBasicModule

app = FastAPI()

class DashboardServer(NMOBasicModule):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.port = config["nmo_system_profile"]["dashboard_port"]
        self.decision_queue = asyncio.Queue()
        self.telemetry_queue = asyncio.Queue()
        self.alert_queue = asyncio.Queue()
        self.genome_queue = asyncio.Queue()

    async def broadcast_decisions(self, websocket: WebSocket):
        await websocket.accept()
        while True:
            data = await self.decision_queue.get()
            await websocket.send_json(data)

    async def broadcast_telemetry(self, websocket: WebSocket):
        await websocket.accept()
        while True:
            data = await self.telemetry_queue.get()
            await websocket.send_json(data)

    async def broadcast_alerts(self, websocket: WebSocket):
        await websocket.accept()
        while True:
            data = await self.alert_queue.get()
            await websocket.send_json(data)

    async def broadcast_genome(self, websocket: WebSocket):
        await websocket.accept()
        while True:
            data = await self.genome_queue.get()
            await websocket.send_json(data)

    def process(self, event_type: str, data: Dict[str, Any]) -> None:
        # In a real system, this would push to the queues
        # Since this is a module within the hypervisor, it receives events to display
        if event_type == "decision":
            self.decision_queue.put_nowait(data)
        elif event_type == "telemetry":
            self.telemetry_queue.put_nowait(data)
        elif event_type == "alert":
            self.alert_queue.put_nowait(data)
        elif event_type == "genome":
            self.genome_queue.put_nowait(data)

    def update_state(self, telemetry_data: Dict[str, Any]) -> None:
        pass

    def get_status(self) -> Dict[str, Any]:
        return {"status": "operational", "port": self.port}

@app.websocket("/ws/decisions")
async def websocket_decisions(websocket: WebSocket):
    # This would need access to the DashboardServer instance
    pass

@app.get("/health")
async def health():
    return {"status": "ok"}
