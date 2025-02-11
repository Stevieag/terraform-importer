import os
import re
import requests
import random
import subprocess
from typing import List, Dict, Optional
from utils import sanitize_name

def clean_up() -> None:
    """Remove temporary Terraform-related files."""
    os.system("rm -rf .terraform .terraform.lock.hcl import_okta_resources.sh okta_provider.tf")

def get_latest_provider_version(provider_name: str) -> str:
    """Fetch the latest provider version from the Terraform registry."""
    if provider_name == "okta":
        url = "https://registry.terraform.io/v1/providers/okta/okta"
    elif provider_name == "google":
         url = "https://registry.terraform.io/v1/providers/hashicorp/google" #Different URL to Okta
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        return data['version']
    except requests.RequestException as e:
        print(f"Failed to fetch the latest {provider_name} provider version: {e}")
        return "~> 4.0"  # Default version if fetching fails

from terraform_utils import get_latest_provider_version
def create_terraform_config(provider: str, **kwargs) -> None:
    """Generate the Terraform configuration file for the specified provider."""
    google_version = get_latest_provider_version("google")
    okta_version = get_latest_provider_version("okta")

    terraform_block = f"""terraform {{
  required_providers {{
    google = {{
      source  = "hashicorp/google"
      version = "{google_version}"
    }}
    okta = {{
      source = "okta/okta"
      version = "{okta_version}"
        }}
  }}
}}
"""
    with open("main.tf", "w") as f:
        f.write(terraform_block)
    create_provider_block(provider, **kwargs)

def create_provider_block(provider: str, **kwargs) -> None:
    """Generates the provider block"""
    if provider.lower() == "gcp":
        config = f"""provider "google" {{
  project     = "{kwargs['project_id']}"
  region      = "{kwargs.get('region', 'us-central1')}"
  zone        = "{kwargs['zone']}"
  credentials = "{kwargs['creds']}"
}}
"""
    elif provider.lower() == "okta":
        config = f"""provider "okta" {{
  org_name  = "{kwargs['org_name']}"
  base_url  = "{kwargs['base_url']}"
  api_token = "{kwargs['api_key']}"
}}
"""
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    with open("main.tf", "a") as f:
        f.write(config)

    print("\nTerraform configuration created successfully: main.tf")

def create_terraform_import_script(data: List[Dict], resource_type: str) -> Optional[str]:
    """Generate a Terraform import script for Okta resources."""
    temp_output_file = f"terraform_import_{resource_type}.tf"

    try:
        with open(temp_output_file, 'w') as file:
            for item in data:
                if resource_type == 'groups':
                    try:
                        name = item['profile']['name']
                        id_ = item['id']
                        resource_address = f"okta_group.{sanitize_name(name)}"
                    except KeyError as e:
                        print(f"Skipping group with missing 'profile.name' or 'id': {e}")
                        continue  # Skip to the next item if there's a KeyError
                elif resource_type == 'users':
                    try:
                        name = f"{item['profile']['firstName']}_{item['profile']['lastName']}"
                        id_ = item['id']
                        resource_address = f"okta_user.{sanitize_name(name)}"
                    except KeyError as e:
                        print(f"Skipping user with missing 'profile.firstName', 'profile.lastName' or 'id': {e}")
                        continue  # Skip to the next item if there's a KeyError
                else:
                    print(f"Unsupported resource type: {resource_type}")
                    return None

                import_block = f"""import {{
  to = {resource_address}
  id = "{id_}"
}}
"""
                file.write(import_block)
                print(f"Added import block for {name} (ID: {id_})")

        final_output_file = f"output_file_{random.randint(1000, 9999)}_{resource_type}.tf"

        try:
            os.rename(temp_output_file, final_output_file)
            print(f"\nTerraform import script created and renamed to: {final_output_file}")
        except OSError as e:
            print(f"Error renaming file: {e}")
            final_output_file = temp_output_file

        return final_output_file

    except IOError as e:
        print(f"Error creating Terraform import script: {e}")
        return None

def handle_duplicate_imports(file_path: str) -> None:
    """Handle duplicate Terraform imports by renaming them and displaying changes."""
    try:
        # Read the file content
        with open(file_path, "r") as file:
            lines = file.readlines()

        # Variables to track duplicates and modifications
        resource_count = {}
        modified_lines = []
        renamed_resources = {}  # Dictionary to track renamed resources

        # Process each line
        for line in lines:
            match = re.search(r'to\s*=\s*(\w+\.\w+)', line)
            if match:
                resource_name = match.group(1)
                if resource_name in resource_count:
                    # Increment duplicate count and modify resource name
                    resource_count[resource_name] += 1
                    new_resource_name = f"{resource_name}_{resource_count[resource_name]}"
                    renamed_resources[resource_name] = new_resource_name
                    line = line.replace(resource_name, new_resource_name)
                else:
                    # First occurrence of the resource
                    resource_count[resource_name] = 0
            modified_lines.append(line)

        # Write the modified content back to the file
        with open(file_path, "w") as file:
            file.writelines(modified_lines)

        # Display renamed resources
        if renamed_resources:
            print(f"\nDuplicate resources found and renamed in {file_path}:")
            for original, renamed in renamed_resources.items():
                print(f"  - {original} -> {renamed}")
        else:
            print(f"\nNo duplicates found in {file_path}.")

    except IOError as e:
        print(f"Error handling duplicate imports in {file_path}: {e}")

#Copyright (c) 2025 Stephen Agius
#Licensed under the GNU General Public License, version 3.