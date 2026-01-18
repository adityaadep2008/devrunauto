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

load_dotenv()

class PharmacyAgent:
    """
    Agent to compare medicine prices across PharmEasy, Apollo 24|7, and Tata 1mg.
    Follows the Professional Architecture.
    """
    
    def __init__(self, provider="gemini", model="models/gemini-2.5-flash"):
        self.provider = provider
        self.model = model
        self._ensure_api_keys()

    def _ensure_api_keys(self):
        if self.provider == "gemini" and not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
             print("[Warn] GEMINI_API_KEY not found in env, checking GOOGLE_API_KEY")

    def _parse_price(self, price_str):
        if not price_str: return float('inf')
        try:
            clean = str(price_str).lower().replace(',', '').replace('₹', '').replace('rs', '').replace('rs.', '').strip()
            match = re.search(r'\d+(\.\d+)?', clean)
            return float(match.group()) if match else float('inf')
        except:
            return float('inf')

    async def execute_task(self, app_name: str, medicine: str, role: str) -> dict:
        print(f"\n[PharmaAgent] Initializing Task for: {app_name} - {medicine} ({role} mode)")
        
        # Mode-specific instructions
        if role == "pharmacist":
            search_instruction = (
                f"Search for '{medicine}'. "
                f"Look specifically for 'bulk packs', 'combo packs', 'wholesale', or largest available strip sizes suitable for restocking. "
                f"If bulk options aren't explicitly labeled, find the standard pack with the best value."
            )
            report_instruction = "Report the Price per pack/unit."
        else:
            search_instruction = f"Search for '{medicine}'. Identify the exact medicine matching the name and dosage."
            report_instruction = "Report the Price."

        goal = (
            f"Open the app '{app_name}'. "
            f"If a 'Location Permission' popup appears, click 'While using the app' or 'Allow'. "
            f"Click on the search bar. "
            f"{search_instruction} "
            f"Visually identify the best result. "
            f"Extract the Price (numeric value). "
            f"Return a strict JSON object with keys: 'app', 'medicine', 'price', 'details'. "
            f"Ensure strict JSON format."
        )

        # --- Professional Config Setup ---
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
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

        result_data = {"app": app_name, "medicine": medicine, "status": "failed", "data": {}, "numeric_price": float('inf')}

        try:
            print(f"[PharmaAgent] 🧠 Running Agent on {app_name} for {medicine}...")
            result = await agent.run()
            
            # --- Robust Output Parsing ---
            if result:
                if hasattr(result, 'reason'):
                     clean_json = str(result.reason).strip()
                elif hasattr(result, 'message'):
                     clean_json = str(result.message).strip()
                else:
                     clean_json = str(result).strip()

                if "<request_accomplished" in clean_json:
                    try:
                        clean_json = clean_json.split(">")[1].split("</request_accomplished>")[0].strip()
                    except IndexError:
                        pass

                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                
                if clean_json.startswith("{"):
                    try:
                        data = json.loads(clean_json)
                        result_data["data"] = data
                        result_data["status"] = "success"
                        result_data["numeric_price"] = self._parse_price(data.get("price"))
                    except json.JSONDecodeError:
                        print(f"[Warn] JSON Decode Error: {clean_json}")
                else:
                     print(f"[Warn] Agent output was not JSON: {clean_json[:50]}...")
            
            return result_data

        except Exception as e:
            print(f"[Error] Task Execution Failed for {app_name}: {e}")
            return result_data

    async def compare_prices(self, meds_str, role, apps_filter=None):
        all_apps = ["PharmEasy", "Apollo 24|7", "Tata 1mg"]
        
        if apps_filter:
            # Filter logic: simple case-insensitive partial match
            apps = []
            for requested in apps_filter:
                match = next((a for a in all_apps if requested.lower() in a.lower()), None)
                if match:
                    apps.append(match)
                else:
                    print(f"[Warn] App '{requested}' not supported. Available: {all_apps}")
            if not apps:
                print("[Error] No valid apps selected. Using default list.")
                apps = all_apps
        else:
            apps = all_apps

        # Parse medicines: "Name:Qty, Name:Qty"
        med_list = []
        for item in meds_str.split(','):
            parts = item.strip().split(':')
            name = parts[0].strip()
            qty = int(parts[1].strip()) if len(parts) > 1 else 1
            med_list.append({"name": name, "qty": qty})

        print(f"\n[PharmaAgent] processing List: {med_list}")
        print(f"[PharmaAgent] Apps Selected: {apps}")
        
        app_totals = {} # {app_name: {total_cost: float, items: [details]}}

        for app in apps:
            print(f"\n--- Checking {app} ---")
            total_cost = 0.0
            item_details = []
            all_found = True

            for med in med_list:
                res = await self.execute_task(app, med['name'], role)
                
                if res["status"] == "success":
                    price = res["numeric_price"]
                    qty = med['qty']
                    line_total = price * qty
                    total_cost += line_total
                    item_details.append({
                        "name": med['name'],
                        "unit_price": price,
                        "qty": qty,
                        "line_total": line_total,
                        "details": res['data'].get("details", "")
                    })
                    print(f"  > Found {med['name']} @ {price} x {qty} = {line_total}")
                else:
                    print(f"  > Failed to find {med['name']}")
                    all_found = False
                    break # Stop if one item not found, basket incomplete
                
                # Small cooldown between searches
                await asyncio.sleep(2)

            if all_found:
                app_totals[app] = {"total_cost": total_cost, "items": item_details}
            else:
                app_totals[app] = {"status": "incomplete"}
                print(f"  > Basket incomplete for {app}")
            
            # Cooldown betwen apps
            await asyncio.sleep(3)

        print(f"\n--- Final Aggregated Basket Results ---")
        best_option = None
        min_total = float('inf')

        for app, result in app_totals.items():
            if result.get("status") != "incomplete":
                total = result["total_cost"]
                print(f"{app}: Total Basket = ₹{total:.2f}")
                for item in result["items"]:
                    print(f"  - {item['name']}: ₹{item['unit_price']} x {item['qty']}")
                
                if total < min_total:
                    min_total = total
                    best_option = {"app": app, "total": total, "items": result["items"]}
            else:
                print(f"{app}: Incomplete Basket")

        if best_option:
            print(f"\n🏆 Best Basket Deal: {best_option['app']} - ₹{best_option['total']:.2f}")
        else:
            print("\n❌ Could not determine best basket option.")

async def main():
    parser = argparse.ArgumentParser(description="Pharmacy Agent (Basket Comparison)")
    parser.add_argument("--meds", required=True, help="List of medicines 'Name:Qty, Name:Qty'")
    parser.add_argument("--role", choices=['patient', 'pharmacist'], default='patient', help="User role")
    parser.add_argument("--apps", help="Comma-separated list of apps to use (e.g., 'Tata, Apollo')")
    args = parser.parse_args()

    apps_filter = [a.strip() for a in args.apps.split(',')] if args.apps else None
    
    agent = PharmacyAgent(model="models/gemini-2.5-flash")
    await agent.compare_prices(args.meds, args.role, apps_filter)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
