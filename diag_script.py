import importlib.metadata
import sys

print(f'Python executable: {sys.executable}')

try:
    print('\n--- Checking google.adk.types ---')
    import google.adk.types
    print(f'google.adk.types location: {google.adk.types.__file__}')
    from google.adk.types import Content, Part
    print('Successfully imported Content, Part from google.adk.types')
except ImportError as e:
    print(f'Error importing from google.adk.types: {e}')
except Exception as e:
    print(f'Unexpected error with google.adk.types: {e}')

try:
    print('\n--- Checking google.adk.events ---')
    import google.adk.events
    print(f'google.adk.events location: {google.adk.events.__file__}')
    print('Attempting to import Content from google.adk.events (expected to fail or not find)...')
    # This is the problematic import, let's see what happens in isolation
    from google.adk.events import Content as EventContent
    print('Unexpectedly imported Content from google.adk.events')
except ImportError as e:
    print(f'Correctly failed to import Content from google.adk.events (or it\'s not there): {e}')
except Exception as e:
    print(f'Unexpected error with google.adk.events: {e}')

try:
    print('\n--- Checking google-adk version ---')
    adk_version = importlib.metadata.version('google-adk')
    print(f'google-adk version: {adk_version}')
except importlib.metadata.PackageNotFoundError:
    print('google-adk package not found by importlib.metadata')
except Exception as e:
    print(f'Unexpected error getting google-adk version: {e}')
