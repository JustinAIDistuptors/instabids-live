import traceback
print('Attempting to import google.adk from script...')
try:
    import google.adk
    print('Successfully imported google.adk. ADK version: ' + str(google.adk.__version__))
except Exception as e:
    print('Failed to import google.adk:')
    traceback.print_exc()
