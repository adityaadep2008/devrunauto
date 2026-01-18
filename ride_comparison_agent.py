import os
import json
import argparse
import asyncio
import re
import sys
from dotenv import load_dotenv

# --- DroidRun Professional Architecture Imports ---
try:
    from droidrun.agent.droid import DroidAgent
    from droidrun.agent.utils.llm_picker import load_llm
    from droidrun.config_manager import DroidrunConfig, AgentConfig, ManagerConfig, ExecutorConfig, TelemetryConfig
except ImportError:
    print("CRITICAL ERROR: 'droidrun' library not found or incompatible version.")
    print("Please ensure you have installed it: pip install droidrun")
    sys.exit(1)

# Load environment variables
load_dotenv()

class RideComparisonAgent:
    """
    Agent to compare ride prices between Uber and Ola using DroidRun.
    Follows the Professional Architecture.
    """
    
    def __init__(self, provider="gemini", model="gemini-1.5-flash"):
        self.provider = provider
        self.model = model
        self._ensure_api_keys()

    def _ensure_api_keys(self):
        if self.provider == "gemini" and not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
             print("[Warn] GEMINI_API_KEY not found in env, checking GOOGLE_API_KEY")

    def _parse_price(self, price_str):
        """Robust price parsing utility handling currency symbols."""
        if not price_str: return float('inf')
        try:
            clean = str(price_str).lower().replace(',', '').replace('₹', '').replace('rs', '').replace('rs.', '').strip()
            match = re.search(r'\d+(\.\d+)?', clean)
            return float(match.group()) if match else float('inf')
        except:
            return float('inf')

    async def execute_task(self, app_name: str, pickup: str, drop: str, action: str = "compare") -> dict:
        """
        Executes a ride check task on a specific app.
        Action: 'compare' (view prices) or 'book' (book cheapest ride via Cash).
        """
        print(f"\n[RideAgent] Initializing Task for: {app_name} (Action: {action})")
        
        # Define Goal with specific instructions for each app and permission handling
        if app_name.lower() == "uber":
            ride_types = "Uber Go and Uber Moto"
        else:
            ride_types = "Ola Mini, Ola Auto, or Bike"

        if action == "book":
            goal = (
                f"Open the app '{app_name}'. "
                f"If a 'Location Permission' popup appears, click 'While using the app' or 'Allow'. "
                f"Click on 'Ride' or the search bar. "
                f"Enter pickup location: '{pickup}'. "
                f"Enter destination: '{drop}'. "
                f"Wait for ride options. "
                f"Select the CHEAPEST available ride (e.g., Moto or Mini). "
                f"Click 'Book' or 'Confirm'. "
                f"Change Payment Method to 'Cash' if not already selected. "
                f"Click 'Confirm Booking' or 'Request Ride'. "
                f"Return a strict JSON object with keys: 'status' (success/failed), 'driver_details' (if visible), 'eta'. "
            )
        else:
            goal = (
                f"Open the app '{app_name}'. "
                f"If a 'Location Permission' popup appears, click 'While using the app' or 'Allow'. "
                f"Click on 'Ride' or the search bar to start a booking. "
                f"Enter pickup location: '{pickup}'. "
                f"Enter destination: '{drop}'. "
                f"Wait for the ride options to load. "
                f"Visually SCAN the ride options for {ride_types}. "
                f"Extract the ride type, price, and ETA. "
                f"Return a strict JSON object with keys: 'app', 'ride_type', 'price', 'eta'. "
                f"Ensure strict JSON format."
            )

        # --- Professional Config Setup ---
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        
        # Determine Provider Name for LLM Picker
        provider_name = "GoogleGenAI" if self.provider == "gemini" else self.provider

        llm = load_llm(
            provider_name=provider_name,
            model=self.model,
            api_key=api_key
        )

        manager_config = ManagerConfig(vision=True)
        executor_config = ExecutorConfig(vision=True)
        
        agent_config = AgentConfig(
            reasoning=True,
            manager=manager_config,
            executor=executor_config
        )
        
        telemetry_config = TelemetryConfig(enabled=False)
        
        config = DroidrunConfig(
            agent=agent_config,
            telemetry=telemetry_config
        )

        agent = DroidAgent(
            goal=goal,
            llms=llm,
            config=config
        )

        result_data = {"app": app_name, "status": "failed", "data": {}, "numeric_price": float('inf')}

        try:
            print(f"[RideAgent] 🧠 Running Agent on {app_name}...")
            result = await agent.run()
            
            # --- Robust Output Parsing ---
            if result:
                 # Handle DroidAgent Event objects (reasoning field)
                if hasattr(result, 'reason'):
                     clean_json = str(result.reason).strip()
                else:
                     clean_json = str(result).strip()

                # XML tag cleanup
                if "<request_accomplished" in clean_json:
                    try:
                        clean_json = clean_json.split(">")[1].split("</request_accomplished>")[0].strip()
                    except IndexError:
                        pass
                
                # Markdown cleanup
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                
                if clean_json.startswith("{"):
                    try:
                        data = json.loads(clean_json)
                        result_data["data"] = data
                        result_data["status"] = "success"
                        # Extract numeric price for comparison
                        price_val = data.get("price", "inf")
                        result_data["numeric_price"] = self._parse_price(price_val)
                    except json.JSONDecodeError:
                        print(f"[Warn] JSON Decode Error: {clean_json}")
                else:
                     print(f"[Warn] Agent output was not JSON: {clean_json[:50]}...")
            
            return result_data

        except Exception as e:
            print(f"[Error] Task Execution Failed for {app_name}: {e}")
            return result_data

    async def compare_rides(self, pickup, drop, preference="cab"):
        apps = ["Uber", "Ola"]
        results = {}

        for app in apps:
            res = await self.execute_task(app, pickup, drop, preference)
            results[app] = res
            # Cooldown to allow app switching/closing
            await asyncio.sleep(3)

        # Comparison Logic
        print("\n--- Final Aggregated Results ---")
        best_deal = None
        min_price = float('inf')

        for app, res in results.items():
            if res["status"] == "success":
                price = res["numeric_price"]
                print(f"{app}: {res['data'].get('ride_type')} - {res['data'].get('price')} (Numeric: {price})")
                
                if price < min_price:
                    min_price = price
                    best_deal = res
            else:
                print(f"{app}: Failed to get data.")

        results["best_deal"] = best_deal

        if best_deal:
            print(f"\n🏆 Best Deal: {best_deal['app']} - {best_deal['data'].get('price')}")
        else:
            print("\n❌ Could not determine best deal.")
        
        return results

    async def book_cheapest_ride(self, pickup, drop):
        """
        High-level method to Find Cheapest -> Book It.
        """
        print(f"\n[RideAgent] 🤖 Autonomous Booking Sequence Initiated...")
        
        # 1. Compare
        results = await self.compare_rides(pickup, drop)
        best_deal = results.get("best_deal")
        
        if not best_deal:
            print("[Error] No valid rides found to book.")
            return None
        
        target_app = best_deal['app']
        price = best_deal['data'].get('price')
        print(f"[RideAgent] 🏆 Best Deal identified: {target_app} @ {price}. Proceeding to BOOK...")
        
        # 2. Book
        booking_result = await self.execute_task(target_app, pickup, drop, action="book")
        
        print(f"\n[RideAgent] Booking Status for {target_app}: {booking_result.get('status')}")
        if booking_result.get('status') == 'success':
             print(f"✅ Cab Booked! Driver Details: {booking_result['data'].get('driver_details')}")
        else:
             print("❌ Booking Failed.")

        return booking_result

async def main():
    parser = argparse.ArgumentParser(description="Ride Comparison Agent (Uber vs Ola)")
    parser.add_argument("--pickup", required=True, help="Pickup location")
    parser.add_argument("--drop", required=True, help="Drop location")
    parser.add_argument("--preference", default="cab", choices=["cab", "auto", "sedan"], help="Preferred ride type")
    args = parser.parse_args()

    # Use models/gemini-2.5-flash as per new standard
    agent = RideComparisonAgent(model="models/gemini-2.5-flash")
    await agent.compare_rides(args.pickup, args.drop, args.preference)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
