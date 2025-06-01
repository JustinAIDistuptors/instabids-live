# src/tools/supabase_tools.py
print(f"[{__file__}] Attempting to load src.tools.supabase_tools", flush=True)
from google.adk.tools import FunctionTool, ToolContext
from supabase import create_client, Client as SupabaseClient
import os
import uuid # For generating IDs if needed
import json # For handling potential JSON in fact_value

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

async def upsert_project_scope_implementation(tool_context: ToolContext, **slots: dict) -> str:
    """
    Upserts project scope data (slots) to Supabase.
    Manages homeowner_id and project_scope_id from agent state.
    """
    if not supabase_client:
        print(f"[{__name__}] ERROR: Supabase client not initialized in upsert_project_scope_tool.")
        return "Error: Supabase client not initialized. Cannot save project scope."

    print(f"[{__name__}] upsert_project_scope_tool called with slots: {slots}")
    print(f"[{__name__}] Current agent state from tool_context: {tool_context.state}")

    # Get or create homeowner_id from agent state
    homeowner_id = tool_context.state.get("current_homeowner_id")
    if not homeowner_id:
        homeowner_id = str(uuid.uuid4())
        tool_context.state["current_homeowner_id"] = homeowner_id
        print(f"[{__name__}] Generated new homeowner_id: {homeowner_id} and updated agent state.")

    # Get or create project_scope_id from agent state
    project_scope_id = tool_context.state.get("current_project_scope_id")
    if not project_scope_id:
        project_scope_id = str(uuid.uuid4())
        tool_context.state["current_project_scope_id"] = project_scope_id
        print(f"[{__name__}] Generated new project_scope_id: {project_scope_id} and updated agent state.")
        # Create a new project scope entry in 'project_scopes' table
        try:
            scope_insert_data = {
                "id": project_scope_id,
                "homeowner_id": homeowner_id,
                # Add other initial fields for project_scopes if necessary, e.g., status
                # "status": "new" 
            }
            print(f"[{__name__}] Attempting to insert new project_scope: {scope_insert_data}")
            response = await supabase_client.table("project_scopes").insert(scope_insert_data).execute()
            if response.data:
                print(f"[{__name__}] Successfully created new project_scope: {project_scope_id}")
            elif response.error:
                print(f"[{__name__}] Supabase error creating project_scope: {response.error.message}")
                # If scope creation fails, we might not want to proceed with facts
                return f"Error creating project scope: {response.error.message}"
            else:
                print(f"[{__name__}] Failed to create project_scope (no data/error): {response}")
                return "Failed to create project scope (no data/error from Supabase)."

        except Exception as e:
            print(f"[{__name__}] Exception creating project_scope: {str(e)}")
            return f"Error creating project scope: {str(e)}"
    else:
        print(f"[{__name__}] Using existing project_scope_id from agent state: {project_scope_id}")


    # Prepare data for project_scope_facts
    facts_to_insert = []
    for key, value in slots.items():
        if value is not None: # Only insert non-null values
            # Ensure value is string, handle dicts/lists by converting to JSON string
            fact_val_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            facts_to_insert.append({
                "project_scope_id": project_scope_id,
                "fact_key": key,
                "fact_value": fact_val_str
            })
    
    if facts_to_insert:
        print(f"[{__name__}] Attempting to upsert facts for project_scope_id {project_scope_id}: {facts_to_insert}")
        try:
            # Supabase upsert: if (project_scope_id, fact_key) conflict, update fact_value.
            # The `on_conflict` parameter should name the constraint or columns involved in the conflict.
            # Assuming you have a unique constraint on (project_scope_id, fact_key) in project_scope_facts.
            # If not, you'll need to add one:
            # ALTER TABLE project_scope_facts ADD CONSTRAINT unique_scope_fact UNIQUE (project_scope_id, fact_key);
            
            response = await supabase_client.table("project_scope_facts").upsert(
                facts_to_insert,
                on_conflict="project_scope_id,fact_key" # Specify columns for conflict resolution
            ).execute()

            if response.data:
                print(f"[{__name__}] Successfully upserted facts for project_scope_id: {project_scope_id}")
            elif response.error:
                print(f"[{__name__}] Supabase error upserting facts: {response.error.message}")
                return f"Error saving project details: {response.error.message}"
            else:
                print(f"[{__name__}] Failed to upsert facts (no data/error): {response}")
                return "Failed to save project details (no data/error from Supabase)."

        except Exception as e:
            print(f"[{__name__}] Exception upserting facts: {str(e)}")
            # Check if the error message indicates a missing unique constraint for on_conflict
            if "constraint" in str(e).lower() and "does not exist" in str(e).lower():
                print(f"[{__name__}] HINT: The upsert failed. You might be missing a unique constraint on (project_scope_id, fact_key) in the 'project_scope_facts' table.")
                print(f"[{__name__}] Try adding it with: ALTER TABLE project_scope_facts ADD CONSTRAINT unique_scope_fact UNIQUE (project_scope_id, fact_key);")
            return f"Error saving project details: {str(e)}"
    else:
        print(f"[{__name__}] No slot data provided to upsert_project_scope_tool.")
        return f"No details provided to save. Homeowner ID: {homeowner_id}, Project Scope ID: {project_scope_id}"

    return f"Project scope details saved. Homeowner ID: {homeowner_id}, Project Scope ID: {project_scope_id}"


upsert_project_scope_tool = FunctionTool(
    upsert_project_scope_implementation
)
