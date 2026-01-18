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
    from droidrun.config_manager import DroidrunConfig
except ImportError:
    print("CRITICAL ERROR: 'droidrun' library not found or incompatible version.")
    print("Please ensure you have installed it: pip install droidrun")
    sys.exit(1)

# Load environment variables
load_dotenv()

class CommerceAgent:
    """
    Professional Commerce Agent using DroidRun Framework.
    Follows the 'Brain' (Host) and 'Senses' (Portal) architecture.
    """
    
    def __init__(self, provider="gemini", model="gemini-1.5-flash"):
        self.provider = provider
        self.model = model
        self._ensure_api_keys()

    def _ensure_api_keys(self):
        if self.provider == "gemini" and not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
             # Fallback check
             print("[Warn] GEMINI_API_KEY not found in env, checking GOOGLE_API_KEY")

    def _parse_price(self, price_str):
        """Robust price parsing utility."""
        if not price_str: return float('inf')
        try:
            clean = str(price_str).lower().replace(',', '').replace('₹', '').replace('rs', '').replace('rs.', '').strip()
            match = re.search(r'\d+(\.\d+)?', clean)
            return float(match.group()) if match else float('inf')
        except:
            return float('inf')

    async def execute_task(self, app_name: str, query: str, item_type: str, action: str = "search") -> dict:
        """
        Spawns a DroidAgent to execute a specific commerce task.
        Uses Vision capabilities for better UI understanding.
        Action: 'search' (compare prices) or 'order' (buy item via COD).
        """
        print(f"\n[CommerceAgent] Initializing Task for: {app_name} (Action: {action})")
        
        # 1. Define Goal (Natural Language with Structural Constraints)
        if action == "order":
            goal = (
                f"Open the app '{app_name}'. "
                f"Search for '{query}'. "
                f"Select the first relevant item. "
                f"Click 'Add' or 'Add to Cart'. "
                f"Go to View Cart / Checkout. "
                f"Proceed to Pay. "
                f"Select 'Cash on Delivery' (COD) or 'Pay on Delivery' as payment method. "
                f"Click 'Place Order' or 'Confirm Order'. "
                f"Return a strict JSON object with keys: 'status' (success/failed), 'order_id' (if visible), 'final_price'. "
            )
        else:
            goal = (
                f"Open the app '{app_name}'. "
                f"Search for '{query}'. "
                f"Wait for the search results to load. "
                f"Visually SCAN the search results. "
                f"Identify multiple items matching '{query}'. "
                f"COMPARE their prices and Select the CHEAPEST option. "
                f"Extract the following details for the CHEAPEST item: "
                f"1. Product Name (title) "
                f"2. Price (numeric value) "
                f"3. Rating "
                f"4. Restaurant Name "
                f"Return a strict JSON object with keys: 'title', 'price', 'rating', 'restaurant'. "
                f"If no exact match is found, find the closest match. "
            )

        # 2. Configure Agent (Professional Pattern)
        # Using Vision for robustness against custom UI (Flutter/React Native)
        # 2. Configure Agent (Professional Pattern)
        # Using load_llm to avoid DroidrunConfig error
        from droidrun.agent.utils.llm_picker import load_llm
        from droidrun.config_manager import DroidrunConfig, AgentConfig, ManagerConfig, ExecutorConfig, TelemetryConfig
        
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        llm = load_llm(
            provider_name="GoogleGenAI",
            model=self.model,
            api_key=api_key
        )

        # Create properly typed config
        # Enable vision for Manager (planning) and Executor (acting)
        manager_config = ManagerConfig(vision=True)
        executor_config = ExecutorConfig(vision=True)
        
        agent_config = AgentConfig(
            reasoning=True,
            manager=manager_config,
            executor=executor_config
        )
        
        # Disable telemetry to avoid "multiple values for distinct_id" error
        telemetry_config = TelemetryConfig(enabled=False)
        
        config = DroidrunConfig(
            agent=agent_config,
            telemetry=telemetry_config
        )

        agent = DroidAgent(
            goal=goal,
            llms=llm,
            config=config,
        )

        # 3. Execute
        start_data = {"platform": app_name, "status": "failed", "data": {}}
        try:
            print(f"[CommerceAgent] 🧠 Running Agent Logic...")
            result = await agent.run()
            print(f"[DEBUG] Raw Agent Result type: {type(result)}")
            print(f"[DEBUG] Raw Agent Result: {result}")
            
            # 4. Parse Output
            if result:
                # Handle DroidAgent Event objects
                if hasattr(result, 'reason'):
                     clean_json = str(result.reason).strip()
                else:
                     clean_json = str(result).strip()
                
                print(f"[DEBUG] Processing result string: {clean_json[:100]}...")

                # XML tag cleanup (common with DroidRun Reasoning)
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
                
                # Heuristic validation
                if clean_json.startswith("{"):
                    try:
                         data = json.loads(clean_json)
                         start_data["data"] = data
                         start_data["status"] = "success"
                         start_data["data"]["numeric_price"] = self._parse_price(data.get("price"))
                         # Ensure restaurant key exists
                         if "restaurant" not in start_data["data"]:
                              start_data["data"]["restaurant"] = "Unknown"
                    except json.JSONDecodeError:
                         print(f"[Warn] JSON Decode Error: {clean_json}")
                else:
                     print(f"[Warn] Agent output was not JSON: {clean_json[:50]}...")
            else:
                 print("[Warn] Agent returned None result.")
            
            return start_data

        except Exception as e:
            print(f"[Error] Task Execution Failed: {e}")
            return start_data

async def main():
    parser = argparse.ArgumentParser(description="BestBuy-Agent: Commerce Automation (DroidRun)")
    parser.add_argument("--task", choices=['shopping', 'food'], default='shopping')
    parser.add_argument("--query", required=True)
    args = parser.parse_args()

    # Domain Configuration
    if args.task == "shopping":
        platforms = ["Amazon", "Flipkart"]
        item_type = "product"
    else:
        platforms = ["Zomato", "Swiggy"]
        item_type = "food item"

    # Initialize Controller
    # Using 2.5 Flash as recommended by quotas
    commerce_bot = CommerceAgent(provider="gemini", model="models/gemini-2.5-flash")
    
    results = {}

    # Sequential Execution (Single Device limitation)
    for platform in platforms:
        res = await commerce_bot.execute_task(platform, args.query, item_type)
        results[platform.lower()] = res
        # Brief cooldown for app switching stability
        await asyncio.sleep(2)

    # Output (Stdout for Backend Integration)
    
    # Calculate Victor
    zomato_res = results.get('zomato', {})
    swiggy_res = results.get('swiggy', {})
    
    z_price = float('inf')
    s_price = float('inf')
    
    if zomato_res.get('status') == 'success':
        z_price = zomato_res['data'].get('numeric_price', float('inf'))
        
    if swiggy_res.get('status') == 'success':
         s_price = swiggy_res['data'].get('numeric_price', float('inf'))
         
    victor = None
    if z_price < s_price:
        victor = {
            "platform": "Zomato",
            "details": zomato_res['data']
        }
    elif s_price < z_price:
         victor = {
            "platform": "Swiggy",
            "details": swiggy_res['data']
        }
    elif s_price == z_price and s_price != float('inf'):
         victor = {
            "platform": "Tie",
            "details": swiggy_res['data']
        }
    else:
        victor = "No valid data found"
        
    results["victor"] = victor

    print("\n--- Final Aggregated Results ---")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())