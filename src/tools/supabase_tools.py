# src/tools/supabase_tools.py
print(f"[{__file__}] Attempting to load src.tools.supabase_tools", flush=True)
from google.adk.tools import FunctionTool, ToolContext
from supabase import create_client, Client as SupabaseClient
from pydantic import BaseModel, Field
import os
import uuid # For generating IDs if needed
import json # For handling potential JSON in fact_value
from typing import Optional, Dict # Added Optional, ensured Dict is present if used elsewhere
import logging
import base64
import mimetypes

logger = logging.getLogger(__name__)

class UpsertProjectScopeSchema(BaseModel):
    project_summary: str | None = Field(default=None, description="A concise summary of all key project details provided by the user.")
    budget_range: str | None = Field(default=None, description="Estimated budget for the project (e.g., '$5000-$10000').")
    zip_code: str | None = Field(default=None, description="Project location zip code.")
    project_title: str | None = Field(default=None, description="A short, descriptive title for the project.")
    status: str | None = Field(default=None, description="Current status of the project (e.g., new, planning, active, completed). Defaults to 'new' if not provided for a new project.")
    image_url: str | None = Field(default=None, description="URL of the primary image associated with the project, if any.")

# Initialize Supabase client - ensure .env variables are loaded
# Best practice: ensure .env is loaded early in your application entry point.
# For ADK, .env is typically loaded automatically if python-dotenv is installed.
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print(f"[{__name__}] WARNING: Supabase URL or Service Role Key not found in environment variables for supabase_tools.py.")
    # This will cause errors if the tool is called without a client.
    # Consider raising an ImportError or a custom configuration error.
    supabase_client = None
else:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def upsert_project_scope_implementation(tool_context: ToolContext, details: dict) -> str:
    """
    Upserts project scope data to Supabase using a single 'details' dictionary.
    Manages homeowner_id and project_scope_id from agent state.
    Extracts primary fields (project_summary, budget_range, etc.) from 'details'.
    Remaining items in 'details' are stored in project_scope_facts.
    """
    if not supabase_client:
        print(f"[{__name__}] ERROR: Supabase client not initialized in upsert_project_scope_tool.")
        return "Error: Supabase client not initialized. Cannot save project scope."

    print(f"[{__name__}] upsert_project_scope_tool called with: details={details}")
    print(f"[{__name__}] Current agent state from tool_context: {tool_context.state}")

    # Extract known fields from the details dictionary for project_scopes table
    # Map 'project_summary' from LLM to 'conversation_summary' in DB
    conversation_summary = details.pop("project_summary", None)
    project_description = details.pop("project_description", None)
    budget_range = details.pop("budget_range", None)
    timeline = details.pop("timeline", None)
    zip_code = details.pop("zip_code", None)
    project_title = details.pop("project_title", None)
    status = details.pop("status", None) # Default status is handled later if new scope
    image_url = details.pop("image_url", None)
    # Add other potential fields from project_scopes if they might be in 'details'
    # For example: contractor_notes, group_bidding_preference
    contractor_notes = details.pop("contractor_notes", None)
    group_bidding_preference = details.pop("group_bidding_preference", None)

    # Known fields have been popped from 'details'. Any remaining items are ignored.

    homeowner_id = tool_context.state.get("current_homeowner_id")
    if not homeowner_id:
        homeowner_id = str(uuid.uuid4())
        tool_context.state["current_homeowner_id"] = homeowner_id
        print(f"[{__name__}] Generated new homeowner_id: {homeowner_id} and updated agent state.")

    project_scope_id = tool_context.state.get("current_project_scope_id")
    
    scope_direct_data = {}
    if conversation_summary is not None: # Use the mapped variable
        scope_direct_data["conversation_summary"] = conversation_summary
    if project_description is not None:
        scope_direct_data["project_description"] = project_description
    if budget_range is not None:
        scope_direct_data["budget_range"] = budget_range
    if timeline is not None:
        scope_direct_data["timeline"] = timeline
    if zip_code is not None:
        scope_direct_data["zip_code"] = zip_code
    if project_title is not None:
        scope_direct_data["project_title"] = project_title
    if status is not None:
        scope_direct_data["status"] = status
    if image_url is not None:
        scope_direct_data["image_url"] = image_url
    if contractor_notes is not None:
        scope_direct_data["contractor_notes"] = contractor_notes
    if group_bidding_preference is not None:
        # Ensure boolean conversion if necessary, though LLM might pass bool directly
        if isinstance(group_bidding_preference, str):
            scope_direct_data["group_bidding_preference"] = group_bidding_preference.lower() == 'true'
        else:
            scope_direct_data["group_bidding_preference"] = group_bidding_preference

    if not project_scope_id:
        project_scope_id = str(uuid.uuid4())
        tool_context.state["current_project_scope_id"] = project_scope_id
        print(f"[{__name__}] Generated new project_scope_id: {project_scope_id} and updated agent state.")
        
        scope_insert_data = {
            "id": project_scope_id,
            "homeowner_id": homeowner_id,
            **scope_direct_data
        }
        if "status" not in scope_insert_data or scope_insert_data["status"] is None: # Check if status was provided or is None
             scope_insert_data["status"] = "new" # Default status for new scopes

        try:
            print(f"[{__name__}] Attempting to insert new project_scope: {scope_insert_data}")
            response = supabase_client.table("project_scopes").insert(scope_insert_data).execute()
            if response.data:
                print(f"[{__name__}] Successfully created new project_scope: {project_scope_id}")
            elif response.error:
                print(f"[{__name__}] Supabase error creating project_scope: {response.error.message}")
                return f"Error creating project scope: {response.error.message}"
            else:
                print(f"[{__name__}] Failed to create project_scope (no data/error): {response}")
                return "Failed to create project scope (no data/error from Supabase)."
        except Exception as e:
            print(f"[{__name__}] Exception creating project_scope: {str(e)}")
            return f"Error creating project scope: {str(e)}"
    elif scope_direct_data: # Existing project_scope_id and there's direct data to update
        print(f"[{__name__}] Using existing project_scope_id: {project_scope_id}. Attempting to update with: {scope_direct_data}")
        try:
            response = supabase_client.table("project_scopes").update(scope_direct_data).eq("id", project_scope_id).execute()
            if response.error:
                print(f"[{__name__}] Supabase error updating project_scope: {response.error.message}")
            else:
                print(f"[{__name__}] Successfully updated project_scope: {project_scope_id}")
        except Exception as e:
            print(f"[{__name__}] Exception updating project_scope: {str(e)}")
            # If update fails, we might still want to return a message indicating IDs
            # but also the error.
            return f"Error updating project scope for {project_scope_id}: {str(e)}. Homeowner ID: {homeowner_id}"

    if not scope_direct_data and not project_scope_id: # Only print if no data AND it was a new scope attempt that failed earlier
        print(f"[{__name__}] No direct data was provided, and no existing project_scope_id was found or generated.")
        return f"No project details to save and no existing project scope. Homeowner ID: {homeowner_id}"
    elif not scope_direct_data:
        print(f"[{__name__}] No new direct data provided to update existing project_scope_id: {project_scope_id}.")

    return f"Project scope details processed. Homeowner ID: {homeowner_id}, Project Scope ID: {project_scope_id}"


upsert_project_scope_tool = FunctionTool(
    upsert_project_scope_implementation
)

