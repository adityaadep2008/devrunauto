import os
import json
import argparse
import asyncio
import sys
from dotenv import load_dotenv

# --- Integrations ---
from commerce_agent import CommerceAgent
from ride_comparison_agent import RideComparisonAgent

# --- DroidRun Imports ---
try:
    from droidrun.agent.droid import DroidAgent
    from droidrun.agent.utils.llm_picker import load_llm
    from droidrun.config_manager import DroidrunConfig, AgentConfig, ManagerConfig, ExecutorConfig, TelemetryConfig
except ImportError:
    print("CRITICAL ERROR: 'droidrun' library not found.")
    sys.exit(1)

load_dotenv()

class EventCoordinatorAgent:
    """
    Orchestrates an event: Invites guests, builds menu, and books logistics.
    """
    def __init__(self, provider="gemini", model="models/gemini-2.5-flash"):
        self.provider = provider
        self.model = model
        self.commerce_agent = CommerceAgent(provider, model)
        self.ride_agent = RideComparisonAgent(provider, model)
        self._ensure_api_keys()

    def _ensure_api_keys(self):
        if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
             print("[Warn] API Keys missing.")

    async def _run_whatsapp_task(self, phone_name: str, message: str):
        """Helper to send a WhatsApp message."""
        print(f"[Coordinator] 📨 Sending Invite to {phone_name}...")
        
        goal = (
            f"Open WhatsApp. "
            f"Tap the 'New Chat' or Search icon. "
            f"Search for contact '{phone_name}'. "
            f"Click on the contact to open chat. "
            f"Type the message: '{message}'. "
            f"Click Send. "
            f"Return success status."
        )

        # Config Setup (Simplified for brevity)
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        llm = load_llm("GoogleGenAI", self.model, api_key)
        config = DroidrunConfig(
            agent=AgentConfig(
                reasoning=True, 
                manager=ManagerConfig(vision=True), 
                executor=ExecutorConfig(vision=True)
            ),
            telemetry=TelemetryConfig(enabled=False)
        )
        
        agent = DroidAgent(goal=goal, llms=llm, config=config)
        
        try:
            await agent.run()
            return True
        except Exception as e:
            print(f"[Error] WhatsApp fail: {e}")
            return False

    async def invite_guests(self, guest_list: list, event_details: str):
        """
        Sends invites to a list of guests.
        guest_list: [{'name': 'Rahul', 'phone': '...'}]
        """
        print(f"\n[Coordinator] 📢 Starting Invitations...")
        
        invite_msg = f"Hey! You are invited to {event_details}. Please reply with your food preference (Veg/Non-Veg) and if you need a cab pickup."
        
        for guest in guest_list:
            await self._run_whatsapp_task(guest['name'], invite_msg)
            await asyncio.sleep(2) # Cooldown

    async def collect_preferences_and_build_menu(self):
        """
        Mock implementation for MVP. 
        In real-world, this would scour WhatsApp chats for replies.
        """
        print(f"\n[Coordinator] 📋 Collecting Preferences...")
        await asyncio.sleep(1)
        
        # Mocking the AI decision from "chat analysis"
        menu = ["Butter Chicken", "Garlic Naan", "Paneer Tikka", "Coke"]
        print(f"[Coordinator] 🍽️ Finalized Menu: {menu}")
        return menu

    async def coordinate_logistics(self, guest_needs: list):
        """
        guest_needs: [{'name': 'Rahul', 'pickup': 'Connaught Place', 'drop': 'My Home'}]
        """
        print(f"\n[Coordinator] 🚕 Coordinating Transport...")
        
        for req in guest_needs:
            print(f"Booking ride for {req['name']}...")
            await self.ride_agent.book_cheapest_ride(req['pickup'], req['drop'])

    async def orchestrate_event(self, event_name, guests, logistics_reqs):
        print(f"=== 🎪 Event Coordinator Started: {event_name} ===")
        
        # 1. Invite
        await self.invite_guests(guests, event_name)
        
        # 2. Planning
        menu = await self.collect_preferences_and_build_menu()
        
        # 3. Execution (Food)
        print(f"\n[Coordinator] 🍔 Ordering Food...")
        for item in menu:
            # We use Swiggy as default for now, or could check both
            await self.commerce_agent.execute_task("Swiggy", item, "food", action="order")
        
        # 4. Execution (Rides)
        await self.coordinate_logistics(logistics_reqs)
        
        print(f"\n=== ✅ Event Setup Complete! ===")

async def main():
    # Example Data
    guests = [
        {"name": "Mom", "phone": "..."} 
        # Add real contacts here for testing
    ]
    
    logistics = [
        {"name": "Mom", "pickup": "Apollo Hospital", "drop": "Home"}
    ]
    
    agent = EventCoordinatorAgent()
    await agent.orchestrate_event("Birthday Bash @ 8PM", guests, logistics)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
