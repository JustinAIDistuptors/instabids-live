import traceback

# Initialize results to 'Not run' or None
adk_version_info = 'ADK import not attempted or failed'
importlib_info = 'Importlib import not attempted or failed'
find_spec_module_info = 'find_spec for module not attempted or failed'
find_spec_package_info = 'find_spec for package not attempted or failed'
error_info = None

print("--- Running src/check_module_visibility.py (absolute_minimal_v1) ---", flush=True)

try:
    print("[SCRIPT] Attempting: import google.adk", flush=True)
    import google.adk
    adk_version_info = f"Successfully imported google.adk, version: {google.adk.__version__}"
    print(f"[SCRIPT] {adk_version_info}", flush=True)

    print("[SCRIPT] Attempting: import importlib.util", flush=True)
    import importlib.util
    importlib_info = "Successfully imported importlib.util"
    print(f"[SCRIPT] {importlib_info}", flush=True)

    candidate_module = "src.agents.homeowner_live"
    print(f"[SCRIPT] Attempting: importlib.util.find_spec('{candidate_module}')", flush=True)
    spec_module = importlib.util.find_spec(candidate_module)
    find_spec_module_info = f"find_spec('{candidate_module}') result: {str(spec_module)}"
    print(f"[SCRIPT] {find_spec_module_info}", flush=True)

    candidate_package = "src.agents"
    print(f"[SCRIPT] Attempting: importlib.util.find_spec('{candidate_package}')", flush=True)
    spec_package = importlib.util.find_spec(candidate_package)
    find_spec_package_info = f"find_spec('{candidate_package}') result: {str(spec_package)}"
    print(f"[SCRIPT] {find_spec_package_info}", flush=True)

except Exception as e:
    print("[SCRIPT] ERROR occurred:", flush=True)
    # Capture traceback to a string to print in finally block
    error_info = traceback.format_exc()

finally:
    print("\n--- [SCRIPT] FINAL DIAGNOSTIC RESULTS ---", flush=True)
    print(f"ADK Import Status: {adk_version_info}", flush=True)
    print(f"Importlib Import Status: {importlib_info}", flush=True)
    print(f"Module Spec (src.agents.homeowner_live): {find_spec_module_info}", flush=True)
    print(f"Package Spec (src.agents): {find_spec_package_info}", flush=True)
    if error_info:
        print("\n[SCRIPT] Captured Error Traceback:\n", error_info, flush=True)
    else:
        print("\n[SCRIPT] No Python-level errors captured during try block.", flush=True)
    print("--- [SCRIPT] Finished --- ", flush=True)