# New tool for uploading images to Supabase Storage
def upload_image_to_storage_implementation(
    tool_context: ToolContext, 
    file_name: Optional[str] = None, # e.g., "photo.jpg"
    bucket_name: str = "project-images",
    process_pending_image: bool = True
) -> str:
    """Uploads an image, previously stored in agent state (tool_context.state['pending_image_data']),
    to Supabase Storage and returns its public URL. Uses tool_context.state['pending_image_mime_type']
    to help determine file_name if not explicitly provided.
    
    Args:
        tool_context: The context providing access to agent state.
        file_name: Optional. The desired file name for the image (e.g., "photo.jpg").
                   If not provided, a name will be derived from mime_type or generated.
        bucket_name: Optional. The Supabase Storage bucket to upload to. 
                     Defaults to "project-images".
        process_pending_image: Flag to confirm processing the image from state. Defaults to True.
    Returns:
        The public URL of the uploaded image, or an error message string.
    """
    logger.debug(f"upload_image_to_storage_tool called. File name: {file_name}, Bucket: {bucket_name}")
    if not process_pending_image:
        return "Image processing not requested by the agent for this call."

    if not supabase_client:
        logger.error("Supabase client not initialized in upload_image_to_storage_tool.")
        return "Error: Supabase client not initialized. Cannot upload image."

    image_data_base64 = tool_context.state.get("pending_image_data")
    pending_mime_type = tool_context.state.get("pending_image_mime_type")

    if not image_data_base64:
        logger.error("No 'pending_image_data' found in agent state for upload_image_to_storage_tool.")
        return "Error: No image data found in agent state to upload."

    try:
        image_data = base64.b64decode(image_data_base64)
        logger.debug("Image data successfully decoded from base64.")
    except Exception as e:
        logger.error(f"Error decoding base64 image data: {str(e)}")
        return f"Error decoding base64 image data: {str(e)}"

    # Determine file extension and content type
    actual_file_name = file_name
    content_type = None

    if not actual_file_name and pending_mime_type:
        # Case 1: No file_name provided, but we have a mime_type from agent state
        ext = mimetypes.guess_extension(pending_mime_type)
        if ext:
            actual_file_name = f"{uuid.uuid4()}{ext}"
            content_type = pending_mime_type
            logger.debug(f"Derived filename '{actual_file_name}' and content_type '{content_type}' from pending_mime_type '{pending_mime_type}'.")
        else:
            # Fallback if mime_type is unknown or doesn't give a common extension
            actual_file_name = f"{uuid.uuid4()}.dat" # Use a generic extension
            content_type = pending_mime_type # Still use the provided mime_type if possible
            logger.debug(f"Could not guess extension for mime_type '{pending_mime_type}'. Using filename '{actual_file_name}' and content_type '{content_type}'.")
    elif actual_file_name:
        # Case 2: file_name IS provided
        content_type, _ = mimetypes.guess_type(actual_file_name)
        if not content_type:
            # If file_name was provided but type couldn't be guessed, default to octet-stream
            logger.warning(f"Could not determine content type for explicitly provided file: '{actual_file_name}'. Defaulting to application/octet-stream.")
            content_type = "application/octet-stream"
        else:
            logger.debug(f"Using explicitly provided filename '{actual_file_name}' and guessed content_type '{content_type}'.")
    else:
        # Case 3: No file_name provided AND no pending_mime_type in state
        actual_file_name = f"{uuid.uuid4()}.png" # Default to png
        content_type = "image/png"
        logger.debug(f"No filename or mime_type provided. Defaulting to filename '{actual_file_name}' and content_type '{content_type}'.")

    # Create a unique path in the bucket to avoid overwriting
    path_in_bucket = f"uploads/{uuid.uuid4()}_{actual_file_name.lstrip('/')}"
    logger.debug(f"Target path in bucket: {path_in_bucket}, Content-Type: {content_type}")

    try:
        response = supabase_client.storage.from_(bucket_name).upload(
            path=path_in_bucket,
            file=image_data,
            file_options={"content-type": content_type, "cache-control": "3600", "upsert": "false"}
        )
        logger.debug(f"Supabase storage upload response status: {response.status_code}")

        if response.status_code == 200:
            # Successfully uploaded, now get the public URL
            public_url = supabase_client.storage.from_(bucket_name).get_public_url(path_in_bucket)
            logger.info(f"Image uploaded successfully. Public URL: {public_url}")
            
            # Clear pending image data from state after successful upload
            if 'pending_image_data' in tool_context.state:
                del tool_context.state['pending_image_data']
                logger.debug("Cleared 'pending_image_data' from agent state.")
            if 'pending_image_mime_type' in tool_context.state:
                del tool_context.state['pending_image_mime_type']
                logger.debug("Cleared 'pending_image_mime_type' from agent state.")
                
            return public_url
        else:
            # Attempt to get error message from response
            try:
                error_content = response.json()
                error_message = error_content.get("message", str(error_content))
            except ValueError: # Not JSON
                error_message = response.text
            logger.error(f"Error uploading image to Supabase Storage: {response.status_code} - {error_message}")
            return f"Error uploading image: {error_message}"

    except Exception as e:
        logger.error(f"Exception during image upload: {str(e)}", exc_info=True)
        return f"Error during image upload: {str(e)}"

# Instantiate the tool
upload_image_to_storage_tool = FunctionTool(
    upload_image_to_storage_implementation
)
