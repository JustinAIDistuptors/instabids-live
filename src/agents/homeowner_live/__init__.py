import os
from dotenv import load_dotenv

# Load .env from project root if it exists
# This ensures that environment variables (like Supabase keys) are available
# when modules like SupabaseSessionService or tools are imported/initialized.
current_dir = os.path.dirname(os.path.abspath(__file__))
# Navigate up three levels: homeowner_live -> agents -> src -> project_root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
dotenv_path = os.path.join(project_root, '.env')

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"[{__file__}] Loaded .env file from: {dotenv_path} for homeowner_live agent init", flush=True)
else:
    print(f"[{__file__}] Root .env file not found at: {dotenv_path}. Relaying on globally set env vars.", flush=True)

import sys
# os is already imported above, but having it again here is fine.
print(f"[{__file__}] Current CWD: {os.getcwd()}", flush=True)
print(f"[{__file__}] sys.path BEFORE project_root adjustment in this __init__: {sys.path}", flush=True)

# project_root should be defined from earlier lines (e.g., line 8 in original view)
# The check 'if project_root not in sys.path:' was from the previous successful edit.
if 'project_root' in locals() and project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"[{__file__}] Added project_root to sys.path: {project_root}", flush=True)
elif 'project_root' in locals(): # Added this elif for robustness
    print(f"[{__file__}] project_root ({project_root}) already in sys.path or not added (if already present).", flush=True)
else:
    print(f"[{__file__}] WARNING: project_root variable was not defined before sys.path adjustment attempt.", flush=True)

print(f"[{__file__}] sys.path AFTER project_root adjustment in this __init__: {sys.path}", flush=True)

# CRUCIAL PART: Import and expose the agent
root_agent = None # Initialize to None
print(f"[{__file__}] Initialized root_agent to None. Attempting 'from .agent import root_agent'...", flush=True)
try:
    from .agent import root_agent
    print(f"[{__file__}] Successfully imported .agent.root_agent. Value: {root_agent}", flush=True)
except ImportError as e:
    print(f"[{__file__}] FAILED to import .agent.root_agent due to ImportError: {e}", flush=True)
    import traceback
    traceback.print_exc() # Print full traceback for import errors
except Exception as e:
    print(f"[{__file__}] UNEXPECTED ERROR importing .agent.root_agent: {e}", flush=True)
    import traceback
    traceback.print_exc() # Print full traceback for other errors

if root_agent:
    print(f"[{__file__}] root_agent is now: {root_agent}. __all__ will be set (currently commented out).", flush=True)
    # __all__ = ["root_agent"] # Temporarily comment out to simplify
else:
    print(f"[{__file__}] root_agent is None or not set after import attempt. __all__ will NOT be set.", flush=True)

