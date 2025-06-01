import os
# Ensure .env is loaded for SupabaseSessionService if it initializes client early
from dotenv import load_dotenv
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(current_dir, '.env') # Assumes script is in project root
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"Loaded .env from {dotenv_path}")
else:
    print(f".env not found at {dotenv_path}")

print("--- Testing ADK Imports and LlmAgent Initialization ---")

try:
    print("Attempting to import State from google.adk.sessions...")
    from google.adk.sessions import State
    print(f"Successfully imported State: {type(State)}")

    print("\nAttempting to import BaseSessionService from google.adk.sessions...")
    from google.adk.sessions import BaseSessionService
    print(f"Successfully imported BaseSessionService: {type(BaseSessionService)}")

    print("\nAttempting to import SupabaseSessionService...")
    # Need to add src to path if not running with poetry run python -m ...
    import sys
    if current_dir not in sys.path: # Add project root to allow src.session...
        sys.path.insert(0, current_dir)
        print(f"Added {current_dir} to sys.path")
    from src.session.supabase_session import SupabaseSessionService
    print(f"Successfully imported SupabaseSessionService: {type(SupabaseSessionService)}")

    print("\nAttempting to import LlmAgent from google.adk.agents...")
    from google.adk.agents import LlmAgent # Agent is an alias for LlmAgent
    print(f"Successfully imported LlmAgent: {type(LlmAgent)}")

    print("\nAttempting to instantiate LlmAgent with SupabaseSessionService...")
    # Dummy instruction for LlmAgent
    instruction_text = "This is a test instruction for LlmAgent."
    agent_instance = LlmAgent(
        name="test_llm_agent",
        model="models/gemini-1.5-flash-latest", # Use a known valid model
        instruction=instruction_text,
        session_service=SupabaseSessionService # Pass the class as per article
    )
    print(f"Successfully instantiated LlmAgent with session_service: {agent_instance}")
    if hasattr(agent_instance, '_session_service_instance') and agent_instance._session_service_instance:
        print(f"LlmAgent has session service instance: {type(agent_instance._session_service_instance)}")
    else:
        print("LlmAgent does NOT have a session service instance after construction with session_service param, or _session_service_instance is not accessible/set.")


except ImportError as e_import:
    print(f"IMPORT ERROR: {e_import}")
    import traceback
    traceback.print_exc()
except Exception as e_other:
    print(f"OTHER EXCEPTION: {e_other}")
    import traceback
    traceback.print_exc()

print("\n--- Test Complete ---")
