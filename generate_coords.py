import pandas as pd
from arcgis.geocoding import geocode

def generate_coords(input_csv: str, output_csv: str = "output_with_coords.csv"):
    """
    Reads a CSV file with a 'Geocoded_Address' column and, for each row,
    retrieves the coordinates (X, Y) from the geocoding service.
    Writes the updated data with 'X' and 'Y' columns to a new CSV file.
    """
    try:
        df = pd.read_csv(input_csv)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    if 'Geocoded_Address' not in df.columns:
        print("❌ 'Geocoded_Address' column not found in the input CSV.")
        return

    x_coords = []
    y_coords = []

    print("Generating coordinates for each geocoded address...")
    for index, row in df.iterrows():
        address = row['Geocoded_Address']
        if not address or address == "Not Found" or "Error:" in address:
            x_coords.append(None)
            y_coords.append(None)
        else:
            try:
                results = geocode(address=address, max_locations=1)
                if results and results[0].get('location'):
                    loc = results[0]['location']
                    x_coords.append(loc.get('x'))
                    y_coords.append(loc.get('y'))
                else:
                    x_coords.append(None)
                    y_coords.append(None)
            except Exception as e:
                x_coords.append(None)
                y_coords.append(None)
                print(f"Error geocoding '{address}': {e}")
    df['X'] = x_coords
    df['Y'] = y_coords

    try:
        df.to_csv(output_csv, index=False)
        print(f"✅ Coordinates generated and saved to '{output_csv}'")
    except Exception as e:
        print(f"Error saving output CSV: {e}")

if __name__ == "__main__":
    input_csv = "./output/output_with_addresses.csv"
    output_csv = "./output/output_with_coords.csv"
    generate_coords(input_csv, output_csv)