from flask_cors import CORS
from flask import Flask, request, jsonify, send_file
import os
import tempfile
from datetime import datetime
import pandas as pd
from io import StringIO, BytesIO
from login import generate_oauth_url, arcgis_login
from generate_coords import generate_coords
from arcgis.features import FeatureLayerCollection
from prepare_data import prepare_data
from update_layer import process_update_layer

app = Flask(__name__)
CORS(app)
# Global GIS object after successful OAuth login
gis = None

@app.route('/start-login', methods=['POST'])
def start_login():
    data = request.get_json()
    client_id = data.get('client_id')
    if not client_id:
        return jsonify({"status": "failure", "message": "client_id missing"}), 400
    oauth_url = generate_oauth_url(client_id)
    return jsonify({"status": "success", "oauth_url": oauth_url})

@app.route('/complete-login', methods=['POST'])
def complete_login():
    global gis
    data = request.get_json()
    client_id = data.get('client_id')
    code = data.get('code')
    if not client_id or not code:
        return jsonify({"status": "failure", "message": "client_id or code missing"}), 400
    gis = arcgis_login(client_id, code)
    if gis:
        user = gis.users.me
        return jsonify({
            "status": "success",
            "username": user.username,
            "full_name": user.fullName,
            "message": f"Logged in as {user.fullName} ({user.username})"
        })
    else:
        return jsonify({"status": "failure", "message": "Login failed"}), 400

@app.route('/geocode', methods=['POST'])
def geocode_endpoint():
    global gis
    if not gis:
        return jsonify({"status": "failure", "message": "Not logged in"}), 400

    # Ensure file and form fields exist
    if 'csv' not in request.files:
        return jsonify({"status": "failure", "message": "No CSV file uploaded"}), 400
    csv_file = request.files['csv']
    address_col = request.form.get('address_col')
    city_col = request.form.get('city_col')
    if not address_col or not city_col:
        return jsonify({"status": "failure", "message": "address_col or city_col missing"}), 400

    # Read CSV into DataFrame
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        return jsonify({"status": "failure", "message": f"Error parsing CSV: {e}"}), 400

    # Geocode logic
    from arcgis.geocoding import geocode
    import re
    def match_addr(row):
        street = str(row.get(address_col, "")).strip()
        city_info = str(row.get(city_col, "")).strip()
        zip_match = re.search(r"\b\d{5}\b", city_info)
        if zip_match:
            zipcode = zip_match.group(0)
            city = re.sub(r"\b\d{5}\b", "", city_info).strip(", ")
        else:
            zipcode = ""
            city = city_info
        full = f"{street}, {city}, CA {zipcode}, USA".replace(" ,", ",").strip()
        try:
            res = geocode(address=full, max_locations=1, source_country='USA', as_featureset=False)
            return res[0]['attributes'].get('Match_addr', "Not Found") if res else "Not Found"
        except:
            return "Error"

    df['Geocoded_Address'] = df.apply(match_addr, axis=1)

    # Prepare CSV for download via BytesIO
    csv_text = df.to_csv(index=False)
    buf = BytesIO(csv_text.encode('utf-8'))
    buf.seek(0)
    return send_file(
        buf,
        mimetype='text/csv',
        as_attachment=True,
        download_name='geocoded.csv'
    )

@app.route('/generate-coords', methods=['POST'])
def generate_coords_endpoint():
    global gis
    if not gis:
        return jsonify({"status": "failure", "message": "Not logged in"}), 400

    # 1) Grab the uploaded file
    if 'input_csv' not in request.files:
        return jsonify({"status": "failure", "message": "No CSV file uploaded"}), 400
    csv_file = request.files['input_csv']

    # 2) Read into DataFrame
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        return jsonify({"status": "failure", "message": f"Error parsing CSV: {e}"}), 400

    # 3) Ensure geocode column exists
    if 'Geocoded_Address' not in df.columns:
        return jsonify({"status": "failure", "message": "'Geocoded_Address' column missing"}), 400

    # 4) Generate X/Y from that address
    from arcgis.geocoding import geocode as arc_geocode
    x_coords, y_coords = [], []
    for addr in df['Geocoded_Address']:
        if not addr or addr in ("Not Found",) or addr.startswith("Error"):
            x_coords.append(None); y_coords.append(None)
        else:
            try:
                results = arc_geocode(address=addr, max_locations=1, source_country='USA', as_featureset=False)
                loc = results[0].get('location') if results else None
                x_coords.append(loc.get('x') if loc else None)
                y_coords.append(loc.get('y') if loc else None)
            except:
                x_coords.append(None); y_coords.append(None)
    df['X'], df['Y'] = x_coords, y_coords

    # 5) Stream it back as a CSV download
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    buf = BytesIO(csv_bytes)
    buf.seek(0)
    return send_file(
        buf,
        mimetype='text/csv',
        as_attachment=True,
        download_name='generated_coords.csv'
    )

@app.route('/prepare-data', methods=['POST'])
def prepare_data_endpoint():
    global gis
    if not gis:
        return jsonify({"status": "failure", "message": "Not logged in"}), 400

    if 'csv_prepare' not in request.files:
        return jsonify({"status": "failure", "message": "No CSV uploaded"}), 400

    try:
        buf = prepare_data(request.files['csv_prepare'])
        return send_file(
            buf,
            mimetype='text/csv',
            as_attachment=True,
            download_name='prepared.csv'
        )
    except Exception as e:
        return jsonify({"status": "failure", "message": str(e)}), 500

@app.route('/update-layer', methods=['POST'])
def update_layer_endpoint():
    global gis
    if not gis:
        return jsonify({"status": "failure", "message": "Not logged in"}), 400

    if 'csv_update' not in request.files:
        return jsonify({"status": "failure", "message": "No CSV uploaded"}), 400

    try:
        result = process_update_layer(
            gis,
            request.files['csv_update'],
            layer_item_id="c90b4cde46fd40eab2d8f95b264183bd",
            csv_item_id="aba88057a34c4d448df443ff21fa7121"
        )
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        return jsonify({"status": "failure", "message": str(e)}), 500
    
if __name__ == "__main__":
    app.run(debug=True)
