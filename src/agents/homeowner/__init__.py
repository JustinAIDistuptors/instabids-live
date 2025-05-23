"""
HomeownerAgent package.
"""

import sys
import os
print(f"[{__file__}] Loaded homeowner agent module.")
print(f"[{__file__}] CWD: {os.getcwd()}")
print(f"[{__file__}] sys.path: {sys.path}")
from .agent import root_agent

__all__ = ["root_agent"]
