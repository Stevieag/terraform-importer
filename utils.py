import re
import subprocess
import os

def sanitize_name(name: str) -> str:
    """Sanitize a string to be a valid Terraform resource name."""
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_').lower())
    if sanitized and sanitized[0].isdigit():
        sanitized = f"r_{sanitized}"
    return sanitized if sanitized else "default_resource"  # Ensure a non-empty string is always returned

def check_terraform_init() -> bool:
    """Check if Terraform is initialized and initialize or upgrade as needed.  Returns True if successful, False otherwise."""
    try:
        if os.path.exists('.terraform'):
            print("Terraform already initialised. Upgrading...")
            result = subprocess.run(["terraform", "init", "-upgrade"], capture_output=True, text=True, check=True)
            print(result.stdout)
            print("Terraform upgraded successfully.")
        else:
            print("Initialising Terraform...")
            result = subprocess.run(["terraform", "init"], capture_output=True, text=True, check=True)
            print(result.stdout)
            print("Terraform initialised successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during Terraform initialisation/upgrade: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Error: Terraform is not installed or not in your PATH.")
        return False
