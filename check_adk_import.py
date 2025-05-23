import sys
print(f"Python Executable: {sys.executable}")
print(f"Sys Path: {sys.path}")
try:
    # Import the 'types' module as suggested by google-genai PyPI page
    from google.genai import types
    # Then access Content and Part as attributes
    Content = types.Content
    Part = types.Part
    print("Successfully accessed Content, Part from 'google.genai.types'")
except ImportError as e_gg_types_module:
    print(f"Failed to import 'types' from 'google.genai': {e_gg_types_module}")
except AttributeError as e_gg_types_attr:
    print(f"Failed to access Content/Part as attributes of 'google.genai.types': {e_gg_types_attr}")

# For diagnostics, let's also check if google.adk.events.Event is importable
try:
    from google.adk.events import Event
    print("Successfully imported Event from google.adk.events")
except ImportError as e_adk_event:
    print(f"Failed to import Event from google.adk.events: {e_adk_event}")
