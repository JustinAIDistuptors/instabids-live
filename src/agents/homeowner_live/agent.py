# src/instabids/agents/homeowner_live.py
from google.adk.agents import LiveAgent
from google.adk.events import Event, Content, Part
from google.adk.context import EventContext, ToolInvocationContext
from google.adk.types import ToolContext
# Assuming tools and session service are structured under 'src' like other project modules
# If 'instabids' is a top-level package in PYTHONPATH, the original paths are fine.
# For now, sticking to brief's 'instabids.' prefix.
from src.tools.vision import describe_image_tool
from src.tools.supabase_tools import upsert_project_scope_tool
from src.session.supabase_session import SupabaseSessionService

class HomeownerLiveAgent(LiveAgent):
    """Converses by voice & chat, analyses images, writes BidCard rows."""

    def __init__(self):
        super().__init__(
            name="homeowner",
            model="models/gemini-2.5-flash-preview-native-audio-dialog",
            instruction=(
                "You are a friendly renovation-scope assistant. "
                "Ask clarifying questions, request photos, fill slots "
                "(budget, timeline, location, category)."
            ),
            tools=[describe_image_tool, upsert_project_scope_tool],
            session_service=SupabaseSessionService()
        )
        self.slots: dict[str, str] = {}

    async def async_on_stream(
        self,
        ctx: EventContext,
        *,
        last_event: Event | None = None,
        tool_ctx: ToolInvocationContext | None = None
    ):
        # 1 · Handle new incoming parts
        if last_event and last_event.content.parts:
            part: Part = last_event.content.parts[-1]

            # IMAGE → call Vision tool
            if part.mime_type.startswith("image/"):
                summary = await self.call_tool(
                    "describe_image_tool",
                    {"image_bytes": part.data}
                )
                await ctx.send(f"I’m seeing: {summary}")

            # TEXT → simple slot filling
            elif part.mime_type == "text/plain":
                text = part.text.strip().lower()
                if "budget" in text and "$" in text:
                    self.slots["budget"] = text
                # …keep going for timeline / category …

        # 2 · When all slots ready → save to Supabase
        required = {"budget", "timeline", "category", "location"}
        if required.issubset(self.slots):
            await self.call_tool("upsert_project_scope_tool", self.slots)
            await ctx.send(
                "Great! I’ve created your project card ✅. "
                "Contractors will be invited shortly.",
                end_of_turn=True
            )
            self.slots.clear()  # new session later

root_agent = HomeownerLiveAgent()
