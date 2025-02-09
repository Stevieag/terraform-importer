import json
import os
import getpass
import requests
import re
import random
import glob
from typing import List, Dict, Optional


def clean_up() -> None:
    """Remove temporary Terraform-related files."""
    os.system("rm -rf .terraform .terraform.lock.hcl import_okta_resources.sh okta_provider.tf")


def check_provider_availability(provider_version: str, latest_version: str) -> None:
    """Check if the specified Okta provider version is available."""
    url = f"https://registry.terraform.io/v1/providers/okta/okta/{provider_version}"
    try:
        response = requests.get(url)
        if response.status_code == 404:
            print(f"\nWARNING: The specified Okta provider version '{provider_version}' is not available.")
            print("This may cause Terraform to fail when initializing.")
            print("Consider using a different version or check your internet connection.")
            print(f"The Latest version is {latest_version}. Other available versions can be found at: "
                  "https://registry.terraform.io/providers/okta/okta/versions")
    except requests.RequestException:
        print("\nWARNING: Unable to verify Okta provider version availability.")
        print("Please ensure you have an active internet connection.")


def check_terraform_init() -> None:
    """Check if Terraform is initialized and initialize or upgrade as needed."""
    if os.path.exists('.terraform'):
        print("Terraform already initialised. Upgrading...")
        os.system("terraform init -upgrade")
    else:
        print("Initialising Terraform...")
        os.system("terraform init")


def get_latest_okta_provider_version() -> str:
    """Fetch the latest Okta provider version from the Terraform registry."""
    url = "https://registry.terraform.io/v1/providers/okta/okta"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data['version']
    except requests.RequestException as e:
        print(f"Failed to fetch the latest Okta provider version: {e}")
        return "~> 4.0"


def get_okta_resources(org_name: str, api_token: str, base_url: str, resource_type: str) -> List[Dict]:
    """Retrieve resources (users/groups) from Okta."""
    resources = []
    if resource_type == "applications":
        url = f"https://{org_name}.{base_url}/api/v1/apps"
    else:
        url = f"https://{org_name}.{base_url}/api/v1/{resource_type}"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"SSWS {api_token}"
    }

    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        resources.extend(response.json())

        links = response.headers.get('Link')
        url = next((link.split(';')[0].strip('<>') for link in links.split(',') if 'rel="next"' in link), None) if links else None

    return resources


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

    with open(temp_output_file, 'w') as file:
        for item in data:
            if resource_type == 'groups':
                name = item['profile']['name']
                id_ = item['id']
                resource_address = f"okta_group.{sanitize_name(name)}"
            elif resource_type == 'users':
                name = f"{item['profile']['firstName']}_{item['profile']['lastName']}"
                id_ = item['id']
                resource_address = f"okta_user.{sanitize_name(name)}"

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

def sanitize_name(name: str) -> str:
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_').lower())
    if sanitized[0].isdigit():
        sanitized = f"r_{sanitized}" 
    return sanitized

def handle_duplicate_imports(file_path: str) -> None:
    """Handle duplicate Terraform imports by renaming them and displaying changes."""
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

def main() -> None:
    """Main function to run the script."""
    resource_types = ['users', 'groups']#, 'applications']  # Added applications

    latest_version = get_latest_okta_provider_version()
    print(f"Latest Okta provider version: {latest_version}")

    api_key = getpass.getpass("Enter your Okta API key: ")
    base_url = input("Enter your Okta Base URL (default: okta.com): ") or "okta.com"
    org_name = input("Enter your Okta Org Name: ")
    provider_version = input(f"Enter Okta provider version (default: {latest_version}): ") or latest_version

    check_provider_availability(provider_version, latest_version)

    create_terraform_config(api_key, base_url, org_name, provider_version)
    print("\nTerraform configuration created successfully!")

    check_terraform_init()

    while True:
        print("\nAvailable Okta resources to import:")
        for i, resource_type in enumerate(resource_types):
            print(f"{i + 1}. {resource_type}")
        print("0. Exit")

        choice = input("Enter the number of the resource to import (or 0 to exit): ")

        if choice == '0':
            print("Exiting resource import.")
            break

        try:
            index = int(choice) - 1
            if 0 <= index < len(resource_types):
                selected_resource_type = resource_types[index]
                if input(f"\nWould you like to import all {selected_resource_type} from Okta? (y/n) ").lower() == "y":
                    resources = get_okta_resources(org_name, api_key, base_url, selected_resource_type)
                    print(f"Total {selected_resource_type} retrieved: {len(resources)}")

                    if resources:
                        if input(f"\nWould you like to save the imported {selected_resource_type} to a file? (y/n) ").lower() == "y":
                            with open(f'okta_{selected_resource_type}.json', 'w') as f:
                                json.dump(resources, f, indent=2)

                        if input(f"\nWould you like to create the import file for {selected_resource_type}? (y/n) ").lower() == 'y':
                            create_terraform_import_script(resources, selected_resource_type)
                    else:
                        print(f"No {selected_resource_type} found in the Okta organization.")
            else:
                print("Invalid choice. Please select a number from the list.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    
    # Handle duplicate imports in generated files
    if input("\nWould you like to handle duplicate imports in generated files? (y/n) ").lower() == 'y':
        for file_path in glob.glob("output_file_*.tf"):
            handle_duplicate_imports(file_path)

if __name__ == "__main__":
    main()

    if input("\nWould you to create a terraform file for all the resources foundnd? (y/n) ").lower() == 'y':
        os.system("terraform plan -generate-config-out=terraform-importer-created.tf")
