print(f"[{__file__}] Top of src/instabids/agents/homeowner/agent.py", flush=True)

"""
HomeownerAgent definition using Google ADK 1.0.0
"""
import os
from typing import AsyncGenerator, Dict, Any, List, Optional
import asyncio # Added for non-blocking Supabase calls
import base64 # Added import

import google.generativeai as genai
import google.ai.generativelanguage as glm

# Supabase and .env imports
from dotenv import load_dotenv
from supabase import create_client, Client as SupabaseClient

# Updated ADK imports
from google.adk.agents import LlmAgent
from google.adk.agents.llm_agent import CallbackContext, InvocationContext
from google.adk.events import Event
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types as google_genai_types # New import
Content = google_genai_types.Content # Access attribute
Part = google_genai_types.Part       # Access attribute

# Import instructions from instruction.py
from .instruction import HOMEOWNER_AGENT_INSTRUCTIONS
# Import new tools
from .tools import upload_image_to_supabase

# Configure API key
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

    if not supabase_client:
        msg = "Supabase client not initialized. Cannot record fact to database."
        print(f"[Tool: submit_scope_fact] {msg}", flush=True)
        # Fallback to old behavior if Supabase is not available
        if tool_context:
            if 'collected_facts' not in tool_context.state:
                tool_context.state['collected_facts'] = {}
            tool_context.state['collected_facts'][fact_name] = fact_value
            return f"Fact '{fact_name}' recorded locally as '{fact_value}'. DB not available."
        return f"Fact '{fact_name}' recorded (local fallback, no context). DB not available."

    current_project_scope_id = tool_context.state.get('current_project_scope_id')
    db_operation_successful = False
    message = ""

    try:
        data_to_save = {fact_name: fact_value}
        if current_project_scope_id:
            print(f"[Tool: submit_scope_fact] Updating existing project scope ID: {current_project_scope_id}", flush=True)
            response = await asyncio.to_thread(
                supabase_client.table('project_scopes')
                .update(data_to_save)
                .eq('id', current_project_scope_id)
                .execute
            )
            if response.data:
                db_operation_successful = True
                message = f"Project scope updated. Fact '{fact_name}' recorded as '{fact_value}' for Project ID: {current_project_scope_id}."
                print(f"[Tool: submit_scope_fact] Update successful: {response.data}", flush=True)
            else:
                error_info = response.error if response.error else "Unknown error during update."
                message = f"Error updating project scope {current_project_scope_id}. Details: {error_info}"
                print(f"[Tool: submit_scope_fact] Update failed: {error_info}", flush=True)
        else:
            print(f"[Tool: submit_scope_fact] Creating new project scope.", flush=True)
            # Add a placeholder for homeowner_id if you have a user system, otherwise omit or set to null if column allows
            # data_to_save['homeowner_id'] = tool_context.state.get('homeowner_user_id') # Example
            response = await asyncio.to_thread(
                supabase_client.table('project_scopes')
                .insert(data_to_save)
                .execute
            )
            if response.data and len(response.data) > 0:
                new_scope_id = response.data[0]['id']
                tool_context.state['current_project_scope_id'] = new_scope_id
                db_operation_successful = True
                message = f"New project scope started. Fact '{fact_name}' recorded as '{fact_value}'. Project ID: {new_scope_id}."
                print(f"[Tool: submit_scope_fact] Insert successful: {response.data}", flush=True)
            else:
                error_info = response.error if response.error else "Unknown error during insert."
                message = f"Error creating new project scope. Details: {error_info}"
                print(f"[Tool: submit_scope_fact] Insert failed: {error_info}", flush=True)

    except Exception as e:
        message = f"An unexpected error occurred while saving fact '{fact_name}': {e}"
        print(f"[Tool: submit_scope_fact] Exception: {message}", flush=True)

    # Fallback state update for local tracking, regardless of DB success for now
    if tool_context:
        if 'collected_facts' not in tool_context.state:
            tool_context.state['collected_facts'] = {}
        tool_context.state['collected_facts'][fact_name] = fact_value
        print(f"[Tool: submit_scope_fact] Local state in tool_context: {tool_context.state['collected_facts']}", flush=True)
    
    return message

# Enhanced tool definition for clarity to the LLM
submit_scope_fact_tool = FunctionTool(func=submit_scope_fact)

# Tool for uploading images
upload_image_tool = FunctionTool(func=upload_image_to_supabase)

