import sys
import os
print(f"Current working directory: {os.getcwd()}")
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"sys.path: {sys.path}")

print("\nAttempting to import HomeownerLiveAgent...")
try:
    # Ensure src is in path if script is run from project root
    # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    from src.agents.homeowner_live.agent import HomeownerLiveAgent
    print("Import of HomeownerLiveAgent successful.")

    print("\nAttempting to instantiate HomeownerLiveAgent...")
    try:
        agent_instance = HomeownerLiveAgent()
        print("Instantiation of HomeownerLiveAgent successful.")
        print(f"  Agent instance: {agent_instance}")
        if hasattr(agent_instance, 'model'):
            print(f"  Agent model: {agent_instance.model}")
        if hasattr(agent_instance, 'tools'):
            print(f"  Agent tools: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in agent_instance.tools]}")
        if hasattr(agent_instance, 'session_service'):
            print(f"  Agent session_service: {agent_instance.session_service}")
        print("  Agent seems configured.")

    except Exception as e:
        print(f"ERROR during instantiation: {e}")
        import traceback
        traceback.print_exc()

except ImportError as e:
    print(f"ERROR during import: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"An UNEXPECTED ERROR occurred during import phase: {e}")
    import traceback
    traceback.print_exc()

print("\nDiagnostic script finished.")
