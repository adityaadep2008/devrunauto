import os
import json
import argparse
import asyncio
import re
from dotenv import load_dotenv

# Conforming to STRICT user documentation example
try:
    from droidrun import DroidAgent
    from droidrun.config_manager import DroidrunConfig
except ImportError:
    DroidAgent = None
    DroidrunConfig = None

# Load environment variables
load_dotenv()

def parse_price(price_str):
    try:
        clean = str(price_str).replace(',', '').strip()
        match = re.search(r'\d+(\.\d+)?', clean)
        return float(match.group()) if match else float('inf')
    except:
        return float('inf')

def parse_rating(rating_str):
    try:
        clean = str(rating_str).strip()
        match = re.search(r'\d+(\.\d+)?', clean)
        return float(match.group()) if match else 0.0
    except:
        return 0.0

async def perform_search(app_name, query, item_type="product"):
    """
    Executes a DroidAgent run for a specific app search.
    """
    if DroidAgent is None:
         raise ImportError("droidrun library not found. Please install it.")

    print(f"\n[Status] Initializing Agent for {app_name}...")
    
    # Configure Goal based on Doc example
    # Combining Open, Search, Extraction into one Agent Goal
    task_goal = (
        f"Open {app_name}. Search for '{query}'. "
        f"Look at the search results and find the best {item_type}s. "
        "Return a JSON list of the top 3 items with keys: title, price, rating. "
        "The output must be a valid JSON string."
    )
    
    # Initialize Config
    # Assuming config picks up env vars (GOOGLE_API_KEY) automatically or defaults
    config = DroidrunConfig()
    
    # Create Agent
    agent = DroidAgent(
        goal=task_goal,
        config=config
    )
    
    print(f"[Run] Executing Agent for {app_name}...")
    # Run Agent (Async)
    output = await agent.run()
    
    # Parse Result
    result_data = {
        "platform": app_name,
        "status": "failed",
        "items": [],
        "best_item": None,
        "raw_response": str(output)
    }
    
    try:
        # Expecting the agent to return the extracted text/JSON as the result
        # Parsing logic remains similar to handle potential Markdown
        json_str = str(output).strip()
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
             json_str = json_str.split("```")[1].split("```")[0].strip()
        
        # Heuristic: if output is bare list [ ... ]
        if json_str.startswith('[') or json_str.startswith('{'):
             items = json.loads(json_str)
             if isinstance(items, dict): items = [items] # handle single item
             
             valid_items = []
             for item in items:
                item['numeric_price'] = parse_price(item.get('price', '999999'))
                item['numeric_rating'] = parse_rating(item.get('rating', '0'))
                if item['numeric_price'] > 0:
                    valid_items.append(item)
                    
             result_data["items"] = valid_items
             result_data["status"] = "success"
             
             if valid_items:
                 valid_items.sort(key=lambda x: (x['numeric_price'], -x['numeric_rating']))
                 result_data["best_item"] = valid_items[0]
                 
    except Exception as e:
        print(f"[{app_name}] Parsing Error: {e}")
        
    return result_data

async def main_async():
    parser = argparse.ArgumentParser(description="DroidRun Commerce Agent (Async)")
    parser.add_argument("--task", choices=['shopping', 'food'], default='shopping', help="Type of task")
    parser.add_argument("--query", required=True, help="Item to search for")
    
    args = parser.parse_args()
    
    platforms = []
    item_type = "product"
    if args.task == "shopping":
        platforms = ["Amazon", "Flipkart"]
        item_type = "product"
    elif args.task == "food":
        platforms = ["Zomato", "Swiggy"]
        item_type = "food"
        
    results = {}
    
    # Run sequentially or in parallel?
    # DroidRun controls one device. Parallel execution on ONE device is impossible/confusing.
    # Must run sequentially.
    
    for plat in platforms:
        res = await perform_search(plat, args.query, item_type)
        results[plat.lower()] = res
        
    # Comparison Logic
    param1 = results.get(platforms[0].lower(), {}).get('best_item')
    param2 = results.get(platforms[1].lower(), {}).get('best_item')
    
    best_platform = None
    recommendation = "No valid items found."
    
    if param1 and param2:
        if param1['numeric_price'] < param2['numeric_price']:
            best_platform = platforms[0]
            recommendation = f"{platforms[0]} is cheaper."
        elif param2['numeric_price'] < param1['numeric_price']:
            best_platform = platforms[1]
            recommendation = f"{platforms[1]} is cheaper."
        else:
             if param1['numeric_rating'] > param2['numeric_rating']:
                best_platform = platforms[0]
                recommendation = f"Prices equal, but {platforms[0]} has better rating."
             else:
                best_platform = platforms[1]
                recommendation = f"Prices equal, but {platforms[1]} has better rating."
    elif param1:
        best_platform = platforms[0]
        recommendation = f"Only found on {platforms[0]}."
    elif param2:
        best_platform = platforms[1]
        recommendation = f"Only found on {platforms[1]}."

    final_output = {
        "query": args.query,
        "category": args.task,
        "winner_platform": best_platform,
        "recommendation": recommendation,
        "details": results
    }
    
    print(json.dumps(final_output, indent=2))

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
