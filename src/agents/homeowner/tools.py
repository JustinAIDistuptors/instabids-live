# tools.py for HomeownerAgent
import os
import uuid
from supabase import create_client, Client as SupabaseClient
from google.adk.tools import ToolContext
import base64
import re # Import re for regex operations

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
