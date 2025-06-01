print("SCRIPT_STARTED") # Print immediately
try:
    print("ATTEMPTING_IMPORT_GOOGLE_ADK")
    import google.adk
    print("IMPORT_GOOGLE_ADK_PASSED")
    
    print("ATTEMPTING_IMPORT_LIVEAGENT")
    from google.adk.agents import LiveAgent
    print("IMPORT_LIVEAGENT_PASSED")
    
    print("ADK_IMPORT_SUCCESSFUL_FINAL")
except ImportError as e:
    print("ADK_IMPORT_FAILED: " + str(e))
except Exception as e_gen:
    print("ADK_IMPORT_GENERAL_ERROR: " + str(e_gen))
finally:
    print("SCRIPT_ENDED_IN_FINALLY") # This should execute even if an error occurs in try