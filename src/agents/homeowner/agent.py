print(f"[{__file__}] Top of src/instabids/agents/homeowner/agent.py", flush=True)

"""
HomeownerAgent definition using Google ADK (post google-generativeai deprecation)
"""
import os
from typing import AsyncGenerator, Dict, Any, List, Optional, Callable
import asyncio # Added for non-blocking Supabase calls
import base64 # Added import

# Removed: import google.generativeai as genai
# Removed: import google.ai.generativelanguage as glm
from google.genai import types as genai_types # Reverting to this for Content and Part
# Removed: from google.adk.types import Content, Part # This path causes ModuleNotFoundError

# Supabase and .env imports
from dotenv import load_dotenv
from supabase import create_client, Client as SupabaseClient

# Updated ADK imports
from google.adk.agents import Agent # Changed from LlmAgent
from google.adk.agents.llm_agent import CallbackContext # Corrected import
# Event might come from genai_types or a new adk.events, adjust if needed later
# from google.adk.events import Event # Old path, likely replaced. AdkApp might use google.adk.types.Content directly.
from google.adk.tools import FunctionTool, ToolContext
# Removed: Content = google_genai_types.Content # Access attribute - will use genai_types.Content directly
# Removed: Part = google_genai_types.Part       # Access attribute - will use genai_types.Part directly

# Import instructions from instruction.py
from .instruction import HOMEOWNER_AGENT_INSTRUCTIONS
# Import new tools
from .tools import upload_image_to_supabase, initialize_tools, TOOL_DESCRIPTIONS, supabase_client

# Constants
DEFAULT_MODEL_NAME = os.getenv("ADK_MODEL_NAME", "gemini-2.0-flash") # Using a recommended Gemini model

# Configure API key - This might be handled by AdkApp or global genai setup
# print(f"[{__file__}] Initializing genai.Client (will use GOOGLE_API_KEY env var)...", flush=True) 
# gemini_client = genai.Client() 

# Load environment variables from .env file
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase_client: Optional[SupabaseClient] = None
if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        print(f"[{__file__}] Supabase client initialized.", flush=True)
    except Exception as e:
        print(f"[{__file__}] Error initializing Supabase client: {e}", flush=True)
else:
    print(f"[{__file__}] SUPABASE_URL or SUPABASE_ANON_KEY not found in environment. Supabase integration will be disabled.", flush=True)


# --- Agent Definition ---

SLOT_FILLING_INSTRUCTION = """
You are a friendly and helpful assistant for homeowners looking to start a new home improvement project. 
Your goal is to gather specific details about their project by asking questions one at a time. 
For each piece of information you successfully gather, you MUST use the 'submit_scope_fact' tool to record it. 

The details you need to collect are:
1.  'project_title': A brief title for the project.
2.  'project_description': A detailed description of what the homeowner wants to do.
3.  'budget_range': The homeowner's estimated budget for the project (e.g., '$500-$1000', 'around $2500').
4.  'timeline': The homeowner's desired timeline for project completion (e.g., 'within 2 weeks', 'next month').

Start by asking for the project title. Once a detail is provided, use the 'submit_scope_fact' tool immediately. Then, ask for the next detail until all are collected.
If the user provides multiple pieces of information at once, use the 'submit_scope_fact' tool for each piece of information.
Do not proceed to the next question until the current piece of information is submitted.
Always confirm what you've recorded using the tool by saying something like "Got it, I've noted down the project title as '...'. Now, could you tell me about..."
"""

# Placeholder for actual tool definition if needed by the agent directly
# For now, tools are typically defined and registered with the ADK server separately.
# This agent will rely on tools being available in its environment.

