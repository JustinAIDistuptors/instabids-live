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
        event_for_llm = last_event  # Default to original event
        system_notes_for_llm = [] # Accumulate notes for the LLM

        if last_event and last_event.type == "USER_MESSAGE" and last_event.content:
            image_part_data = None
            for part_idx, part in enumerate(last_event.content.parts):
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    image_part_data = part
                    break
            
            if image_part_data:
                print(f"[{__file__}] Image detected in USER_MESSAGE: {image_part_data.inline_data.mime_type}", flush=True)
                image_bytes = image_part_data.inline_data.data
                mime_type = image_part_data.inline_data.mime_type
                file_extension = mime_type.split('/')[-1]
                image_base64_string = base64.b64encode(image_bytes).decode('utf-8')

                image_url_from_upload = None
                try:
                    if 'upload_image_to_supabase' in self.tools_map:
                        print(f"[{__file__}] Calling upload_image_to_supabase function...", flush=True)
                        # Ensure the tool uses the global supabase_client by its definition in tools.py or agent.py
                        image_url_from_upload = await self.tools_map['upload_image_to_supabase'].func(
                            tool_context=current_tool_context, 
                            image_base64=image_base64_string,  
                            file_extension=file_extension
                        )
                        print(f"[{__file__}] Image upload result (URL or error): {image_url_from_upload}", flush=True)

                        if image_url_from_upload:
                            if image_url_from_upload.startswith("Error:"):
                                system_notes_for_llm.append(f"System note: Image upload failed. Detail: {image_url_from_upload}")
                                print(f"[{__file__}] Image upload tool returned an error: {image_url_from_upload}", flush=True)
                            else:
                                system_notes_for_llm.append(f"System note: An image was successfully uploaded with URL: {image_url_from_upload}.")
                                project_scope_id = current_tool_context.state.get('current_project_scope_id')
                                # Use the global supabase_client for consistency with other tools
                                active_supabase_client = supabase_client 
                                if project_scope_id and active_supabase_client:
                                    print(f"[{__file__}] Saving image URL to project_images. Scope ID: {project_scope_id}, URL: {image_url_from_upload}", flush=True)
                                    image_data_to_save = {
                                        'project_scope_id': project_scope_id,
                                        'image_url': image_url_from_upload
                                    }
                                    insert_response = await asyncio.to_thread(
                                        active_supabase_client.table('project_images').insert(image_data_to_save).execute
                                    )
                                    if not insert_response.data or (hasattr(insert_response, 'error') and insert_response.error):
                                        error_info = insert_response.error if hasattr(insert_response, 'error') and insert_response.error else "Unknown error during project_images insert."
                                        system_notes_for_llm.append(f"System note: Image was uploaded, but failed to catalog it in project_images table. Detail: {error_info}")
                                        print(f"[{__file__}] Error saving image URL to project_images: {error_info}", flush=True)
                                    else:
                                        system_notes_for_llm.append(f"System note: Image URL successfully cataloged in project_images table.")
                                        print(f"[{__file__}] Image URL successfully saved to project_images table for scope {project_scope_id}.", flush=True)
                                elif not project_scope_id:
                                    system_notes_for_llm.append(f"System note: Image was uploaded, but cannot catalog to project_images: current_project_scope_id is not set.")
                                    print(f"[{__file__}] Cannot save image to project_images: current_project_scope_id is not set.", flush=True)
                                elif not active_supabase_client:
                                    system_notes_for_llm.append(f"System note: Image was uploaded, but cannot catalog to project_images: Supabase client not initialized.")
                                    print(f"[{__file__}] Cannot save image to project_images: Supabase client (global) not initialized.", flush=True)
                        else: # image_url_from_upload is None
                            system_notes_for_llm.append(f"System note: Image upload attempt did not return a URL or an error message.")
                            print(f"[{__file__}] Image upload tool returned None.", flush=True)

                    else: # Tool not in map
                        system_notes_for_llm.append(f"System note: Image detected, but 'upload_image_to_supabase' tool is not available.")
                        print(f"[{__file__}] 'upload_image_to_supabase' tool not found in tools_map.", flush=True)

                except Exception as e:
                    system_notes_for_llm.append(f"System note: An unexpected error occurred during image processing: {str(e)}")
                    print(f"[{__file__}] Exception during image processing: {e}", flush=True)

                # Create a modified event for the LLM, excluding the image data, but including system notes
                text_parts = [p for p_idx, p in enumerate(last_event.content.parts) if not (p.inline_data and p.inline_data.mime_type.startswith("image/"))]
                if system_notes_for_llm:
                    full_system_note = " ".join(system_notes_for_llm)
                    text_parts.append(Part(text=f"({full_system_note})"))
                
                modified_content = Content(parts=text_parts, role=last_event.content.role)
                event_for_llm = Event(type=last_event.type, content=modified_content)
                print(f"[{__file__}] Image processed. Modified event created for LLM.", flush=True)
            else:
                print(f"[{__file__}] No image detected in USER_MESSAGE parts.", flush=True)

        # Fallback to default LlmAgent.chat behavior if no specific handling was done or to continue processing
        print(f"[{__file__}] Yielding to super().chat with event_for_llm (type: {event_for_llm.type if event_for_llm else 'None'}). Current tool_context state: {current_tool_context.state if current_tool_context else 'None'}", flush=True)
        async for response_event in super().chat(
            context=context, 
            last_event=event_for_llm, 
            tool_context=current_tool_context
        ):
            print(f"[{__file__}] Event from super().chat: {response_event.type if response_event else 'None'}", flush=True)
            yield response_event

    def get_current_project_scope_id(self) -> Optional[str]:
        """Helper to get current_project_scope_id from tool_context."""
        return self.tool_context.state.get('current_project_scope_id')

print(f"[{__file__}] End of src/instabids/agents/homeowner/agent.py", flush=True)

# Instantiate the agent for discovery
root_agent = HomeownerAgent() 

print(f"[{__file__}] HomeownerAgent instance 'root_agent' created.", flush=True)
print(f"[{__file__}] root_agent.instruction: {root_agent.instruction[:100]}...", flush=True) 
print(f"[{__file__}] root_agent.tools: {root_agent.tools}", flush=True)
