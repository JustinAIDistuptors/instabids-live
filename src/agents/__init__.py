# src/agents/__init__.py
from .homeowner_live.agent import HomeownerLiveAgent # Import the agent class

APPS = {
    "homeowner_live": HomeownerLiveAgent # Register the agent
}

__all__ = ["APPS"]

# Optional: A print statement to confirm this file was at least touched.
print(f"[{__file__}] src/agents/__init__.py loaded. APPS configured for homeowner_live.", flush=True)

