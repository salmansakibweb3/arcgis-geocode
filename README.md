# Custom Address Geocoding and Coordinate Generation Tool

This project provides a modular Python solution to:
- **Authenticate** with ArcGIS Enterprise using OAuth.
- **Geocode addresses** from a CSV file.
- **Generate XY coordinates** (latitude and longitude) from the geocoded addresses.

The workflow is interactive and prompts the user for all necessary inputs, including the ArcGIS Client ID, CSV file path, and the names of the address columns.

## Project Structure

├── input/ 
│ └── <your_input_file.csv> # Place your CSV input files here. 
├── output/ 
│ ├── output_with_addresses.csv # Geocoded CSV output. 
│ └── output_with_coords.csv # CSV output with XY coordinates. 
├── login.py # Handles ArcGIS Enterprise OAuth login. 
├── geocode.py # Reads the input CSV, geocodes addresses, and saves output. 
├── generate_coords.py # Reads the geocoded CSV and generates XY coordinate columns. 
├── main.py # Orchestrates the entire workflow. 
└── requirements.txt # List of required Python packages.


## Prerequisites

- Python 3.6 or higher.
- An ArcGIS Enterprise account and a registered OAuth app.
- Ensure your OAuth app has the correct allowed redirect URI (e.g., `http://localhost:8080` for local server authentication).

## Installation

1. **Clone the repository:**

   ```bash
   git clone <your-repo-url>
   cd <your-repo-folder>

## (Optional) Create and activate a virtual environment:

```bash
    python -m venv venv
    source venv/bin/activate   # On Windows: venv\Scripts\activate
```

## Install dependencies:
The project automatically installs dependencies when you run main.py. Alternatively, run:

```bash
pip install -r requirements.txt
```

# Usage
Prepare your CSV file:

Place your CSV file in the input folder.

Ensure it contains at least two columns:

One column with street addresses (e.g., Address).

One column with city information (e.g., City).
Note: The City column may sometimes include a ZIP code.

Run the project:

bash
Copy
python main.py
Follow the prompts:

Enter your ArcGIS Client ID.

Log in via the browser when prompted.

Confirm if you want to proceed with geocoding.

Provide the path to your CSV file (for example, ./input/your_file.csv).

Enter the column names for addresses and cities.

Confirm to generate coordinates (XY) from the geocoded addresses.

Output:

The geocoded addresses will be saved to ./output/output_with_addresses.csv.

The final CSV file with XY coordinates will be saved to ./output/output_with_coords.csv.

Modules Overview
login.py:
Handles the OAuth login with ArcGIS Enterprise using a local server flow. The browser is automatically used for authentication.

geocode.py:
Reads the input CSV, combines the address and city (parsing out ZIP code if available), and geocodes the resulting address. The geocoded address is then saved to a new CSV.

generate_coords.py:
Reads the CSV produced by geocode.py and uses the geocoded address to generate X (longitude) and Y (latitude) coordinates. These columns are added to the CSV output.

main.py:
Orchestrates the workflow by:

Installing dependencies if needed.

Logging into ArcGIS Enterprise.

Prompting the user for necessary input details.

Running the geocoding and coordinate generation steps.

Contributing
Feel free to fork the repository, make changes, and submit pull requests. For any issues or suggestions, please open an issue.

License
This project is licensed under the MIT License.

pgsql
Copy

This README should be ready to add to your repository. Simply copy and paste it into a file named