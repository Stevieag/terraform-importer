import os
import re
import random
import subprocess
from typing import List, Dict, Optional
from utils import sanitize_name

def clean_up() -> None:
    """Remove temporary Terraform-related files."""
    os.system("rm -rf .terraform .terraform.lock.hcl import_okta_resources.sh okta_provider.tf")

def create_terraform_config(api_key: str, base_url: str, org_name: str, provider_version: str) -> None:
    """Generate the Terraform configuration file for the Okta provider."""
    config = f"""terraform {{
  required_providers {{
    okta = {{
      source  = "okta/okta"
      version = "{provider_version}"
    }}
  }}
}}

provider "okta" {{
  org_name  = "{org_name}"
  base_url  = "{base_url}"
  api_token = "{api_key}"
}}
"""
    with open("okta_provider.tf", "w") as f:
        f.write(config)

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

