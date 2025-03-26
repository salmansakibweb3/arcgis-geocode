import subprocess
import sys

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

    # 3) Prompt for client ID
    client_id = input("Enter your ArcGIS Client ID: ").strip()

    # 4) Login
    gis = arcgis_login(client_id)
    if not gis:
        print("Exiting due to failed login.")
        return

    # 5) Ask user to proceed with geocoding step
    proceed = input("Proceed to geocoding step? (y/n): ").strip().lower()
    if proceed != 'y':
        print("🛑 Operation cancelled by user.")
        return

    # 6) Geocode
    csv_path = input("Enter the path to your CSV file (e.g. input.csv): ").strip()
    address_col = input("Enter the name of the column with addresses (e.g. 'Address'): ").strip()
    city_col = input("Enter the name of the column with city information (e.g. 'City'): ").strip()
    geocode_csv(gis, csv_path, address_col, city_col, "./output/output_with_addresses.csv")

    # 7) Ask user to proceed with generating coordinates
    proceed_coords = input("Proceed to generate coordinates (XY) from geocoded addresses? (y/n): ").strip().lower()
    if proceed_coords != 'y':
        print("🛑 Operation cancelled by user.")
        return

    generate_coords("./output/output_with_addresses.csv", "./output/output_with_coords.csv")

if __name__ == "__main__":
    main()
