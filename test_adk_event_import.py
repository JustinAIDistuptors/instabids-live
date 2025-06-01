print("Attempting to import EventContext and ToolInvocationContext from google.adk.events.event...")
try:
    from google.adk.events.event import EventContext, ToolInvocationContext
    print("Successfully imported EventContext and ToolInvocationContext from google.adk.events.event.")
    print(f"EventContext: {EventContext}")
    print(f"ToolInvocationContext: {ToolInvocationContext}")
except ImportError as e:
    print(f"ImportError: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    import traceback
    traceback.print_exc()
print("Import test finished.")
