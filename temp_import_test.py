print(f"[{__file__}] TEMP_TEST: STARTING SCRIPT", flush=True)
print(f"[{__file__}] TEMP_TEST: Attempting to import google.adk.agents.Agent...", flush=True)
try:
    from google.adk.agents import Agent
    print(f"[{__file__}] TEMP_TEST: Successfully imported google.adk.agents.Agent. Value: {Agent}", flush=True)
except Exception as e:
    print(f"[{__file__}] TEMP_TEST: FAILED to import google.adk.agents.Agent. Error: {e}", flush=True)
    import traceback
    traceback.print_exc()
print(f"[{__file__}] TEMP_TEST: FINISHED SCRIPT", flush=True)