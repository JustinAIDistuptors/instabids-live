# src/agents/__init__.py
# This file is crucial for the ADK framework to discover your agents.

# Import the root_agent instance from the agent package(s) you want to expose.
# Ensure that the __init__.py within each agent package (e.g., homeowner_live/__init__.py)
# correctly exports its own root_agent.

from src.agents.homeowner_live import root_agent as homeowner_live_root_agent

# APPS is a dictionary where keys are the URL-friendly names of your agent apps
# and values are the root_agent instances.
APPS = {
    "homeowner_live": homeowner_live_root_agent,
    # Add other agents here if you have them, e.g.:
    # "contractor_agent": contractor_root_agent,
}

# The ADK framework will look for this APPS dictionary to load the agents.
__all__ = ["APPS"]

print(f"[{__file__}] src/agents/__init__.py loaded. Exposing APPS: {list(APPS.keys())}", flush=True)
