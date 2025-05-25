"""
Definition of the BidCardAgent.
"""
import os
from google.adk.agents import Agent
from .instruction import INSTRUCTION
from .tools import tool_set
import logging

logger = logging.getLogger(__name__)

# Determine the model to use, defaulting if not set in environment
DEFAULT_MODEL_NAME = "gemini-2.0-flash" # Or any other suitable default
ADK_MODEL_NAME = os.environ.get("ADK_MODEL_NAME")

if ADK_MODEL_NAME:
    logger.info(f"Using model from ADK_MODEL_NAME: {ADK_MODEL_NAME}")
    MODEL_NAME = ADK_MODEL_NAME
else:
    logger.info(f"ADK_MODEL_NAME not set. Using default model: {DEFAULT_MODEL_NAME}")
    MODEL_NAME = DEFAULT_MODEL_NAME

root_agent = Agent(
    name="bid_card_agent",
    model=MODEL_NAME,
    instruction=INSTRUCTION,
    tools=tool_set,
    description="Agent responsible for creating, presenting, and finalizing bid cards."
)

logger.info(f"BidCardAgent initialized with model: {MODEL_NAME}")
