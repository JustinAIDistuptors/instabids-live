# This file makes 'bid_card_agent' a Python package
# and exports its root_agent for discovery by ADK.

from .agent import root_agent

__all__ = ["root_agent"]
