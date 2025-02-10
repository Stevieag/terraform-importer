from google.cloud import compute, storage, iam_admin
from google.api_core import exceptions
import terraform_utils
from terraform_utils import get_latest_provider_version, create_provider_block, create_terraform_config, create_terraform_import_script
import json

def get_gcp_compute_instances(project_id, zone):
    """Retrieves a list of Compute Engine instances for a project and zone."""
    from google.cloud import compute_v1

    client = compute_v1.InstancesClient()
    request = compute_v1.ListInstancesRequest(
        project=project_id,
        zone=zone,
    )

    resources = []
    try:
        page_result = client.list(request=request)
        for response in page_result:
            for instance in response.items:
                resources.append(instance)
    except exceptions.Forbidden as e: 
        print(f"Error: Insufficient permissions to list Compute Engine instances: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []
    return resources


def get_gcp_groups(project_id: str) -> list:
    client = iam_admin.GroupsClient()
    groups = []
    request = iam_admin.ListGroupsRequest(parent=f"projects/{project_id}")
    page_result = client.list_groups(request=request)
    for group in page_result:
        groups.append(group)
    return groups

def get_gcp_users(project_id: str) -> list:
    client = iam_admin.IAMClient()
    users = []
    request = iam_admin.ListServiceAccountsRequest(parent=f"projects/{project_id}")
    page_result = client.list_service_accounts(request=request)
    for user in page_result:
        users.append(user)
    return users

def get_gcp_custom_roles(project_id: str) -> list:
    client = iam_admin.IAMClient()
    roles = []
    request = iam_admin.ListRolesRequest(parent=f"projects/{project_id}")
    page_result = client.list_roles(request=request)
    for role in page_result:
        if role.is_custom:
            roles.append(role)
    return roles

def get_gcp_buckets(project_id: str) -> list:
    client = storage.Client(project=project_id)
    buckets = list(client.list_buckets())
    return buckets

def choose_resource_type(project_id, zone):
    resource_types = {
        "1": ("Compute Instance", get_gcp_compute_instances),
        "2": ("Storage Buckets", get_gcp_buckets),
        #"3": ("Group", get_gcp_groups),
        #"4": ("Users", get_gcp_users),
        #"5": ("Custom Roles", get_gcp_custom_roles)
    }
    
    while True:
        print("\nSelect a resource type to import:")
        for key, value in resource_types.items(): 
            print(f"{key}. {value[0]}")
        print("0. Exit")
    
        choice = input("Enter your choice: ")
        
        if choice not in resource_types:
            print("Invalid choice. Exiting.")
            return
        print(f"Selected {resource_types[choice][0]}")
        resource_type, get_function = resource_types[choice]
        
        if resource_type == "Compute Instance":
            resources = get_function(project_id, zone)
        else:
            resources = get_function(project_id)
        
        print(f"Found {len(resources)} {resource_type} resources.")
    

def gcp():
    latest_version = get_latest_provider_version("google")
    project_id = input("Enter your GCP Project ID: ")
    zone = input("Enter the GCP Zone (default: europe-west2-a): ") or "europe-west2-a"
    creds_file = input("Enter the path to or drag and drop your JSON credentials file: ")
    try:
        with open(creds_file, 'r') as f:
            creds = f.read()
    except FileNotFoundError:
        print("Error: Credentials file not found.")
        return 

    terraform_utils.create_provider_block(
        provider="gcp",
        project_id=project_id,
        zone=zone,
        creds=creds,
    )

    print("\nTerraform configuration created successfully!")
    
    choose_resource_type(project_id, zone)

    if input(f"\nWould you like to save the imported {resource_type} to a file? (y/n) ").lower() == "y":
        with open(f'gcp_{resource_type}.json', 'w') as f:
            json.dump([resource.to_dict() for resource in resources], f, indent=2)

    if input(f"\nWould you like to create the import file for {resource_type}? (y/n) ").lower() == "y":
        create_terraform_import_script(resources, resource_type)

def main():
    gcp()

if __name__ == "__main__":
    main()