async def submit_scope_fact(
    tool_context: ToolContext,
    fact_name: str,
    fact_value: str
) -> str:
    """
    Records a single piece of information (a "fact") about the homeowner's project scope.
    Use this tool immediately after the homeowner provides a specific detail.
    For example, if the user says 'I want a new kitchen', call this with fact_name='project_type', fact_value='new kitchen'.
    If they say 'My budget is $10000', call this with fact_name='budget', fact_value='10000'.
    """
    print(f"[Tool: submit_scope_fact] Attempting to record: {fact_name} = {fact_value}", flush=True)
    # Explicitly use the global supabase_client defined in this agent.py file.
    active_supabase_client = supabase_client 

    if not active_supabase_client:
        msg = "CRITICAL_ERROR: Supabase client (global) not initialized in submit_scope_fact. Cannot record fact to database. Check server logs for Supabase client initialization errors at the top of agent.py."
        print(f"[Tool: submit_scope_fact] {msg}", flush=True)
        # Update local facts for debugging, but current_project_scope_id will not be set from DB.
        if tool_context:
            if 'collected_facts' not in tool_context.state:
                tool_context.state['collected_facts'] = {}
            tool_context.state['collected_facts'][fact_name] = fact_value
            print(f"[Tool: submit_scope_fact] Local collected_facts updated. current_project_scope_id remains: {tool_context.state.get('current_project_scope_id')}", flush=True)
        return msg # Return critical error

    current_project_scope_id = tool_context.state.get('current_project_scope_id')
    print(f"[Tool: submit_scope_fact] Initial current_project_scope_id from state: {current_project_scope_id}", flush=True)
    message = ""

    try:
        data_to_save = {fact_name: fact_value}
        if current_project_scope_id:
            print(f"[Tool: submit_scope_fact] Updating existing project scope ID: {current_project_scope_id}", flush=True)
            response = await asyncio.to_thread(
                active_supabase_client.table('project_scopes')
                .update(data_to_save)
                .eq('id', current_project_scope_id)
                .execute
            )
            if response.data:
                message = f"Project scope updated. Fact '{fact_name}' recorded as '{fact_value}' for Project ID: {current_project_scope_id}."
                print(f"[Tool: submit_scope_fact] Update successful: {response.data}", flush=True)
            else:
                error_info = response.error if response.error else "Unknown error during update."
                message = f"DB_ERROR: Error updating project scope {current_project_scope_id}. Details: {error_info}"
                print(f"[Tool: submit_scope_fact] Update failed: {error_info}", flush=True)
        else: # Creating a new project scope
            print(f"[Tool: submit_scope_fact] Creating new project scope with data: {data_to_save}", flush=True)
            response = await asyncio.to_thread(
                active_supabase_client.table('project_scopes')
                .insert(data_to_save)
                .execute
            )
            print(f"[Tool: submit_scope_fact] DB insert response: {response}", flush=True)
            if response.data and len(response.data) > 0 and response.data[0].get('id'):
                new_scope_id = response.data[0]['id']
                tool_context.state['current_project_scope_id'] = new_scope_id
                message = f"New project scope started. Fact '{fact_name}' recorded as '{fact_value}'. Project ID: {new_scope_id}."
                print(f"[Tool: submit_scope_fact] Insert successful, new scope ID set in state: {new_scope_id}", flush=True)
            else: # Failed to create new scope or get ID
                error_info = response.error if response.error else f"Insert operation did not return data or ID. Response data: {response.data}"
                message = f"CRITICAL_ERROR: Failed to create new project scope or retrieve its ID. Details: {error_info}"
                print(f"[Tool: submit_scope_fact] Insert failed or no ID returned: {message}", flush=True)
                # current_project_scope_id remains None or its previous value

    except Exception as e:
        message = f"CRITICAL_ERROR: An unexpected error occurred in submit_scope_fact while saving '{fact_name}': {str(e)}"
        print(f"[Tool: submit_scope_fact] Exception: {message}", flush=True)

    # Update local collected_facts for debugging or if DB is transiently down.
    if tool_context:
        if 'collected_facts' not in tool_context.state:
            tool_context.state['collected_facts'] = {}
        tool_context.state['collected_facts'][fact_name] = fact_value
        print(f"[Tool: submit_scope_fact] Local collected_facts updated: {tool_context.state.get('collected_facts')}", flush=True)
        print(f"[Tool: submit_scope_fact] Final current_project_scope_id in state: {tool_context.state.get('current_project_scope_id')}", flush=True)
    
    return message

# Enhanced tool definition for clarity to the LLM
submit_scope_fact_tool = FunctionTool(func=submit_scope_fact)

# Tool for uploading images
upload_image_tool = FunctionTool(func=upload_image_to_supabase)

