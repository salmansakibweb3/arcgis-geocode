import re
import pandas as pd
from arcgis.geocoding import geocode

def geocode_csv(gis, csv_path: str, address_col: str, city_col: str,
                output_path: str = "output_with_addresses.csv"):
    """
    Reads a CSV file, parses the address and city columns, builds a full address string,
    geocodes it, and writes the output to a new CSV file.

    Parameters:
        gis: Authenticated GIS object.
        csv_path: Path to the input CSV.
        address_col: Name of the column with street addresses.
        city_col: Name of the column with city information (may include ZIP code).
        output_path: File path for saving the output CSV.
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Ensure the required columns exist
    for col in [address_col, city_col]:
        if col not in df.columns:
            print(f"❌ Column '{col}' not found in CSV.")
            return

    def get_geocoded_address(row):
        # Get the street address from the specified address column
        street = str(row.get(address_col, "")).strip()
        
        # Get the city info and attempt to extract a 5-digit ZIP code using regex
        city_info = str(row.get(city_col, "")).strip()
        zip_match = re.search(r'\b\d{5}\b', city_info)
        if zip_match:
            zipcode = zip_match.group(0)
            # Remove the ZIP code from the city string for clarity
            city = re.sub(r'\b\d{5}\b', '', city_info).strip(", ").strip()
        else:
            zipcode = ""
            city = city_info

        # Build a full address string, explicitly including CA and USA.
        # If your data isn't all in California, adjust accordingly.
        full_address = f"{street}, {city}, CA {zipcode}, USA".replace(" ,", ",").strip()
        
        try:
            # Removed sourceCountry='USA' to avoid errors on older arcgis versions
            results = geocode(address=full_address, max_locations=1, source_country='USA', as_featureset=False)
            if results and results[0]['attributes'].get('Match_addr'):
                return results[0]['attributes']['Match_addr']
            else:
                return "Not Found"
        except Exception as e:
            return f"Error: {e}"

    print("Geocoding addresses...")
    df['Geocoded_Address'] = df.apply(get_geocoded_address, axis=1)

    try:
        df.to_csv(output_path, index=False)
        print(f"✅ Done! Geocoded addresses saved to '{output_path}'")
    except Exception as e:
        print(f"Error saving output CSV: {e}")

if __name__ == "__main__":
    # For testing purposes only:
    from arcgis.gis import GIS
    client_id = "YOUR_CLIENT_ID"
    gis = GIS("https://cmad.maps.arcgis.com", client_id=client_id, authorize=True)
    csv_file = "input.csv"
    address_column = "Address"
    city_column = "City"
    geocode_csv(gis, csv_file, address_column, city_column, "output_with_addresses.csv")