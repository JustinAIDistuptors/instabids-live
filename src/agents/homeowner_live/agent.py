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
# Assuming tools and session service are structured under 'src' like other project modules
# If 'instabids' is a top-level package in PYTHONPATH, the original paths are fine.
from src.tools.vision import describe_image_tool
from src.tools.supabase_tools import upsert_project_scope_tool
from src.session.supabase_session import SupabaseSessionService

instruction = (
    "You are a friendly renovation-scope assistant. "
    "Ask clarifying questions, request photos, fill slots "
    "for a project_scope, and call tools to save the scope."
)

class HomeownerLiveAgent(Agent):
    """Converses by voice & chat, analyses images, writes BidCard rows."""
    slots: dict[str, str] = Field(default_factory=dict)

    def __init__(self):
        super().__init__(
            name="homeowner_live",
            model="gemini-2.5-flash-preview-05-20", # Trying specific preview model ID from Colab
            instruction=instruction,
            tools=[describe_image_tool, upsert_project_scope_tool]
        )
        # self.slots is now initialized by Pydantic via Field(default_factory=dict)

    async def async_on_stream(self, event_stream: AsyncIterator[Event]) -> AsyncIterator[Event]: # Changed return type annotation
        """Handles a stream of events for live interaction."""
        async for event in event_stream:
            # Process each event from the stream
            # For example, if it's a user message, you might generate a response
            if event.type == "USER_MESSAGE": # Example event type check
                # ADK Event uses event.data for payload, not event.content directly
                user_text = event.data.parts[0].text if event.data and event.data.parts and event.data.parts[0].text else ""
                print(f"[{self.name}] Received live event: {user_text}")
                # Simple echo for live interaction
                # In a real scenario, you'd likely call an LLM or other logic here
                yield Event(type="agent_says", data=Content(parts=[Part(text=f"Live echo: {user_text}")])) 
            # Ensure to handle other event types or end_of_turn appropriately
        yield Event(type="agent_says", data=Content(parts=[Part(text="Live stream ended.")]), end_of_turn=True)

    async def async_invoke(self, event: Event, invocation_context: InvocationContext) -> Event | None:
        """Handles a single event for non-streaming invocation."""
        print(f"HomeownerLiveAgent async_invoke called with event: {event.type}, context_id: {invocation_context.id if invocation_context else 'None'}")
        
        # ADK Event uses event.data for payload, not event.content directly
        if event.data and event.data.parts and event.data.parts[0].text:
            input_text = event.data.parts[0].text
            response_text = f"HomeownerLiveAgent invoked with: {input_text}"
            return Event(type="agent_says", data=Content(parts=[Part(text=response_text)]))
        return Event(type="agent_says", data=Content(parts=[Part(text="HomeownerLiveAgent invoked without specific text input.")]))

# Instantiate the agent to be exported as root_agent
# This is what src/agents/homeowner_live/__init__.py will import
root_agent = HomeownerLiveAgent()
