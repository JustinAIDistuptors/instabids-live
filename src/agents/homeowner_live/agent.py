# src/instabids/agents/homeowner_live.py

from typing import AsyncIterator
from pydantic import Field
from google.adk.agents import Agent # LlmAgent is aliased as Agent here as per inspection
from google.adk.events.event import Event
from google.adk.agents.invocation_context import InvocationContext # For async_invoke context
from google.genai.types import Content, Part # For FunctionCall, FunctionResponse payloads
# EventContext and ToolInvocationContext are removed in ADK v1.1.1;
# their functionality is merged into the Event class and genai.types.
from google.adk.tools.tool_context import ToolContext # Corrected path

import logging
import base64
import uuid

# Assuming tools and session service are structured under 'src' like other project modules
# If 'instabids' is a top-level package in PYTHONPATH, the original paths are fine.
from src.tools.vision import describe_image_tool
from src.tools.supabase_tools import upsert_project_scope_tool, upload_image_to_storage_tool
from src.session.supabase_session import SupabaseSessionService

instruction = """You are the InstaBids Homeowner Helper: friendly, highly observant, efficient, and focused on accurately capturing project needs for bids.


    "# PHASE 1: IMAGE UPLOAD PROTOCOL (IF APPLICABLE)\n"
    "**IF the user's message contains an `inline_data` part (this is where the system places image information):**\n"
    "1.  When `inline_data` is present, the system automatically stores its `data` (base64 image) into `tool_context.state['pending_image_data']` and its `mime_type` into `tool_context.state['pending_image_mime_type']`. You do not need to handle this data directly.\n"
    "2.  **IMMEDIATE FIRST ACTION (if image present): NO GREETING, NO OTHER QUESTIONS.** Your response **MUST BE A CALL** to the `describe_image_tool`. Call it simply as `describe_image_tool()` or `describe_image_tool(process_pending_image=True)`. The tool will automatically use the image data from the agent's state.\n"
    "3.  **SECOND ACTION (after describe_image_tool successfully returns a description):** Your response **MUST BE A CALL** to the `upload_image_to_storage_tool`. You can call it as `upload_image_to_storage_tool()` or `upload_image_to_storage_tool(process_pending_image=True)`. If you want to suggest a filename, you can pass it as `file_name` (e.g., `upload_image_to_storage_tool(file_name='project_photo.jpg')`). The tool will use the image data from the agent's state.\n"
    "4.  Do NOT ask the user for `mime_type` or image data if `inline_data` was present; the system handles storing it for the tools.\n"
    "5.  After both `describe_image_tool` and `upload_image_to_storage_tool` calls are processed, use the image description and the `image_url` (returned by `upload_image_to_storage_tool`) to inform your understanding. Include this `image_url` in the `details` dictionary when calling `upsert_project_scope_tool`. Continue the conversation by asking clarifying questions about the project or the image content.\n"
    "6.  The `upload_image_to_storage_tool` will attempt to clear the `pending_image_data` and `pending_image_mime_type` from the state after a successful upload. If an image was present but you decide not to upload it, you should make a plan to clear these state variables (though specific tools for this are not yet defined, so proceed with caution or note it for future improvement).\n\n"
    "# PHASE 2: CORE GOAL: Collect Project Details & Save via `upsert_project_scope_tool`\n"
    "-   Your main goal is to gather details for a 'project_scope'. This includes understanding the project type, specific work needed, budget, timeline, and location.\n"
    "-   Ask clarifying questions to fill these details. Encourage the user to describe their project thoroughly.\n"
    "-   When you have gathered a significant piece of information or a set of related details for the project scope, you should use the `upsert_project_scope_tool` to save this information. For example, after discussing the kitchen layout and desired changes, you might call `upsert_project_scope_tool`.\n"
    "-   The `upsert_project_scope_tool` will save or update the project scope. When calling `upsert_project_scope_tool`, you **MUST** provide a single keyword argument named `details`. The value for `details` **MUST BE A DICTIONARY** containing all the information gathered.\n"
    "-   This `details` dictionary **MUST** include a key `"project_summary"` whose value is a concise string summarizing all key project details collected so far (e.g., type of work, main requirements, budget if known, location details if known).\n"
    "-   The `details` dictionary can also include other known keys if the information is available. These keys correspond to fields in the main project record: `"project_description"`, `"budget_range"`, `"timeline"`, `"zip_code"`, `"project_title"`, `"status"`, `"image_url"`, `"contractor_notes"`, `"group_bidding_preference"` (this should be a boolean true/false if specified).\n"
    "-   Any other miscellaneous facts or details you've gathered that don't fit the fields above should also be included as additional key-value pairs within this same `details` dictionary (these will be stored as 'other facts').\n"
    "-   Example: If the summary is "Full kitchen remodel", description is "Gutting entire kitchen, new cabinets, granite countertops, island installation", budget is "$20k-$25k", timeline is "3 months", and a miscellaneous fact is "prefers morning work by contractors", the tool call (in the system's internal representation) would look like: `upsert_project_scope_tool(details={"project_summary": "Full kitchen remodel", "project_description": "Gutting entire kitchen, new cabinets, granite countertops, island installation", "budget_range": "$20k-$25k", "timeline": "3 months", "prefers_morning_work": "true"})`\n\n"
    "# GENERAL WORKFLOW\n"
    "1.  **Initial Interaction & Image Handling:**\n"
    "    *   Greet the user and ask about their project.\n"
    "    *   If an image is provided at any point, immediately follow the IMAGE UPLOAD PROTOCOL above.\n"
    "2.  **Information Gathering:**\n"
    "    *   Ask open-ended and specific questions to understand the project (e.g., 'What kind of renovation are you planning?', 'Can you describe the current state?', 'What are your goals for this space?').\n"
    "    *   If an image was described by the `describe_image_tool`, use that information to ask more targeted questions.\n"
    "3.  **Saving Scope:**\n"
    "    *   Periodically, or when the user indicates a section is complete, use the `upsert_project_scope_tool` to save the gathered details.\n"
    "4.  **User Guidance:**\n"
    "    *   Always be helpful and clear. If you use a tool, briefly inform the user what you're doing (e.g., 'Okay, I'll analyze that image.').

5.  **Group Bidding Inquiry (Contextual):**
    *   If the project timeline is flexible (e.g., user mentions a 1-3 month window or similar, rather than an immediate rush), and the project type is suitable (e.g., roofing, siding, windows, painting), ask the user if they are interested in group bidding to potentially save costs. For example: 'Since your timeline for the roof is within the next couple of months, would you be interested in exploring a group bid with other homeowners in your area? This can sometimes lead to cost savings.'
    *   If they express interest, capture this preference (e.g., `group_bidding_preference: true`) when you next save the project scope with `upsert_project_scope_tool`.

# GENERAL FLOW:   "Remember, if an image is present, dealing with it via `describe_image_tool` is your TOP PRIORITY for that turn."""

