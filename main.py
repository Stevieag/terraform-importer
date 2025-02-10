import importlib
import os

def main():
    """Main entry point for the resource import tool."""
    services = {'1': 'okta', '2': 'gcp'}

    while True:
        print("\nChoose a service to import resources from:")
        for key, service in services.items():
            print(f"{key}. {service.capitalize()}")
        print("0. Exit")

        choice = input("Enter the number of the service to import (or 0 to exit): ")

        if choice == '0':
            print("Exiting resource import tool.")
            break
        elif choice in services:
            service_name = services[choice]
            try:
                handler_module = importlib.import_module(f"{service_name}_handler")
                handler_module.main()
            except ImportError:
                print(f"Error: Could not find or load {service_name}_handler.py")
            except AttributeError:
                print(f"Error: {service_name}_handler.py does not have a 'main' function.")
        else:
            print("Invalid choice. Please select a number from the list.")

    if input("\nWould you like to create a Terraform plan file for all the resources found? (y/n) ").lower() == 'y':
        try:
            import subprocess 
            result = subprocess.run(["terraform", "plan", "-generate-config-out=terraform-importer-created.tf"], capture_output=True, text=True, check=True)
            print(result.stdout)
            print("Terraform plan file created (terraform-importer-created.tf).  Review this file carefully before applying!")
        except subprocess.CalledProcessError as e:
            print(f"Error during Terraform plan generation: {e.stderr}")
        except FileNotFoundError:
            print("Error: Terraform is not installed or not in your PATH.")

if __name__ == "__main__":
    main()
