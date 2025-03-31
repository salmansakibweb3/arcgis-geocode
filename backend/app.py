# backend/app.py
from flask import Flask, request, jsonify
import os
from login import generate_oauth_url, arcgis_login
from geocode import geocode_csv
from generate_coords import generate_coords

app = Flask(__name__)

# Global variable to store the GIS object after login
gis = None

@app.route('/start-login', methods=['POST'])
def start_login():
    data = request.get_json()
    client_id = data.get('client_id')
    if not client_id:
        return jsonify({"status": "failure", "message": "client_id missing"}), 400
    oauth_url = generate_oauth_url(client_id)
    print("Generated OAuth URL:", oauth_url)  # Debug: Check the URL here
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
        return jsonify({"status": "success", "message": f"Logged in as {gis.users.me.username}"})
    else:
        return jsonify({"status": "failure", "message": "Login failed"}), 400

@app.route('/geocode', methods=['POST'])
def geocode_endpoint():
    if not gis:
        return jsonify({"status": "failure", "message": "Not logged in"}), 400
    data = request.get_json()
    csvPath = data.get('csvPath')
    address_col = data.get('address_col')
    city_col = data.get('city_col')
    output_path = "backend/output/output_with_addresses.csv"
    try:
        geocode_csv(gis, csvPath, address_col, city_col, output_path)
        return jsonify({"status": "success", "message": f"Geocoded addresses saved to {output_path}"})
    except Exception as e:
        return jsonify({"status": "failure", "message": str(e)}), 500

@app.route('/generate-coords', methods=['POST'])
def generate_coords_endpoint():
    data = request.get_json()
    input_csv = data.get('input_csv')
    output_csv = "backend/output/output_with_coords.csv"
    try:
        generate_coords(input_csv, output_csv)
        return jsonify({"status": "success", "message": f"Coordinates generated and saved to {output_csv}"})
    except Exception as e:
        return jsonify({"status": "failure", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
