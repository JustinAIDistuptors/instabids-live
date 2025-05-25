from google.adk.agents import Agent
from google.adk.tools import ToolContext 
from google.genai import types
import logging

# General debug logging
logging.basicConfig(level=logging.DEBUG)

# Specific logger for our parts dumping
parts_logger = logging.getLogger("ImageTestAgentParts")
parts_logger.setLevel(logging.DEBUG) # Ensure this logger outputs DEBUG messages

def dump_user_message_parts(tool_context: ToolContext) -> str:
    """
    Logs the parts of the last user message from the ToolContext.
    The LLM should call this tool after receiving an image.
    """
    if not tool_context.history:
        parts_logger.warning("dump_user_message_parts: No history in ToolContext.")
        return "Error: No history found in ToolContext."

    # The last message in history should be the user's current input
    # However, history might also include previous agent turns.
    # We are interested in the message that triggered this agent turn.
    # The ADK structures this such that the relevant user message parts
    # are directly available in invocation_context.new_message.parts
    # but tools don't directly get invocation_context.
    # Let's assume the most recent user message in history is the one we want.
    
    user_messages = [msg for msg in tool_context.history if msg.role == "user"]
    if not user_messages:
        parts_logger.warning("dump_user_message_parts: No user messages in ToolContext history.")
        return "Error: No user messages found in history."

    last_user_message = user_messages[-1]

    if not last_user_message.content or not last_user_message.content.parts:
        parts_logger.warning("dump_user_message_parts: No content or parts in last user message.")
        return "Error: No content or parts in the last user message."

    parts_logger.debug("--- Dumping User Message Parts (from ToolContext history) ---")
    for i, p in enumerate(last_user_message.content.parts):
        # Ensure the logger we configured is used
        parts_logger.debug("CONTEXT_PART %d → %s", i, p)
    parts_logger.debug("--- End Dumping User Message Parts ---")
    return "Image parts logged to debug output. Please check terminal."

root_agent = Agent(
    name="image_test_agent",
    model="gemini-2.0-flash",
    instruction=(
        "If the user sends an image, you MUST respond with the exact phrase 'Got it!'. "
        "After saying 'Got it!', you MUST then call the 'dump_user_message_parts' tool to log the details of the image received. "
        "Do not add any other commentary."
    ),
    tools=[dump_user_message_parts], # Use the new tool
)
