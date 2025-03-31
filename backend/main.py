import subprocess
import sys
import os

def install_requirements():
    """
    Installs all dependencies listed in requirements.txt
    if they are not already installed.
    """
    try:
        import arcgis
        import pandas
    except ImportError:
        print("Dependencies missing. Installing from requirements.txt...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])

def main():
    # 1) Install/verify dependencies
    install_requirements()

    # 2) Import modules *after* installing dependencies
    from login import arcgis_login
    from geocode import geocode_csv
    from generate_coords import generate_coords

    # 3) Create input and output directories if they don't exist, with console messages
    input_dir = "input"
    output_dir = "output"
    if not os.path.exists(input_dir):
        print(f"Creating '{input_dir}' folder...")
        os.makedirs(input_dir)
    else:
        print(f"'{input_dir}' folder already exists.")
        
    if not os.path.exists(output_dir):
        print(f"Creating '{output_dir}' folder...")
        os.makedirs(output_dir)
    else:
        print(f"'{output_dir}' folder already exists.")

    print("\nPlease ensure you place your CSV input file in the 'input' folder.\n")

    # 4) Prompt for client ID
    client_id = input("Enter your ArcGIS Client ID: ").strip()

    # 5) Login
    gis = arcgis_login(client_id)
    if not gis:
        print("Exiting due to failed login.")
        return

    # 6) Ask user to proceed with geocoding step
    proceed = input("Proceed to geocoding step? (y/n): ").strip().lower()
    if proceed != 'y':
        print("🛑 Operation cancelled by user.")
        return

    # 7) Prompt for input file name (assumed to be located in the "input" folder)
    input_file = input("Enter the name of your CSV file in the 'input' folder (e.g. 'your_file.csv'): ").strip()
    csv_path = os.path.join(input_dir, input_file)
    if not os.path.exists(csv_path):
        print(f"❌ File '{csv_path}' not found. Please copy your CSV file into the '{input_dir}' folder and try again.")
        return
    
    address_col = input("Enter the name of the column with addresses (e.g. 'Address'): ").strip()
    city_col = input("Enter the name of the column with city information (e.g. 'City'): ").strip()
    
    addresses_output = os.path.join(output_dir, "output_with_addresses.csv")
    geocode_csv(gis, csv_path, address_col, city_col, addresses_output)
    
    # 8) Ask user to proceed with generating coordinates
    proceed_coords = input("Proceed to generate coordinates (XY) from geocoded addresses? (y/n): ").strip().lower()
    if proceed_coords != 'y':
        print("🛑 Operation cancelled by user.")
        return

    coords_output = os.path.join(output_dir, "output_with_coords.csv")
    generate_coords(addresses_output, coords_output)

if __name__ == "__main__":
    main()
