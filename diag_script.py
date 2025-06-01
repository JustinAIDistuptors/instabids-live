import importlib
import pkgutil
import sys

OUTPUT_FILE = "diag_output.txt"

with open(OUTPUT_FILE, "w", encoding="utf-8") as f_out:
    def write_log(message):
        f_out.write(str(message) + "\n")
        print(message) # Also print to console for immediate feedback if possible

    write_log(f"Python version: {sys.version}")
    write_log(f"Python executable: {sys.executable}")
    write_log(f"sys.path:")
    for p_idx, p_val in enumerate(sys.path):
        write_log(f"  [{p_idx}] {p_val}")

    write_log("-" * 50)

    try:
        write_log("Attempting to import 'google'...")
        import google
        write_log(f"Successfully imported 'google'.")
        write_log(f"google.__file__ -> {getattr(google, '__file__', 'N/A')!r}")
        write_log("google.__path__:")
        if hasattr(google, '__path__'):
            for p_idx, p_val in enumerate(google.__path__):
                write_log(f"  [{p_idx}] {p_val}")
        else:
            write_log("   google module has no __path__ attribute (not a namespace package or not found correctly)")

        write_log("-" * 50)
        write_log("Attempting to import 'google.adk'...")
        import google.adk
        write_log(f"Successfully imported 'google.adk'.")
        write_log(f"google.adk.__file__ -> {getattr(google.adk, '__file__', 'N/A')!r}")
        write_log(f"google.adk.__version__ -> {getattr(google.adk, '__version__', 'N/A')!r}")
        write_log("google.adk.__path__:")
        if hasattr(google.adk, '__path__'):
            for p_idx, p_val in enumerate(google.adk.__path__):
                write_log(f"  [{p_idx}] {p_val}")

            write_log("\\nIterating modules in google.adk.__path__:")
            if google.adk.__path__ and all(isinstance(path_item, str) for path_item in google.adk.__path__):
                mods = [m.name for m in pkgutil.iter_modules(google.adk.__path__)]
                write_log(f"  Modules found: {mods[:20]} {'...' if len(mods) > 20 else ''}")
                if not mods:
                    write_log("  No modules found directly in google.adk.__path__ by pkgutil.iter_modules.")
            else:
                write_log("  google.adk.__path__ is empty, contains non-string elements, or does not exist. Cannot iterate modules.")
        else:
            write_log("   google.adk module has no __path__ attribute.")

        write_log("-" * 50)
        write_log("Attempting to import 'google.adk.context'...")
        from google.adk import context
        write_log(f"\\n✅ Successfully imported 'google.adk.context'.")
        write_log(f"   google.adk.context.__file__ -> {getattr(context, '__file__', 'N/A')!r}")
        write_log(f"   First 5 attributes of context: {dir(context)[:5]} ...")

    except ImportError as ie:
        write_log(f"\\n❌ IMPORT ERROR: {ie}")
        write_log(f"   Failed to import: {ie.name}")
        if ie.path is not None:
            write_log(f"   Path involved: {ie.path}")
    except Exception as e:
        write_log(f"\\n❌ UNEXPECTED ERROR: {type(e).__name__}: {e}")

    write_log("-" * 50)
    write_log("Script finished.")
