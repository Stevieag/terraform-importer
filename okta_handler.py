import json
import os
import getpass
import requests
import random
import glob
from typing import List, Dict, Optional
from terraform_utils import create_terraform_config, create_terraform_import_script, handle_duplicate_imports
from utils import sanitize_name, check_terraform_init


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

def main() -> None:
    """Main function to run the Okta resource import."""
    resource_types = ['users', 'groups']  # Removed applications for now

    latest_version = get_latest_okta_provider_version()
    print(f"Latest Okta provider version: {latest_version}")

    api_key = getpass.getpass("Enter your Okta API key: ")
    base_url = input("Enter your Okta Base URL (default: okta.com): ") or "okta.com"
    org_name = input("Enter your Okta Org Name: ")
    provider_version = input(f"Enter Okta provider version (default: {latest_version}): ") or latest_version

    check_provider_availability(provider_version, latest_version)

    create_terraform_config(
        provider="okta",
        api_key=api_key,
        base_url=base_url,
        org_name=org_name,
        provider_version=provider_version
    )
    print("\nTerraform configuration created successfully!")

    if not check_terraform_init():
        print("Terraform initialisation failed.  Please check your Terraform installation and configuration.")
        return  # Exit the function if Terraform init fails

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
                            import_file = create_terraform_import_script(resources, selected_resource_type)
                            if import_file:
                                print(f"Terraform import script created: {import_file}")
                                if input("\nWould you like to handle duplicate imports in this file? (y/n) ").lower() == 'y':
                                    handle_duplicate_imports(import_file)
                    else:
                        print(f"No {selected_resource_type} found in the Okta organization.")
            else:
                print("Invalid choice. Please select a number from the list.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    
    # Handle duplicate imports in generated files
    if input("\nWould you like to handle duplicate imports in *all* generated files? (y/n) ").lower() == 'y':
        for file_path in glob.glob("output_file_*.tf"):
            handle_duplicate_imports(file_path)

#Example use
if __name__ == "__main__":
    main()



#Copyright (c) 2025 Stephen Agius
#Licensed under the GNU General Public License, version 3.