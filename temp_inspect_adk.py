import importlib
import inspect
import sys
import os

output_file_path = os.path.join(os.getcwd(), "adk_inspection_results.txt")
original_stdout = sys.stdout

with open(output_file_path, 'w', encoding='utf-8') as f_out:
    sys.stdout = f_out
    print(f"Python version: {sys.version}")
    print(f"Python path: {sys.path}")
    print(f"Current working directory: {os.getcwd()}")

    def check_module(module_name_str):
        print(f"\n--- Checking module: {module_name_str} ---")
        try:
            module = importlib.import_module(module_name_str)
            print(f"Successfully imported {module_name_str}")
            print(f"Contents of {module_name_str} (path: {getattr(module, '__file__', 'N/A')}):")
            
            members = []
            try:
                members = dir(module)
            except Exception as e:
                print(f"  Error calling dir() on {module_name_str}: {e}")

            for name in members:
                if name.startswith('_') and name != '__all__':
                    continue

                try:
                    attr = getattr(module, name)
                    attr_type_str = ""
                    try:
                        attr_type_str = str(type(attr))
                    except Exception:
                        attr_type_str = "[could not get type]"
                    
                    if inspect.isclass(attr):
                        class_module = getattr(attr, '__module__', 'N/A')
                        print(f"  - {name} (Class, from module: {class_module})")
                        if name == "LiveAgent":
                            print(f"    !!!! FOUND LiveAgent in {module_name_str} as {name} (module: {class_module}) !!!!")
                    elif inspect.ismodule(attr):
                        submodule_path = getattr(attr, '__file__', 'N/A')
                        print(f"  - {name} (Submodule, path: {submodule_path})")
                    else:
                        print(f"  - {name} (Type: {attr_type_str})")

                except Exception as e:
                    print(f"  - {name} (Error inspecting member: {e})")
            return module
        except ImportError as e:
            print(f"Failed to import {module_name_str}: {e}")
        except Exception as e:
            print(f"Error inspecting module {module_name_str}: {e}")
        return None

    print("\nInspecting google.adk.agents...")
    agents_module = check_module("google.adk.agents")

    potential_submodules_to_check = ["google.adk.agents.live", "google.adk.agents.core_agents", "google.adk.agents.experimental"]
    if agents_module:
        for name in dir(agents_module):
            if not name.startswith('_'):
                try:
                    attr = getattr(agents_module, name)
                    if inspect.ismodule(attr):
                        submodule_full_name = getattr(attr, '__name__', f"google.adk.agents.{name}")
                        if submodule_full_name not in potential_submodules_to_check:
                            potential_submodules_to_check.append(submodule_full_name)
                except Exception:
                    pass

    print("\nInspecting potential submodules...")
    for sub_mod_name in sorted(list(set(potential_submodules_to_check))):
        check_module(sub_mod_name)

    print("\n--- Direct import attempts for LiveAgent ---")
    direct_import_paths = [
        "google.adk.agents.LiveAgent",
        "google.adk.agents.live.LiveAgent",
        "google.adk.agents.core.LiveAgent",
        "google.adk.live.LiveAgent",
        "google.adk.experimental.LiveAgent"
    ]

    for path_str in direct_import_paths:
        try:
            parts = path_str.split('.')
            class_name = parts[-1]
            module_path = '.'.join(parts[:-1])
            
            module_to_import = importlib.import_module(module_path)
            LiveAgentClass = getattr(module_to_import, class_name)
            
            print(f"Successfully imported: from {module_path} import {class_name}")
            print(f"  {class_name} type: {type(LiveAgentClass)}, module: {LiveAgentClass.__module__}")
        except (ImportError, AttributeError) as e:
            print(f"Failed direct import/getattr: from {module_path} import {class_name} ({e})")
        except Exception as e:
            print(f"Unexpected error with {path_str}: {e}")

    print("\nInspection complete.")

sys.stdout = original_stdout
print(f"Inspection output saved to: {output_file_path}")
