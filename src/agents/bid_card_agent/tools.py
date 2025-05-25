import asyncio
import logging
from typing import Dict, Any, List, Optional
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from google.adk.tools import FunctionTool

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Supabase client initialization
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Ensure this matches your .env file

supabase_client: Optional[Client] = None
if supabase_url and supabase_key:
    try:
        options = ClientOptions(postgrest_client_timeout=10) # Example option, adjust as needed
        supabase_client = create_client(supabase_url, supabase_key, options=options)
        logger.info("Supabase client initialized successfully for BidCardAgent.")
    except Exception as e:
        logger.error(f"Error initializing Supabase client for BidCardAgent: {e}")
else:
    logger.error(
        "Supabase URL or Service Role Key not found in environment variables for BidCardAgent."
    )


# ──────────────────────────────────────────────────────────────
# Helper to run blocking Supabase calls in a thread
# ──────────────────────────────────────────────────────────────
def _query_latest_scope_blocking(sb, homeowner_id: str) -> Dict[str, Any] | None:
    """
    Returns the newest project_scope row (with joined project_images) or None.
    Executed in a thread because supabase-py is sync.
    """
    logger.debug("Supabase: _query_latest_scope_blocking for homeowner_id=%s", homeowner_id)

    resp = (
        sb.table("project_scopes")
        .select("*,project_images(*)")
        .eq("homeowner_id", homeowner_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    logger.debug("Supabase HTTP status (_query_latest_scope_blocking): %s", getattr(resp, "status_code", "N/A"))
    logger.debug("Supabase raw data (_query_latest_scope_blocking): %s", getattr(resp, "data", None))

    if resp and isinstance(resp.data, list) and resp.data:
        return resp.data[0]  # newest row
    return None


async def get_project_details_for_bid_card(
    homeowner_id: str,
    project_id: str = "",
) -> Dict[str, Any] | None:
    """
    Fetch a single project scope (and its images) for a homeowner.

    Args:
        homeowner_id: UUID of the homeowner.
        project_id:   UUID of the specific project.  Empty string = latest project.

    Returns:
        Dict with project & images, or None if nothing found.
    """
    if not supabase_client:
        logger.error("Supabase client not initialised in get_project_details_for_bid_card")
        return None

    try:
        if project_id:
            # direct lookup by project_id AND homeowner_id
            logger.info(f"Supabase: get_project_details_for_bid_card querying for specific project_id: {project_id} AND homeowner_id: {homeowner_id}")
            resp = await asyncio.to_thread(
                lambda: supabase_client.table("project_scopes")
                .select("*,project_images(*)")
                .eq("id", project_id)
                .eq("homeowner_id", homeowner_id) # Crucial: ensure project belongs to the homeowner
                .single() # Expects one row or raises error (0 or >1 rows)
                .execute()
            )
            logger.debug("Supabase HTTP status (lookup by ID): %s", getattr(resp, "status_code", "N/A"))
            logger.debug("Supabase raw data (lookup by ID): %s", getattr(resp, "data", None))
            return resp.data if resp and resp.data else None # resp.data should be the dict if successful, None if .single() found 0 and error was handled by supabase-py, or error raised

        # else: latest project for homeowner
        logger.info(f"Supabase: get_project_details_for_bid_card querying for latest project for homeowner_id: {homeowner_id}")
        row = await asyncio.to_thread(_query_latest_scope_blocking, supabase_client, homeowner_id)
        return row

    except Exception as exc:
        # This will catch errors from .single() if 0 or multiple rows are found for the specific project_id query,
        # or any other unexpected issues.
        logger.exception(f"Supabase query failed in get_project_details_for_bid_card (homeowner_id: {homeowner_id}, project_id: '{project_id}'): {exc}")
        return None

# Create the tool instance and the tool_set
get_project_details_tool = FunctionTool(
    func=get_project_details_for_bid_card,
)

tool_set = [get_project_details_tool]
