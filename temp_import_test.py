# c:\Users\Not John Or Justin\Documents\GitHub\instabids-live\temp_import_test.py
print("--- Attempting to import SessionService ---")
try:
    from google.adk.sessions.session_service import SessionService
    print("SUCCESS: Imported SessionService from google.adk.sessions.session_service")
    print(f"SessionService object: {SessionService}")
except ImportError as e:
    print(f"FAILED SessionService ImportError: {e}")
except ModuleNotFoundError as e:
    print(f"FAILED SessionService ModuleNotFoundError: {e}")
print("-" * 40)

print("\n--- Attempting to import SessionState ---")
try:
    from google.adk.sessions.session import SessionState
    print("SUCCESS: Imported SessionState from google.adk.sessions.session")
    print(f"SessionState object: {SessionState}")
except ImportError as e:
    print(f"FAILED SessionState ImportError: {e}")
except ModuleNotFoundError as e:
    print(f"FAILED SessionState ModuleNotFoundError: {e}")
print("-" * 40)

import sys
print("\n--- sys.path ---")
for p in sys.path:
    print(p)
print("-" * 40)

print("\n--- Inspecting google.adk.sessions package ---")
try:
    import google.adk.sessions
    print(f"SUCCESS: Imported google.adk.sessions")
    print(f"dir(google.adk.sessions): {dir(google.adk.sessions)}")
    try:
        print(f"google.adk.sessions.__file__: {google.adk.sessions.__file__}")
    except AttributeError:
        print("google.adk.sessions has no __file__ attribute (might be a namespace package or issue)")

    # Check if 'session_service' is an attribute (e.g., if __init__.py makes it available)
    if hasattr(google.adk.sessions, 'session_service'):
        print("FOUND: 'session_service' as attribute of google.adk.sessions")
        print(f"google.adk.sessions.session_service: {google.adk.sessions.session_service}")
    else:
        print("NOT FOUND: 'session_service' as attribute of google.adk.sessions")

    # Check if 'session' is an attribute
    if hasattr(google.adk.sessions, 'session'):
        print("FOUND: 'session' as attribute of google.adk.sessions")
        print(f"google.adk.sessions.session: {google.adk.sessions.session}")
    else:
        print("NOT FOUND: 'session' as attribute of google.adk.sessions")

except Exception as e:
    print(f"FAILED to import or inspect google.adk.sessions: {e}")
print("-" * 40)