# --- Agent Definition ---
from pydantic import Field
class HomeownerAgent(Agent):  # Inherits from google.adk.agents.Agent
    """Agent to assist homeowners in describing their project scope."""

    # Declare supabase_client as a Pydantic field without leading underscore
    supabase_client: Optional[SupabaseClient] = Field(default=None, exclude=True)

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        tools: Optional[List[Callable]] = None, # Updated type hint
        name: str = "HomeownerAgent",
        description: str = "Collects project scope details and image uploads from homeowners.",
        instruction: Optional[str] = None  # Added instruction parameter
    ):
        """Initializes the HomeownerAgent.

        Args:
            model_name: The name of the generative model to use.
            tools: A list of callable functions for the agent. ADK will wrap them.
            name: The name of the agent.
            description: A description of the agent.
            instruction: Optional. The instruction string for the agent. Defaults to HOMEOWNER_AGENT_INSTRUCTIONS.
        """
        print(f"[{__file__} HomeownerAgent.__init__] Initializing with model: {model_name}, name: {name}", flush=True)
        # Call the base Agent constructor with all necessary parameters
        super().__init__(
            model=model_name,       # Base Agent expects 'model'
            instruction=instruction or HOMEOWNER_AGENT_INSTRUCTIONS, # Use provided or default
            tools=tools or initialize_tools(), # Ensure tools are initialized if not provided
            name=name,
            description=description
        )
        
        # Keep other specific initializations for HomeownerAgent
        self.supabase_client = supabase_client # Assign to the Pydantic field
        if self.supabase_client:
            print(f"[{__file__}] Supabase client initialized in HomeownerAgent.", flush=True)
        else:
            print(f"[{__file__}] Supabase client NOT initialized in HomeownerAgent.", flush=True)
        
        print(f"[{__file__} HomeownerAgent.__init__] Tools configured in base: {self.tools}", flush=True)

        # The following attributes are now set by super().__init__ if provided:
        # self.model_name = model_name 
        # self.instruction_text = INSTRUCTION 
        # self.name = name
        # self.description = description

        print(f"[{__file__} HomeownerAgent] Initialized. Name: {self.name}, Model: {self.model}, Description: {self.description}", flush=True)

    # @property
    # def model(self) -> str:
    #     return self.model_name

    async def async_process_event(
        self,
        context: CallbackContext, # Corrected import path used
        *, 
        last_event: Optional[genai_types.Content] = None, # Using genai_types.Content
        tool_context: Optional[ToolContext] = None
    ) -> AsyncGenerator[genai_types.Content, None]: # Using genai_types.Content
        """Processes an incoming event and yields response events."""
        print(f"[{__file__} HomeownerAgent.async_process_event] Received last_event: {last_event}", flush=True)
        print(f"[{__file__} HomeownerAgent.async_process_event] Tool context: {tool_context}", flush=True)

        # This method will be significantly different with AdkApp.
        # AdkApp is expected to handle the primary LLM interaction loop.
        # This agent's role might be to provide specific prompts or handle state.

        # For now, let's assume AdkApp calls this with user input (last_event).
        # The agent needs to formulate a response or decide on actions.

        # Example: If it's user input, prepare it for the LLM (though AdkApp might do this)
        # If AdkApp handles the LLM call, this method might just yield events to send to the user
        # or update internal state.

        # Placeholder logic - actual implementation will depend on AdkApp interaction model.
        if last_event:
            # If there's a last event (e.g., user message), echo it back or process it.
            # This is a simplified placeholder. The actual logic will involve invoking
            # the LLM via AdkApp's mechanisms or responding to tool calls.
            
            # Check for image data in the last event
            image_parts = []
            text_parts = []
            if last_event.parts:
                for part in last_event.parts:
                    if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                        image_parts.append(part)
                        # Potentially trigger image upload tool via AdkApp if not automatic
                        print(f"Image part detected: {part.inline_data.mime_type}", flush=True)
                        # Simulate yielding an event to call upload_image_to_supabase
                        # This is NOT how it will actually work with AdkApp, which handles tool calls.
                        # This is just to illustrate thinking about image parts.
                        # image_data_b64 = base64.b64encode(part.inline_data.data).decode('utf-8')
                        # yield genai_types.Content(parts=[
                        #     genai_types.Part(function_call=genai_types.FunctionCall( # This FunctionCall would be from adk.tools or adk.types if available
                        #         name='upload_image_to_supabase',
                        #         args={'image_base64': image_data_b64, 'project_scope_id': context.state.get('current_project_scope_id')}
                        #     ))
                        # ])
                    elif part.text:
                        text_parts.append(part.text)
            
            user_message = " ".join(text_parts)
            if image_parts:
                user_message += f" (Image{'s' if len(image_parts) > 1 else ''} received)"

            # This is where the agent would typically use the LLM.
            # With AdkApp, the LLM interaction is managed by AdkApp itself based on the agent's
            # instructions and the current conversation history.
            # The agent's `async_process_event` might be more about reacting to LLM outputs
            # or preparing data for the LLM if AdkApp calls it for that purpose.

            # For now, if this method is called by AdkApp, it's likely after an LLM turn
            # or for the agent to produce its own non-LLM event.
            # Let's assume this simplified version just yields a text response for demonstration.
            # The actual logic will be driven by how AdkApp integrates with this method.
            if user_message:
                yield genai_types.Content(parts=[genai_types.Part(text=f"Agent received: {user_message}")])
            else:
                yield genai_types.Content(parts=[genai_types.Part(text="Agent is ready.")])
        else:
            # No last event, perhaps initial call or a system event
            yield genai_types.Content(parts=[genai_types.Part(text="Hello from HomeownerAgent! How can I help you with your project today?")])
        
        # Ensure the generator always yields something or completes.
        # The `async for event in agent.run(...)` in AdkApp expects this.
        await asyncio.sleep(0) # Placeholder for any actual async work if needed

    async def _get_current_project_scope_id_from_db(self, user_id: str) -> Optional[str]:
        """Attempts to retrieve the most recent project_scope_id for a given user_id/homeowner_id."""
        if not self.supabase_client:
            print(f"[{__file__}] Supabase client not available in _get_current_project_scope_id_from_db.", flush=True)
            return None
        try:
            query = self.supabase_client.table('project_scopes').select('id')
            if user_id == "default_user":
                print(f"[{__file__}] Querying for latest project_scope_id where homeowner_id IS NULL", flush=True)
                query = query.is_('homeowner_id', None)
            else:
                print(f"[{__file__}] Querying for latest project_scope_id for homeowner_id: {user_id}", flush=True)
                query = query.eq('homeowner_id', user_id)
            
            response = await asyncio.to_thread(query.execute)
            print(f"[{__file__}] DB query response for latest scope ID: {response}", flush=True)
            if response.data and len(response.data) > 0 and response.data[0].get('id'):
                return response.data[0]['id']
            else:
                print(f"[{__file__}] No project scope ID found for homeowner_id: {user_id if user_id != 'default_user' else 'NULL'}", flush=True)
                return None
        except Exception as e:
            print(f"[{__file__}] Error querying for project scope ID: {str(e)}", flush=True)
            return None

    async def _get_or_create_project_scope_id(self, tool_context: ToolContext, user_id: str) -> str:
        """Gets the current project_scope_id from state or DB, or creates a new one if none exists."""
        current_scope_id = tool_context.state.get('current_project_scope_id')
        if current_scope_id:
            print(f"[{__file__}] Found current_project_scope_id in agent state: {current_scope_id}", flush=True)
            return current_scope_id

        if user_id:
            db_scope_id = await self._get_current_project_scope_id_from_db(user_id)
            if db_scope_id:
                tool_context.state['current_project_scope_id'] = db_scope_id
                print(f"[{__file__}] Fetched project_scope_id from DB: {db_scope_id}. Stored in agent state.", flush=True)
                return db_scope_id
        
        print(f"[{__file__}] Attempting to get/create project_scope_id for user_id (maps to homeowner_id): {user_id}", flush=True)

        if not self.supabase_client:
            print(f"[{__file__}] Supabase client not available in _get_or_create_project_scope_id. Cannot create new scope.", flush=True)
            raise ValueError("Supabase client not initialized, cannot get/create project scope ID.")

        try:
            homeowner_id_to_insert = None
            if user_id != "default_user":
                homeowner_id_to_insert = user_id # Assuming user_id is a valid UUID if not 'default_user'
            
            print(f"[{__file__}] Creating new project scope with homeowner_id: {homeowner_id_to_insert}", flush=True)
            insert_data = {'homeowner_id': homeowner_id_to_insert}
            
            response = await asyncio.to_thread(
                self.supabase_client.table('project_scopes')
                .insert(insert_data)
                .execute
            )
            print(f"[{__file__}] DB insert response for new scope: {response}", flush=True)

            if response.data and len(response.data) > 0 and response.data[0].get('id'):
                new_scope_id = response.data[0]['id']
                tool_context.state['current_project_scope_id'] = new_scope_id
                print(f"[{__file__}] New project scope created. ID: {new_scope_id}. Stored in agent state.", flush=True)
                return new_scope_id
            else:
                print(f"[{__file__}] Failed to create new project scope or retrieve its ID.", flush=True)
                raise ValueError("Failed to create new project scope or retrieve its ID.")
        except Exception as e:
            print(f"[{__file__}] Error creating new project scope: {str(e)}", flush=True)
            raise ValueError(f"Error creating new project scope: {str(e)}")

print(f"[{__file__}] End of src/instabids/agents/homeowner/agent.py", flush=True)

# Instantiate the agent for ADK discovery if this file is the entry point for the agent package
# This is typically done in __init__.py of the agent's package, but shown here for completeness
# if agent.py is directly scanned.
root_agent = HomeownerAgent()

# Make the agent instance available for global tools if necessary
agent_instance_for_tools = root_agent

print(f"[{__file__}] root_agent and agent_instance_for_tools initialized.", flush=True)
