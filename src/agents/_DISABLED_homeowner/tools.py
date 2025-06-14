# tools.py for HomeownerAgent
import os
import uuid
from supabase import create_client, Client as SupabaseClient
from google.adk.tools import ToolContext
import base64
import re # Import re for regex operations
from typing import Optional, List, Callable

# Initialize Supabase client (similar to agent.py, consider refactoring to a shared client later)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY") # For storage, service_role key might be needed for more privileged operations
supabase_client: SupabaseClient | None = None
if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        print(f"[{__file__}] Supabase client initialized for tools.", flush=True)
    except Exception as e:
        print(f"[{__file__}] Error initializing Supabase client for tools: {e}", flush=True)
else:
    print(f"[{__file__}] SUPABASE_URL or SUPABASE_ANON_KEY not found. Supabase tools may fail.", flush=True)

IMAGE_BUCKET_NAME = "project_images"

MIME_TO_EXTENSION = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
    # Add other common image types as needed
}

# Helper function to strip data URL prefix if present
def _strip_base64_prefix(base64_string: str) -> str:
    match = re.match(r"data:image\/\w+;base64,(.*)", base64_string)
    if match:
        return match.group(1)
    return base64_string

# Helper function to ensure correct base64 padding
def _ensure_base64_padding(base64_string: str) -> str:
    missing_padding = len(base64_string) % 4
    if missing_padding:
        base64_string += '=' * (4 - missing_padding)
    return base64_string

async def upload_image_to_supabase(
    tool_context: ToolContext,
    image_base64: str, 
    mime_type: str
) -> str:
    """
    Uploads an image to Supabase Storage in the 'project_images' bucket and returns its public URL.
    The image will be named using the current_project_scope_id if available, or a new UUID.
    The file extension is derived from the mime_type.
    Arguments:
        image_base64: The base64 encoded string of the image to upload.
        mime_type: The MIME type of the image (e.g., 'image/jpeg', 'image/png').
    """
    print(f"[Tool: upload_image_to_supabase] Attempting to upload image with mime_type: {mime_type}...", flush=True)
    if not supabase_client:
        msg = "Supabase client not initialized. Cannot upload image."
        print(f"[Tool: upload_image_to_supabase] {msg}", flush=True)
        return f"Error: {msg}"

    file_extension = MIME_TO_EXTENSION.get(mime_type.lower())
    if not file_extension:
        error_message = f"Unsupported or unknown mime_type: {mime_type}. Cannot determine file extension."
        print(f"[Tool: upload_image_to_supabase] {error_message}", flush=True)
        return f"Error: {error_message}"

    project_scope_id = tool_context.state.get('current_project_scope_id')
    if project_scope_id:
        file_name = f"{project_scope_id}.{file_extension}"
    else:
        # If no project scope ID yet, generate a unique name (e.g., if image is uploaded before title)
        file_name = f"{uuid.uuid4()}.{file_extension}"
    
    file_path_in_bucket = f"{file_name}" # Can add subdirectories like public/{file_name} if desired

    try:
        # Pre-process the base64 string
        processed_base64 = _strip_base64_prefix(image_base64)
        processed_base64 = _ensure_base64_padding(processed_base64)

        # Decode base64 string to bytes
        try:
            image_bytes = base64.b64decode(processed_base64)
        except Exception as e:
            error_message = f"Error decoding base64 image string after processing: {e}. Original string snippet: {image_base64[:100]}..."
            print(f"[Tool: upload_image_to_supabase] {error_message}", flush=True)
            return f"Error: {error_message}"

        # Simplistic approach: write bytes to a temporary file then upload
        # This is a common workaround if the library expects a file path.
        temp_file_path = f"temp_image_for_upload_{uuid.uuid4()}.{file_extension}"
        with open(temp_file_path, 'wb') as f:
            f.write(image_bytes)

        print(f"[Tool: upload_image_to_supabase] Uploading {temp_file_path} to bucket {IMAGE_BUCKET_NAME} as {file_path_in_bucket}", flush=True)
        response = supabase_client.storage.from_(IMAGE_BUCKET_NAME).upload(
            path=file_path_in_bucket,
            file=temp_file_path, # Path to the temporary file
            file_options={"cache-control": "3600", "upsert": "true"} # Upsert to overwrite if same name
        )
        os.remove(temp_file_path) # Clean up temporary file

        if response.status_code == 200:
            # Get public URL
            public_url_response = supabase_client.storage.from_(IMAGE_BUCKET_NAME).get_public_url(file_path_in_bucket)
            image_db_url = public_url_response
            print(f"[Tool: upload_image_to_supabase] Upload successful. Public URL: {image_db_url}", flush=True)
            
            # Save this URL to the project_scopes table using submit_scope_fact
            # This assumes submit_scope_fact is available in this context or we call it from the agent
            # For now, let's return the URL and let the agent handle saving it via submit_scope_fact.
            return image_db_url
        else:
            error_message = f"Error uploading image: {response.json() if hasattr(response, 'json') else response.text}"
            print(f"[Tool: upload_image_to_supabase] {error_message}", flush=True)
            return f"Error: {error_message}"

    except Exception as e:
        error_message = f"An unexpected error occurred during image upload: {e}"
        print(f"[Tool: upload_image_to_supabase] {error_message}", flush=True)
        return f"Error: {error_message}"