class HomeownerLiveAgent(Agent):
    """Converses by voice & chat, analyses images, writes BidCard rows."""
    slots: dict[str, str] = Field(default_factory=dict)

    def __init__(self):
        super().__init__(
            name="homeowner_live",
            model="gemini-2.5-flash-preview-05-20",  # Updated model
            instruction=instruction,
            tools=[describe_image_tool, upsert_project_scope_tool, upload_image_to_storage_tool]
        )
        # self.slots is now initialized by Pydantic via Field(default_factory=dict)

    async def async_on_message(self, tool_context: ToolContext) -> Event | None:
        logger = logging.getLogger(__name__)
        # !!!!! VERY IMPORTANT DIAGNOSTIC LOG !!!!!
        logger.critical("!!!!!!!! ASYNC_ON_MESSAGE CALLED FOR HOMEOWNER_LIVE !!!!!!!!")
        logger.info(f"[{self.name}] Raw tool_context.message: {tool_context.message}")
        if hasattr(tool_context.message, '__dict__'):
            logger.info(f"[{self.name}] Raw tool_context.message.__dict__: {tool_context.message.__dict__}")
        else:
            logger.info(f"[{self.name}] Raw tool_context.message has no __dict__.")

        logger.info(f"[{self.name}] State BEFORE super().async_on_message AND manual processing: {tool_context.state}")

        # Original detailed logging for parts processing
        logger.info(f"[{self.name}] Entering async_on_message for message (second log).") # Differentiate from first entry log
        logger.debug(f"[{self.name}] tool_context.message type: {type(tool_context.message)}")
        if hasattr(tool_context.message, 'parts'):
            logger.debug(f"[{self.name}] tool_context.message.parts: {tool_context.message.parts}")
        else:
            logger.debug(f"[{self.name}] tool_context.message has no 'parts' attribute.")

        image_data_processed_from_parts = False
        if tool_context.message and hasattr(tool_context.message, 'parts') and tool_context.message.parts:
            for part_idx, part in enumerate(tool_context.message.parts):
                logger.debug(f"[{self.name}] Examining part #{part_idx}: {type(part)}")
                if hasattr(part, 'inline_data') and part.inline_data and hasattr(part.inline_data, 'data'):
                    logger.info(f"[{self.name}] Found inline_data in message part #{part_idx}.")
                    logger.debug(f"[{self.name}] part.inline_data type: {type(part.inline_data)}")
                    logger.debug(f"[{self.name}] part.inline_data.mime_type: {part.inline_data.mime_type}")
                    
                    image_bytes = part.inline_data.data
                    logger.debug(f"[{self.name}] part.inline_data.data type: {type(image_bytes)}")
                    
                    if image_bytes:
                        logger.info(f"[{self.name}] part.inline_data.data is present. Length (bytes): {len(image_bytes)}")
                        image_data_base64 = base64.b64encode(image_bytes).decode('utf-8')
                        tool_context.state['pending_image_data'] = image_data_base64
                        tool_context.state['pending_image_mime_type'] = part.inline_data.mime_type
                        image_data_processed_from_parts = True
                        logger.info(f"[{self.name}] Successfully processed and stored base64 image data and mime_type from part #{part_idx} into state.")
                        # It's generally safer to process only the first image found.
                        # If multiple images in one message need different handling, the logic would need to be more complex.
                        break 
                    else:
                        logger.warning(f"[{self.name}] part.inline_data.data is present but empty (falsey).")
                else:
                    logger.debug(f"[{self.name}] Part #{part_idx} does not have usable inline_data. Has inline_data: {hasattr(part, 'inline_data')}")
                    if hasattr(part, 'inline_data') and part.inline_data:
                         logger.debug(f"[{self.name}] Part #{part_idx} inline_data content: {part.inline_data}")

        if not image_data_processed_from_parts:
            logger.info(f"[{self.name}] No image data was processed from message parts.")

        logger.info(f"[{self.name}] State AFTER manual processing, BEFORE super().async_on_message: {tool_context.state}")
        if "session_id" not in tool_context.state:
            tool_context.state["session_id"] = str(uuid.uuid4())
            logger.info(f"[{self.name}] New session_id generated and saved to state: {tool_context.state['session_id']}")
        
        logger.debug(f"[{self.name}] State after async_on_message custom logic: {tool_context.state.get('pending_image_mime_type', 'No image mime type in state')}, Image data present: {'pending_image_data' in tool_context.state}")
        logger.info(f"[{self.name}] Exiting async_on_message.")
        return await super().async_on_message(tool_context)

    async def async_on_stream(self, event_stream: AsyncIterator[Event]) -> AsyncIterator[Event]: # Changed return type annotation
        """Handles a stream of events for live interaction.
        Delegates to the base class implementation for LLM interaction and tool calling based on instructions.
        """
        # To rely on the base Agent's LLM interaction and tool calling for streaming:
        async for event_out in super().async_on_stream(event_stream):
            yield event_out

    async def async_invoke(self, event: Event, invocation_context: InvocationContext) -> Event | None:
        """Handles a single event for non-streaming invocation.
        Delegates to the base class implementation for LLM interaction and tool calling based on instructions.
        """
        # To rely on the base Agent's LLM interaction and tool calling:
        return await super().async_invoke(event, invocation_context)

# Instantiate the agent to be exported as root_agent
# This is what src/agents/homeowner_live/__init__.py will import
root_agent = HomeownerLiveAgent()
