# DroidRun Auto - Commerce & Service Agents

This project implements intelligent autonomous agents using the [DroidRun](https://github.com/droidrun/droidrun) framework. These agents leverage key-less signing, advanced vision, and reasoning capabilities (powered by Google Gemini 2.5 Flash) to automate complex tasks across multiple Android applications.

## 🤖 Available Agents

### 1. Commerce Agent (Food Delivery)
**Script**: `commerce_agent.py`
**Goal**: Compare food prices across **Swiggy** and **Zomato** to find the cheapest option ("Victor").

**Key Features**:
- **Multi-App Orchestration**: Navigates both apps seamlessly.
- **Smart Parsing**: Extracts restaurant names, ratings, and prices even from complex UIs.
- **Victor Logic**: Automatically identifies the best deal.

**Usage**:
```bash
python commerce_agent.py --task food --query "Masala Dosa"
```

---

### 2. Rider Agent (Ride Sharing)
**Script**: `ride_comparison_agent.py`
**Goal**: Compare ride prices between **Uber** and **Ola** for a specific route.

**Key Features**:
- **Preference Filtering**: prioritize specific vehicle types (`auto`, `sedan`, `cab`).
- **Dynamic Prompting**: Customizes visual search based on your preference.

**Usage**:
```bash
# Default (Compare Cabs)
python ride_comparison_agent.py --pickup "Home" --drop "Office"

# Prefer Auto/Rickshaw
python ride_comparison_agent.py --pickup "Current Location" --drop "Malls" --preference auto

# Prefer Sedans
python ride_comparison_agent.py --pickup "Airport" --drop "Hotel" --preference sedan
```
**Flags**:
- `--preference`: Options: `cab` (default), `auto`, `sedan`.

---

### 3. Pharmacy Agent (Medicine Basket)
**Script**: `pharmacy_agent.py`
**Goal**: Compare the total cost of a **basket of medicines** across **Tata 1mg**, **Apollo 24|7**, and **PharmEasy**.

**Key Features**:
- **Basket Logic**: Sums up prices for a list of items to find the cheapest *total* order.
- **Quantity Support**: Calculates cost based on required quantities.
- **App Filtering**: Run comparisons on specific apps only.

**Usage**:
```bash
# Compare a basket of medicines
python pharmacy_agent.py --meds "Dolo 650:1, Eco Sprin Gold 40:2"

# Filter specific apps
python pharmacy_agent.py --meds "Dolo 650:1" --apps "Tata 1mg, Apollo 24|7"
```
**Flags**:
- `--meds`: Comma-separated list in `"MedicineName:Quantity"` format.
    - Example: `"Dolo 650:1, Eco Sprin:2"` (1 strip of Dolo, 2 strips of Eco Sprin).
- `--apps`: Comma-separated list of apps to search (e.g., `"Tata 1mg, PharmEasy"`).

---

## 🛠️ Setup & Configuration

### Prerequisites
1.  **Python 3.10+**
2.  **DroidRun Installed**: `pip install droidrun`
3.  **Android Device**: Connected via ADB and accessible.
4.  **API Keys**: Google Gemini API Key.

### Environment Variables
Create a `.env` file in the root directory:
```env
# Required for Reasoning & Vision
GEMINI_API_KEY=your_api_key_here
# or
GOOGLE_API_KEY=your_api_key_here
```

## 📂 Project Structure
- `commerce_agent.py`: Food delivery comparison logic.
- `ride_comparison_agent.py`: Ride-sharing logic with preferences.
- `pharmacy_agent.py`: Medicine basket comparison logic.
- `neurorun/`: Core orchestration utilities (if applicable).

## 🚀 Architecture
This project uses the **DroidRun Professional Architecture**:
- **ConfigManager**: Structured configuration for Agents, Managers, and Executors.
- **LLM Picker**: Dynamic model loading (`load_llm`).
- **Vision & Reasoning**: Enabled via `AgentConfig` for robust UI interaction.
- **Telemetry**: Disabled for local privacy/stability.
