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

from .agent import root_agent

__all__ = ["root_agent"]
