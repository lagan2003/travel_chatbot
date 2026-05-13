"""
Quick smoke test - verifies all imports work and the LangGraph compiles.
Run from the project root:  python test_workflow.py
"""

import sys
import os

# Make sure we import from the project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    print("1. Testing model imports...")
    from models.schemas import IntentExtraction, Flight, Hotel, WeatherForecast, FullItinerary, DailyPlan, Activity
    print("   [OK] models.schemas")

    from models.state import AgentState
    print("   [OK] models.state")

    print("2. Testing service imports...")
    from services.llm import get_llm, generate_structured_data
    print("   [OK] services.llm")
    from services.flights import search_flights
    print("   [OK] services.flights")
    from services.hotels import search_hotels
    print("   [OK] services.hotels")
    from services.weather import get_weather
    print("   [OK] services.weather")
    from services.pdf_export import export_itinerary_to_html
    print("   [OK] services.pdf_export")

    print("3. Testing agent imports...")
    from agents.intent_classifier_agent import intent_classifier_agent
    from agents.orchestrator_agent import orchestrator_agent, orchestrator_route_selector
    from agents.intent_agent import intent_agent
    from agents.flight_agent import flight_agent
    from agents.hotel_agent import hotel_agent
    from agents.weather_agent import weather_agent
    from agents.budget_agent import budget_agent
    from agents.itinerary_agent import itinerary_agent
    from agents.recommendation_agent import recommendation_agent
    from agents.validation_agent import validation_agent
    from agents.critic_agent import critic_agent, critic_route_selector
    from agents.formatter_agent import formatter_agent
    from agents.subgraph_agents import flight_only_node, hotel_only_node, chat_fallback_node
    print("   [OK] All agents")

    print("4. Testing prompt imports...")
    from prompts.system_prompts import INTENT_EXTRACTION_PROMPT, BUDGET_OPTIMIZATION_PROMPT
    print("   [OK] prompts")

    print("5. Compiling LangGraph workflow...")
    from workflows.graph import create_travel_workflow
    workflow = create_travel_workflow()
    print("   [OK] Workflow compiled successfully!")

    print("\n=== ALL IMPORTS AND COMPILATION PASSED ===")
    return True

if __name__ == "__main__":
    try:
        test_imports()
    except Exception as e:
        print(f"\n--- FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
