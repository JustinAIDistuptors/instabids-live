import sys
import os
import importlib
import site

print("--- Python Environment Diagnostic (Focused) ---")
print(f"Python Version: {sys.version}")
print(f"Python Executable: {sys.executable}")

print("\n--- sys.path ---")
for p in sys.path:
    print(p)

print("\n--- Site-Packages Directories ---")
site_packages_dirs = site.getsitepackages()
if isinstance(site_packages_dirs, str): # getsitepackages can return str or list
    site_packages_dirs = [site_packages_dirs]

# Also add user site packages
user_site_packages = site.getusersitepackages()
if user_site_packages not in site_packages_dirs:
    site_packages_dirs.append(user_site_packages)

for sp_dir in site_packages_dirs:
    print(f"Site-packages dir: {sp_dir}")
    google_dir_path = os.path.join(sp_dir, 'google')
    print(f"  Checking for google dir: {google_dir_path}")
    if os.path.isdir(google_dir_path):
        print(f"  SUCCESS: 'google' directory found at {google_dir_path}")
        print(f"  Contents of {google_dir_path}:")
        try:
            for item in os.listdir(google_dir_path):
                print(f"    - {item}")
                if item == 'adk':
                    print(f"      SUCCESS: 'adk' subdirectory found in {google_dir_path}!")
                    adk_subdir_path = os.path.join(google_dir_path, 'adk')
                    print(f"      Contents of {adk_subdir_path}:")
                    try:
                        for adk_item in os.listdir(adk_subdir_path):
                            print(f"        - {adk_item}")
                    except Exception as e_ls_adk:
                        print(f"      ERROR listing contents of {adk_subdir_path}: {e_ls_adk}")

        except Exception as e_ls:
            print(f"  ERROR listing contents of {google_dir_path}: {e_ls}")
    else:
        print(f"  INFO: 'google' directory NOT found at {google_dir_path}")


print("\n--- Attempting google.adk import again ---")
try:
    import google.adk
    print(f"SUCCESS: google.adk imported. Version: {getattr(google.adk, '__version__', 'N/A')}")
    print(f"Location: {google.adk.__file__ if hasattr(google.adk, '__file__') else 'N/A'}")
except ImportError as e:
    print(f"ERROR: Could not import google.adk: {e}")
except Exception as e_gen:
    print(f"ERROR: General exception during google.adk import: {e_gen}")

print("\n--- Diagnostic Complete ---")
