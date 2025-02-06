import json
import os
import getpass
import requests
import re

def clean_up():
    os.system("rm -rf .terraform .terraform.lock.hcl import_okta_resources.sh okta_provider.tf")

def check_provider_availability(provider_version, latest_version):
    url = f"https://registry.terraform.io/v1/providers/okta/okta/{provider_version}"
    try:
        response = requests.get(url)
        if response.status_code == 404:
            print(f"\nWARNING: The specified Okta provider version is not available.")
            print("This may cause Terraform to fail when initializing.")
            print("Consider using a different version or check your internet connection.")
            print(f"The Latest version is {latest_version}. Other available versions can be found at: https://registry.terraform.io/providers/okta/okta/versions")
    except requests.RequestException:
        print("\nWARNING: Unable to verify Okta provider version availability.")
        print("Please ensure you have an active internet connection.")

def check_terraform_init():
    if os.path.exists('.terraform'):
        print("Terraform already initialised. Upgrading...")
        os.system("terraform init -upgrade")
    else:
        print("Initialising Terraform...")
        os.system("terraform init")

def get_latest_okta_provider_version():
    url = "https://registry.terraform.io/v1/providers/okta/okta"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data['version']
    except requests.RequestException as e:
        print(f"Failed to fetch the latest Okta provider version: {e}")
        return "~> 4.0"

def get_okta_resources(org_name, api_token, base_url, resource_type):
    resources = []
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

def create_terraform_config(api_key, base_url, org_name, provider_version):
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

def create_terraform_import_script(data, resource_type):
    output_file = f"terraform_import_{resource_type}.tf"
    with open(output_file, 'w') as file:
        for item in data:
            if resource_type == 'groups':
                name = item['profile']['name']
                id = item['id']
                resource_address = f"okta_group.{sanitize_name(name)}"
            elif resource_type == 'users':
                name = f"{item['profile']['firstName']}_{item['profile']['lastName']}"
                id = item['id']
                resource_address = f"okta_user.{sanitize_name(name)}"
            
            import_block = f"""
resource "{resource_type.rstrip('s')}" "{sanitize_name(name)}" {{
  # Define your resource attributes here
}}

import {{
  to = {resource_address}
  id = "{id}"
}}

"""
            file.write(import_block)
            print(f"Added import block for {name} (ID: {id})")
    
    print(f"\nTerraform import script created: {output_file}")

def sanitize_name(name):
    return re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_').lower())

def main():
    latest_version = get_latest_okta_provider_version()
    print(f"Latest Okta provider version: {latest_version}")

    api_key = getpass.getpass("Enter your Okta API key: ")
    base_url = input("Enter your Okta Base URL: (default: okta.com) ") or "okta.com"
    org_name = input("Enter your Okta Org Name: ")
    provider_version = input(f"Enter Okta provider version (default: {latest_version}): ") or latest_version

    check_provider_availability(provider_version, latest_version)

    create_terraform_config(api_key, base_url, org_name, provider_version)
    print("\nTerraform configuration created successfully!")
    check_terraform_init()

    for resource_type in ['users', 'groups']:
        if input(f"\nWould you like to import all {resource_type} from Okta? (y/n) ").lower() == "y":
            resources = get_okta_resources(org_name, api_key, base_url, resource_type)
            print(f"Total {resource_type} retrieved: {len(resources)}")
            
            if resources:
                if input(f"\nWould you save the imported {resource_type} to a file? (y/n) ").lower() == "y":
                    with open(f'okta_{resource_type}.json', 'w') as f:
                        json.dump(resources, f, indent=2)
                
                if input(f"\nWould you like to create the imported {resource_type} into Terraform? (y/n) ").lower() == 'y':
                    create_terraform_import_script(resources, resource_type)
            else:
                print(f"No {resource_type} found in the Okta organization.")

    if input("\nWould you like to clean up temporary files? (y/n) ").lower() == "y":
        print("\nCleaning up temporary files...")   
        clean_up()

    print("\nDone!")

if __name__ == "__main__":
    main()
