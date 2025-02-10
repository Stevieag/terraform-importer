import importlib
import os
import subprocess

def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    """Main entry point for the resource import tool."""
    print("PLEASE ENSURE YOU HAVE RUN THE REQUIREMENTS FILE: `pip install -r requirements.txt`")
    input("Press Enter to continue...")  
    clear_screen()

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
            print("Initialising Terraform...")
            init_result = subprocess.run(["terraform", "init"], capture_output=True, text=True, check=True)
            print(init_result.stdout)
            print("Terraform initialised successfully.")

            print("Generating Terraform plan file...")
            plan_result = subprocess.run(
                ["terraform", "plan", "-generate-config-out=terraform-importer-created.tf"],
                capture_output=True,
                text=True,
                check=True
            )
            print(plan_result.stdout)
            print("Terraform plan file created (terraform-importer-created.tf).  Review this file carefully before applying!")
        except subprocess.CalledProcessError as e:
            print(f"Error during Terraform plan generation: {e.stderr}")

            with open("terraform_plan_error.log", "w") as log_file:
                log_file.write(e.stderr)
            print("Detailed error information has been logged to terraform_plan_error.log")
        except FileNotFoundError:
            print("Error: Terraform is not installed or not in your PATH.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
