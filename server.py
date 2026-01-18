import asyncio
import json
import logging
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import Agents
from commerce_agent import CommerceAgent
from ride_comparison_agent import RideComparisonAgent
from pharmacy_agent import PharmacyAgent
from event_coordinator_agent import EventCoordinatorAgent

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DroidServer")

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Data Models
class TaskPayload(BaseModel):
    persona: str
    product: str = None
    pickup: str = None
    drop: str = None
    medicine: str = None
    # For Coordinator
    event_name: str = None
    guest_list: list = [] # [{'name':..., 'phone':...}]
    
@app.get("/")
async def root():
    return {"status": "DroidRun Server Running"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
            # Keep alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def run_agent_task(payload: TaskPayload):
    """
    Executes the agent logic based on persona.
    Broadcasts logs to WebSocket.
    """
    await manager.broadcast(f"🚀 Starting Executor for Persona: {payload.persona}")
    
    result = None
    
    try:
        if payload.persona == "shopper":
            agent = CommerceAgent(model="models/gemini-2.5-flash")
            await manager.broadcast(f"Searching for {payload.product} on Amazon/Flipkart...")
            # Note: Using default 'search' action for now. Could expose 'order' later.
            result = await agent.execute_task("Amazon", payload.product, "product") # Just Amazon for speed in demo or iter over list
            # To actually run comparison:
            # We recreate the main loop logic here roughly or allow agent to return multiple
            # For this simple server version, let's just check Amazon as a proxy for 'Best Deal' logic
            # OR ideally we run the full comparison. 
            # Let's run full comparison for robustness if possible, but keep it simple.
            # Let's assume CommerceAgent main() did the comparison. 
            # We will run Amazon first.
            if result['status'] == 'failed':
                 await manager.broadcast("Amazon failed, trying Flipkart...")
                 result = await agent.execute_task("Flipkart", payload.product, "product")
                 
        elif payload.persona == "rider":
            agent = RideComparisonAgent(model="models/gemini-2.5-flash")
            await manager.broadcast(f"Comparing rides from {payload.pickup} to {payload.drop}...")
            # Run comparison
            full_res = await agent.compare_rides(payload.pickup, payload.drop)
            result = full_res.get('best_deal', {"status": "failed"})
            
        elif payload.persona == "patient":
            agent = PharmacyAgent(model="models/gemini-2.5-flash")
            await manager.broadcast(f"Searching for medicine: {payload.medicine}...")
            full_res = await agent.compare_prices(payload.medicine, "patient")
            result = full_res.get('best_option', {"status": "failed"})

        elif payload.persona == "coordinator":
            agent = EventCoordinatorAgent(model="models/gemini-2.5-flash")
            await manager.broadcast(f"🎪 Orchestrating Event: {payload.event_name}")
            # Mocking logistics reqs for now or deriving from guest list
            logistics = [] 
            # In a real app, guest_list would have 'needs_cab' flag.
            
            await agent.orchestrate_event(payload.event_name, payload.guest_list, logistics)
            result = {"status": "success", "message": "Event Orchestration Complete"}

        # Broadcast Final Result
        if result:
            await manager.broadcast(f"✅ Task Complete. Result: {json.dumps(result, default=str)}")
        else:
            await manager.broadcast("❌ Task Failed or Returned No Data.")

    except Exception as e:
        logger.error(f"Task Error: {e}")
        await manager.broadcast(f"🔥 Error: {str(e)}")

@app.post("/task")
async def create_task(payload: TaskPayload):
    # Run in background
    asyncio.create_task(run_agent_task(payload))
    return {"status": "accepted", "message": "Task queued"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
