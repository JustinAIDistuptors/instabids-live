"""
HomeownerAgent package.
"""
print(f"[{__file__}] Attempting to load homeowner agent module...", flush=True)

import logging

# --- ADDED DEBUG LOGGING ---
# This should be at the very top, before other ADK or Google imports if possible,
# or at least before the agent instantiation that might trigger Google SDK calls.
import os
# Ensure ADK_DEBUG_LOGGING_ENABLED is respected if set in .env
# Load .env from project root if it exists
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
dotenv_path = os.path.join(project_root, '.env')
if os.path.exists(dotenv_path):
    from dotenv import load_dotenv
    load_dotenv(dotenv_path)
    print(f"[{__file__}] Loaded .env file from: {dotenv_path} for homeowner agent init", flush=True)

# Configure logging based on environment variable
logging.basicConfig(level=logging.WARN) # Default to WARN
if os.getenv('ADK_DEBUG_LOGGING_ENABLED', 'false').lower() == 'true':
    # More specific logger targeting if needed, or a general 'google' logger
    logging.getLogger('google').setLevel(logging.DEBUG)
    logging.getLogger('google.api_core').setLevel(logging.DEBUG)
    logging.getLogger('google.auth').setLevel(logging.DEBUG)
    logging.getLogger('google.cloud').setLevel(logging.DEBUG)
    logging.getLogger('google_auth_httplib2').setLevel(logging.DEBUG)
    logging.getLogger('google.generativeai').setLevel(logging.DEBUG) # For Gemini models
    logging.getLogger('google.adk').setLevel(logging.DEBUG) # For ADK specific logs
    # Confirm that debug logging is being set
    print(f"[{__file__}] DEBUG LOGGING ENABLED FOR GOOGLE SDKs in {__name__}", flush=True)
    # Example of a debug log message from ADK itself if it uses standard logging
    logging.debug(f"ADK Debug logging test from {__name__}")
else:
    print(f"[{__file__}] Debug logging for Google SDKs is NOT enabled in {__name__} (ADK_DEBUG_LOGGING_ENABLED is false or not set)", flush=True)

# --- END ADDED DEBUG LOGGING ---

import sys
# Import AdkApp and the agent class
# from vertexai.preview.reasoning_engines import AdkApp # AdkApp is not used directly if root_agent is just an Agent instance
from .agent import HomeownerAgent
from .instruction import HOMEOWNER_AGENT_INSTRUCTIONS # Import instructions

print(f"[{__file__}] Loaded homeowner agent module components (Agent, Instructions).", flush=True)
print(f"[{__file__}] CWD: {os.getcwd()}", flush=True)
print(f"[{__file__}] sys.path: {sys.path}", flush=True)

# 1. Instantiate the agent
print(f"[{__file__}] Instantiating HomeownerAgent...", flush=True)
DEFAULT_MODEL_NAME = os.getenv("ADK_MODEL_NAME", "gemini-1.5-flash-preview-0514") # Ensure model name is sourced

homeowner_agent_instance = HomeownerAgent(
    model_name=DEFAULT_MODEL_NAME, 
    instruction=HOMEOWNER_AGENT_INSTRUCTIONS, # Pass the imported instructions
    # Tools will be initialized by default within HomeownerAgent.__init__ if not provided
    name="HomeownerProjectScopeAgent", 
    description="Agent to collect project scope details and manage image uploads for homeowners."
)
print(f"[{__file__}] HomeownerAgent instantiated: {homeowner_agent_instance.name}", flush=True)

# The ADK server will discover this 'root_agent'.
root_agent = homeowner_agent_instance

# Print a confirmation that the module was loaded and root_agent is set.
print(f"[{__file__}] 'root_agent' (HomeownerAgent instance) assigned and module loaded.", flush=True)

__all__ = ["root_agent"]