# Tool: submit_scope_fact
async def submit_scope_fact(
    tool_context: ToolContext,
    fact_name: str,
    fact_value: str,
    project_scope_id: Optional[str] = None
) -> str:
    """
    Saves a specific piece of information (a fact) about the homeowner's project to the database.
    If 'current_homeowner_id' is not in tool_context.state, it will be generated and stored.
    If project_scope_id is not provided, it will use 'current_project_scope_id' from the agent's state.
    If 'current_project_scope_id' is not in state and project_scope_id is not provided, a new project_scope will be initiated.

    Args:
        fact_name: The name of the fact to save (e.g., 'project_title', 'project_description', 'image_url', 'contractor_notes').
        fact_value: The value of the fact.
        project_scope_id: Optional. The ID of the project scope to update. If None, uses current_project_scope_id from state or creates a new one.
    """
    print(f"[Tool: submit_scope_fact] Called with fact_name: {fact_name}, fact_value: {fact_value}, project_scope_id: {project_scope_id}", flush=True)
    if not supabase_client:
        msg = "Supabase client not initialized. Cannot submit fact."
        print(f"[Tool: submit_scope_fact] {msg}", flush=True)
        return f"Error: {msg}"

    generated_new_homeowner_id_message_suffix = ""
    current_homeowner_id = tool_context.state.get('current_homeowner_id')
    if not current_homeowner_id:
        current_homeowner_id = str(uuid.uuid4()) # Generate new homeowner_id
        tool_context.state['current_homeowner_id'] = current_homeowner_id
        print(f"[Tool: submit_scope_fact] No Homeowner ID in state. Generated new Homeowner ID: {current_homeowner_id}", flush=True)
        generated_new_homeowner_id_message_suffix = f" A new Homeowner ID was generated for you: {current_homeowner_id}. Please save this for future reference."
    else:
        print(f"[Tool: submit_scope_fact] Using existing Homeowner ID from state: {current_homeowner_id}", flush=True)

    current_project_scope_id = project_scope_id or tool_context.state.get('current_project_scope_id')
    generated_new_project_id_message_suffix = ""

    # Prepare the value to be saved, converting to boolean if necessary
    value_to_save = fact_value
    if fact_name == "group_bidding_preference":
        if isinstance(fact_value, str):
            value_to_save = fact_value.lower() in ['true', 'yes']
        elif isinstance(fact_value, bool):
            value_to_save = fact_value # Already a boolean
        else:
            # Handle unexpected types for group_bidding_preference, default to False or log error
            print(f"[Tool: submit_scope_fact] Warning: Unexpected type for group_bidding_preference '{fact_value}'. Defaulting to False.", flush=True)
            value_to_save = False

    try:
        if not current_project_scope_id:
            new_project_scope_uuid = str(uuid.uuid4()) # Generate UUID for the project's own ID column
            print(f"[Tool: submit_scope_fact] No current_project_scope_id. Creating new project scope (ID: {new_project_scope_uuid}) for homeowner_id {current_homeowner_id} with {fact_name}: {value_to_save}", flush=True)
            new_scope_data = {
                'id': new_project_scope_uuid, # Explicitly set the project's own ID
                fact_name: value_to_save, # Use the potentially converted value
                'homeowner_id': current_homeowner_id
            }
            
            response = supabase_client.table("project_scopes").insert(new_scope_data).execute()
            # After insert, the ID we set is the one to use.
            current_project_scope_id = new_project_scope_uuid
            tool_context.state['current_project_scope_id'] = current_project_scope_id # Update state
            print(f"[Tool: submit_scope_fact] New project_scope created with ID: {current_project_scope_id} for homeowner_id: {current_homeowner_id}", flush=True)
            generated_new_project_id_message_suffix = f" Project ID is {current_project_scope_id}."
            return f"Successfully created new project and saved {fact_name}.{generated_new_project_id_message_suffix}{generated_new_homeowner_id_message_suffix}"
        else:
            print(f"[Tool: submit_scope_fact] Updating project_scope ID: {current_project_scope_id} (homeowner_id: {current_homeowner_id}) with {fact_name}: {value_to_save}", flush=True)
            update_data = {fact_name: value_to_save} # Use the potentially converted value
            response = supabase_client.table("project_scopes").update(update_data).eq("id", current_project_scope_id).execute()
            print(f"[Tool: submit_scope_fact] Update operation completed for project_scope ID: {current_project_scope_id}. Response status: {getattr(response, 'status_code', 'N/A')}, data: {getattr(response, 'data', 'N/A')}", flush=True)
            return f"Successfully updated {fact_name} for project ID {current_project_scope_id}.{generated_new_homeowner_id_message_suffix}"

    except Exception as e:
        error_message = f"An unexpected error occurred in submit_scope_fact: {e}"
        print(f"[Tool: submit_scope_fact] {error_message}", flush=True)
        return f"Error: {error_message}"

TOOL_DESCRIPTIONS = {
    "submit_scope_fact": "Saves a specific piece of information (a fact) about the homeowner's project to the database. Use this for project_title, project_description, image_url, location, budget, timeline, contractor_notes, etc. If no project ID exists, it will create one.",
    "upload_image_to_supabase": "Uploads an image to Supabase Storage and returns its public URL. Requires base64 encoded image data and its MIME type."
}

def initialize_tools() -> List[Callable]: 
    """Initializes and returns a list of callable tool functions for the HomeownerAgent.
    ADK will automatically wrap these callables into FunctionTool objects.
    """
    print(f"[{__file__}] Returning callable tools: submit_scope_fact, upload_image_to_supabase", flush=True)
    return [submit_scope_fact, upload_image_to_supabase]

__all__ = ["initialize_tools", "TOOL_DESCRIPTIONS", "submit_scope_fact", "upload_image_to_supabase"]