# --- Agent Definition ---
from pydantic import Field
class HomeownerAgent(LlmAgent):
    """Agent for homeowners to describe their project and upload images."""
    uploaded_image_urls: List[str] = Field(default_factory=list)
    current_session_id: Optional[str] = Field(default=None)
    supabase_client: Optional[SupabaseClient] = Field(default=None) # Initialized by _initialize_supabase_client in __init__

    def __init__(self, **kwargs: Any): 
        instruction_to_use = (
            kwargs.pop('instruction', None) or
            HOMEOWNER_AGENT_INSTRUCTIONS or
            SLOT_FILLING_INSTRUCTION 
        )
        default_tools_list = [submit_scope_fact_tool, upload_image_tool] 
        user_provided_tools = kwargs.pop('tools', None)
        tools_to_use = user_provided_tools if user_provided_tools is not None else default_tools_list

        model_to_use = kwargs.pop('model', "gemini-1.5-flash-latest")

        super().__init__(
            name="HomeownerAgent",
            instruction=instruction_to_use,
            model=model_to_use,
            tools=tools_to_use,
            **kwargs  # Pass any other LlmAgent-specific or miscellaneous kwargs
        )

        self.supabase_client = self._initialize_supabase_client()

        print(f"[{__file__}] HomeownerAgent initialized with instruction: {self.instruction[:100]}...", flush=True)
        print(f"[{__file__}] HomeownerAgent initialized with tools: {self.tools}", flush=True)

    def _initialize_supabase_client(self) -> Optional[SupabaseClient]:
        """Initializes and returns a Supabase client if credentials are set."""
        load_dotenv() # Ensure .env variables are loaded
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_ANON_KEY")

        if supabase_url and supabase_key:
            print(f"[{__file__}] Supabase URL and Key found. Initializing client.", flush=True)
            try:
                client = create_client(supabase_url, supabase_key)
                print(f"[{__file__}] Supabase client initialized successfully.", flush=True)
                return client
            except Exception as e:
                print(f"[{__file__}] Error initializing Supabase client: {e}", flush=True)
                return None
        else:
            print(f"[{__file__}] SUPABASE_URL or SUPABASE_ANON_KEY not found in environment variables.", flush=True)
            print(f"[{__file__}] Supabase client will not be initialized. Image upload tool may not function.", flush=True)
            return None

    async def async_process_event(
        self,
        context: CallbackContext, 
        *,
        last_event: Event = None, 
        tool_context: ToolContext = None, 
    ) -> AsyncGenerator[Event, None]:
        """Processes events, handling image uploads and then passing to LlmAgent.chat."""
        print(f"[{__file__}] HomeownerAgent.async_process_event called. Last event type: {last_event.type if last_event else 'None'}", flush=True)

        current_tool_context = tool_context or self.tool_context

        if last_event and last_event.type == "USER_MESSAGE" and last_event.content:
            image_url_to_report = None
            for part in last_event.content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    print(f"[{__file__}] Image detected in USER_MESSAGE: {part.inline_data.mime_type}", flush=True)
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type
                    file_extension = mime_type.split('/')[-1]

                    # Encode bytes to base64 string
                    image_base64_string = base64.b64encode(image_bytes).decode('utf-8')

                    if 'upload_image_to_supabase' in self.tools_map:
                        try:
                            print(f"[{__file__}] Calling upload_image_to_supabase function...", flush=True)
                            image_url_from_upload = await self.tools_map['upload_image_to_supabase'].func(
                                tool_context=current_tool_context, 
                                image_base64=image_base64_string,  
                                file_extension=file_extension
                            )
                            print(f"[{__file__}] Image upload result (URL or error): {image_url_from_upload}", flush=True)
                            if image_url_from_upload and not image_url_from_upload.startswith("Error:"):
                                image_url_to_report = image_url_from_upload
                            if image_url_from_upload and image_url_from_upload.startswith("Error:"):
                                yield Event(type="ASSISTANT_MESSAGE", content=Content(parts=[Part(text=f"I encountered an issue uploading your image: {image_url_from_upload}")]))
                                return 

                        except Exception as e:
                            print(f"[{__file__}] Error calling upload_image_to_supabase: {e}", flush=True)
                            yield Event(type="ASSISTANT_MESSAGE", content=Content(parts=[Part(text=f"I encountered an unexpected error trying to upload your image: {e}. Please try again or continue without it for now.")]))
                            return 
                    else:
                        print(f"[{__file__}] 'upload_image_to_supabase' tool not found in tools_map.", flush=True)
                    break 
            
            if image_url_to_report and not image_url_to_report.startswith("Error:"):
                yield Event(type="ASSISTANT_MESSAGE", content=Content(parts=[Part(text=f"I've uploaded the image. You can find it at: {image_url_to_report}. I will now save this information.")]))
                self.uploaded_image_urls.append(image_url_to_report)

        async for response_event in super().chat(last_event=last_event, tool_context=current_tool_context):
            print(f"[{__file__}] Yielding event from super().chat(): {response_event.type}, content: {response_event.content.parts[0].text if response_event.content and response_event.content.parts else 'N/A'}", flush=True)
            yield response_event
        print(f"[{__file__}] Finished super().chat() for event type: {last_event.type if last_event else 'None'}", flush=True)

    def get_current_project_scope_id(self) -> str | None:
        """Helper to get current_project_scope_id from tool_context."""
        return self.tool_context.state.get('current_project_scope_id')

print(f"[{__file__}] End of src/instabids/agents/homeowner/agent.py", flush=True)

# Instantiate the agent for discovery
root_agent = HomeownerAgent() 

print(f"[{__file__}] HomeownerAgent instance 'root_agent' created.", flush=True)
print(f"[{__file__}] root_agent.instruction: {root_agent.instruction[:100]}...", flush=True) 
print(f"[{__file__}] root_agent.tools: {root_agent.tools}", flush=True)
