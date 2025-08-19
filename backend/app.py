from flask_cors import CORS
from flask import Flask, request, jsonify, send_file
import os
import tempfile
from datetime import datetime
import pandas as pd
from io import StringIO, BytesIO
from login import generate_oauth_url, arcgis_login
from generate_coords import generate_coords
from arcgis.features import FeatureLayerCollection, FeatureLayer
from prepare_data import prepare_data
from update_layer import process_update_layer
from generate_spray_notifications import generate_spray_notifications

app = Flask(__name__)
CORS(app)
# Global GIS object after successful OAuth login
gis = None

def get_layer_info(gis, layer_id):
    """
    Retrieve layer information from AGOL using layer ID
    
    Args:
        gis: Authenticated ArcGIS GIS object
        layer_id: The layer ID to get information for
        
    Returns:
        dict: Layer information including title, type, owner, etc.
    """
    try:
        item = gis.content.get(layer_id)
        if not item:
            return {"error": f"Layer {layer_id} not found"}
            
        info = {
            "id": layer_id,
            "title": item.title,
            "type": item.type,
            "owner": item.owner,
            "created": str(item.created) if item.created else None,
            "modified": str(item.modified) if item.modified else None,
            "snippet": item.snippet,
            "description": item.description,
            "tags": item.tags if hasattr(item, 'tags') else [],
        }
        
        # Additional info for feature services/layers
        if hasattr(item, 'url'):
            info["url"] = item.url
            
        return info
        
    except Exception as e:
        return {"error": f"Failed to get info for layer {layer_id}: {str(e)}"}

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

    # Get layer type from form data
    layer_type = request.form.get('layer_type', 'surveillance')  # default to surveillance
    
    # Define layer configurations
    LAYER_CONFIGS = {
        'surveillance': {
            'layer_item_id': "c90b4cde46fd40eab2d8f95b264183bd",
            'csv_item_id': "aba88057a34c4d448df443ff21fa7121",
            'name': "Collection 2025"
        },
        'disease': {
            'layer_item_id': "d2a9cfa0aa4e4b0e8a2c30da319957fe",  # Replace with actual disease layer ID
            'csv_item_id': "d26c1a0e2b5c4a0883d3d4aaa412dd07",      # Replace with actual disease CSV ID
            'name': "Pools 2025"  # Update this with your actual disease layer name
        }
    }
    
    if layer_type not in LAYER_CONFIGS:
        return jsonify({"status": "failure", "message": f"Invalid layer_type: {layer_type}"}), 400
    
    config = LAYER_CONFIGS[layer_type]

    try:
        result = process_update_layer(
            gis,
            request.files['csv_update'],
            layer_item_id=config['layer_item_id'],
            csv_item_id=config['csv_item_id']
        )
        result['layer_name'] = config['name']
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        return jsonify({"status": "failure", "message": str(e)}), 500

@app.route('/get-layer-info', methods=['POST'])
def get_layer_info_endpoint():
    """Get detailed information about an AGOL layer by ID"""
    global gis
    if not gis:
        return jsonify({"status": "failure", "message": "Not logged in"}), 400

    try:
        data = request.get_json()
        layer_id = data.get('layer_id')
        
        if not layer_id:
            return jsonify({"status": "failure", "message": "layer_id is required"}), 400
            
        layer_info = get_layer_info(gis, layer_id)
        
        if "error" in layer_info:
            return jsonify({"status": "failure", "message": layer_info["error"]}), 400
            
        return jsonify({
            "status": "success",
            "layer_info": layer_info
        })
        
    except Exception as e:
        return jsonify({"status": "failure", "message": f"Error retrieving layer info: {str(e)}"}), 500

@app.route('/test-spray-layers', methods=['POST'])
def test_spray_layers_endpoint():
    """Test endpoint to verify AGOL layer access before spray notifications generation"""
    global gis
    if not gis:
        return jsonify({"status": "failure", "message": "Not logged in"}), 400

    try:
        # Layer IDs
        SUBGRID_LAYER_ID = "e8656893998e497fa8161f87d053a725"
        RESIDENT_NOTICES_LAYER_ID = "cd84fc9ddca2406f85c185a5841be65b"  # Hosted feature layer: Resident_Notices_2025
        # RESIDENT_NOTICES_SUBLAYER = 31  # Not needed for hosted feature layer

        result = {
            "status": "success",
            "tests": {}
        }

        # Test 1: Access Subgrid Layer
        try:
            print(f"[test] Accessing subgrid layer: {SUBGRID_LAYER_ID}")
            subgrid_item = gis.content.get(SUBGRID_LAYER_ID)
            if not subgrid_item:
                raise RuntimeError("Item not found")
            
            subgrid_layer = FeatureLayerCollection.fromitem(subgrid_item).layers[0]
            
            # Get basic info
            subgrid_count = subgrid_layer.query(return_count_only=True)
            sample_features = subgrid_layer.query(where="1=1", return_geometry=False, result_record_count=3)
            
            # Check for GridLabel field
            fields = [f['name'] for f in subgrid_layer.properties.fields]
            has_gridlabel = 'GridLabel' in fields
            
            result["tests"]["subgrid_layer"] = {
                "accessible": True,
                "title": subgrid_item.title,
                "feature_count": subgrid_count,
                "fields": fields,
                "has_gridlabel": has_gridlabel,
                "sample_gridlabels": [f.attributes.get('GridLabel') for f in sample_features.features[:3]]
            }
            
        except Exception as e:
            result["tests"]["subgrid_layer"] = {
                "accessible": False,
                "error": str(e)
            }

        # Test 2: Access Resident Notices Layer (standalone shapefile)
        try:
            print(f"[test] Accessing resident notices layer: {RESIDENT_NOTICES_LAYER_ID}")
            resident_item = gis.content.get(RESIDENT_NOTICES_LAYER_ID)
            if not resident_item:
                raise RuntimeError("Item not found")
            
            # Access standalone shapefile layer directly
            resident_layer = FeatureLayer.fromitem(resident_item)
            
            # Get basic info
            resident_count = resident_layer.query(return_count_only=True)
            sample_features = resident_layer.query(where="1=1", return_geometry=False, result_record_count=3)
            
            # Check fields
            fields = [f['name'] for f in resident_layer.properties.fields]
            
            result["tests"]["resident_notices_layer"] = {
                "accessible": True,
                "title": resident_item.title,
                "layer_type": "standalone_shapefile",
                "feature_count": resident_count,
                "fields": fields,
                "sample_records": len(sample_features.features)
            }
            
        except Exception as e:
            result["tests"]["resident_notices_layer"] = {
                "accessible": False,
                "error": str(e)
            }

        # Test 3: Try a simple GridLabel query
        if result["tests"]["subgrid_layer"].get("accessible") and result["tests"]["subgrid_layer"].get("has_gridlabel"):
            try:
                # Get a sample GridLabel and try querying it
                sample_gridlabel = result["tests"]["subgrid_layer"]["sample_gridlabels"][0]
                if sample_gridlabel:
                    test_query = subgrid_layer.query(where=f"GridLabel = '{sample_gridlabel}'", return_geometry=True)
                    result["tests"]["gridlabel_query"] = {
                        "success": True,
                        "test_gridlabel": sample_gridlabel,
                        "features_found": len(test_query.features),
                        "has_geometry": len(test_query.features) > 0 and test_query.features[0].geometry is not None
                    }
                else:
                    result["tests"]["gridlabel_query"] = {
                        "success": False,
                        "error": "No sample GridLabel found"
                    }
            except Exception as e:
                result["tests"]["gridlabel_query"] = {
                    "success": False,
                    "error": str(e)
                }

        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "status": "failure", 
            "message": f"Test failed: {str(e)}"
        }), 500

@app.route('/generate-spray-notifications', methods=['POST'])
def generate_spray_notifications_endpoint():
    global gis
    if not gis:
        return jsonify({"status": "failure", "message": "Not logged in"}), 400

    try:
        data = request.get_json()
        selected_subgrids = data.get('selected_subgrids', [])
        buffer_distance = data.get('buffer_distance', 300)
        
        if not selected_subgrids:
            return jsonify({"status": "failure", "message": "No subgrids selected"}), 400
        
        # Validate GridLabel format (e.g., "172024-1", "122136-1")
        import re
        gridlabel_pattern = re.compile(r'^\d+-\d+$')
        
        invalid_labels = [sg for sg in selected_subgrids if not gridlabel_pattern.match(str(sg).strip())]
        if invalid_labels:
            return jsonify({
                "status": "failure", 
                "message": f"Invalid GridLabel format: {invalid_labels}. Expected format: 'TRS-Quadrant' (e.g., '172024-1')"
            }), 400
        
        # Clean up the subgrid labels
        subgrid_labels = [str(sg).strip() for sg in selected_subgrids]
        
        # Validate buffer distance
        try:
            buffer_dist = float(buffer_distance)
            if buffer_dist <= 0:
                raise ValueError("Buffer distance must be positive")
        except (ValueError, TypeError):
            return jsonify({"status": "failure", "message": "Invalid buffer distance"}), 400
        
        # Generate spray notifications
        result = generate_spray_notifications(
            gis,
            subgrid_labels,
            buffer_dist
        )
        
        # Return the CSV file for download
        return send_file(
            result['csv_buffer'],
            mimetype='text/csv',
            as_attachment=True,
            download_name=result['filename']
        )
        
    except Exception as e:
        return jsonify({"status": "failure", "message": str(e)}), 500

@app.route('/analyze-disease-positives', methods=['POST'])
def analyze_disease_positives_endpoint():
    """
    Analyze disease positive samples from pools layer within a date range
    This is Step 1 of the Disease Map Generation workflow
    """
    global gis
    if not gis:
        return jsonify({"status": "failure", "message": "Not logged in"}), 400

    try:
        data = request.get_json()
        # Hardcoded Pools layer ID
        pools_layer_id = "d2a9cfa0aa4e4b0e8a2c30da319957fe"
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({"status": "failure", "message": "Both start_date and end_date are required"}), 400
        
        from datetime import datetime
        from arcgis.features import FeatureLayerCollection, FeatureLayer
        
        # Log the request
        print(f"[disease_analysis] Starting analysis for layer {pools_layer_id}")
        print(f"[disease_analysis] Date range: {start_date} to {end_date}")
        
        # Access the pools layer
        try:
            pools_item = gis.content.get(pools_layer_id)
            if not pools_item:
                return jsonify({"status": "failure", "message": f"Layer {pools_layer_id} not found"}), 400
                
            # Try to get the layer - could be standalone or part of a service
            if pools_item.type == "Feature Service":
                pools_layer = FeatureLayerCollection.fromitem(pools_item).layers[0]
            else:
                # Standalone shapefile/feature layer
                pools_layer = FeatureLayer.fromitem(pools_item)
                
            print(f"[disease_analysis] Successfully accessed layer: {pools_item.title}")
            
        except Exception as layer_error:
            print(f"[disease_analysis] Error accessing layer: {layer_error}")
            return jsonify({"status": "failure", "message": f"Error accessing layer: {str(layer_error)}"}), 400
        
        # Get layer info and fields for console logging
        layer_properties = pools_layer.properties
        field_names = [f['name'] for f in layer_properties.fields] if hasattr(layer_properties, 'fields') else []
        
        print(f"[disease_analysis] Layer fields: {field_names}")
        
        # Log field types and details
        if hasattr(layer_properties, 'fields'):
            for field in layer_properties.fields:
                print(f"[disease_analysis] Field: {field['name']} | Type: {field['type']} | Alias: {field.get('alias', 'N/A')}")
        
        # Get total feature count
        total_count = pools_layer.query(return_count_only=True)
        print(f"[disease_analysis] Total features in layer: {total_count}")
        
        # Construct the WHERE clause for date filtering
        # We'll try common date field patterns and let the user know what we find
        date_field_candidates = [
            'add_date', 'Add_Date', 'ADD_DATE',
            'collection_date', 'Collection_Date', 'COLLECTION_DATE',
            'date_added', 'Date_Added', 'DATE_ADDED',
            'sample_date', 'Sample_Date', 'SAMPLE_DATE'
        ]
        
        # Find which date fields exist
        existing_date_fields = [field for field in date_field_candidates if field in field_names]
        print(f"[disease_analysis] Found date fields: {existing_date_fields}")
        
        # For now, let's assume 'add_date' field (adjust based on actual field name)
        date_field = 'add_date'  # We'll make this configurable later
        
        # Convert dates to proper format for ArcGIS query
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Format for ArcGIS SQL query (depends on your database type)
            # For most cases, this format works: date '2025-01-01'
            date_where = f"{date_field} >= date '{start_date}' AND {date_field} <= date '{end_date}'"
            
        except ValueError as date_error:
            return jsonify({"status": "failure", "message": f"Invalid date format: {str(date_error)}"}), 400
        
        print(f"[disease_analysis] Date WHERE clause: {date_where}")
        
        # First, get all samples within the date range to understand the data structure
        try:
            all_samples = pools_layer.query(
                where=date_where,
                out_fields='*',
                return_geometry=True,
                result_record_count=1000  # Limit to avoid large queries initially
            )
            
            print(f"[disease_analysis] Found {len(all_samples.features)} samples in date range")
            
            # Log the first few samples to understand the data structure
            if len(all_samples.features) > 0:
                first_sample = all_samples.features[0]
                print(f"[disease_analysis] First sample attributes: {first_sample.attributes}")
                print(f"[disease_analysis] First sample geometry: {first_sample.geometry}")
                
                # Look for disease fields
                disease_field_patterns = {
                    'WNV': ['wnv', 'WNV', 'west_nile', 'West_Nile', 'WEST_NILE'],
                    'SLEV': ['slev', 'SLEV', 'st_louis', 'St_Louis', 'ST_LOUIS'],
                    'WEEV': ['weev', 'WEEV', 'western_equine', 'Western_Equine', 'WESTERN_EQUINE']
                }
                
                found_disease_fields = {}
                for disease, patterns in disease_field_patterns.items():
                    for pattern in patterns:
                        if pattern in field_names:
                            found_disease_fields[disease] = pattern
                            break
                
                print(f"[disease_analysis] Found disease fields: {found_disease_fields}")
                
        except Exception as query_error:
            print(f"[disease_analysis] Error querying samples: {query_error}")
            # Try without date filter to see if layer is accessible
            try:
                test_query = pools_layer.query(where="1=1", return_count_only=True, result_record_count=1)
                print(f"[disease_analysis] Layer is accessible, but date query failed. Total records: {test_query}")
                return jsonify({
                    "status": "failure", 
                    "message": f"Date query failed. Check date field name. Available fields: {', '.join(field_names)}"
                }), 400
            except:
                return jsonify({"status": "failure", "message": f"Layer query error: {str(query_error)}"}), 400
        
        # Now identify positive samples
        positive_samples = []
        
        for feature in all_samples.features:
            attrs = feature.attributes
            geometry = feature.geometry
            
            # Check for positive results (1 means positive, 0 means negative)
            diseases_positive = []
            
            # Check each disease field if it exists
            for disease, field_name in found_disease_fields.items():
                if attrs.get(field_name) == 1:
                    diseases_positive.append(disease)
            
            # If any disease is positive, add to our list
            if diseases_positive:
                # Extract coordinates
                if geometry and 'x' in geometry and 'y' in geometry:
                    x, y = geometry['x'], geometry['y']
                elif geometry and 'rings' in geometry:
                    # For polygon geometry, get centroid (shouldn't happen for point samples)
                    continue
                else:
                    continue
                
                positive_samples.append({
                    'objectId': attrs.get('OBJECTID', attrs.get('objectid', attrs.get('FID', 'Unknown'))),
                    'x': x,
                    'y': y,
                    'collection_date': attrs.get('collection_date', attrs.get('Collection_Date', 'Unknown')),
                    'add_date': attrs.get('add_date', attrs.get('Add_Date', 'Unknown')),
                    'wnv_positive': 'WNV' in diseases_positive,
                    'slev_positive': 'SLEV' in diseases_positive,
                    'weev_positive': 'WEEV' in diseases_positive,
                    'diseases': diseases_positive
                })
        
        print(f"[disease_analysis] Found {len(positive_samples)} positive samples")
        
        # Prepare response
        result = {
            "status": "success",
            "message": f"Analysis completed for {pools_item.title}",
            "total_samples": len(all_samples.features),
            "positive_samples": len(positive_samples),
            "samples": positive_samples[:50],  # Limit to first 50 for display
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            },
            "layer_info": {
                "title": pools_item.title,
                "feature_count": total_count,
                "fields": field_names,
                "found_date_fields": existing_date_fields,
                "found_disease_fields": found_disease_fields
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[disease_analysis] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "failure", "message": f"Analysis failed: {str(e)}"}), 500
    
if __name__ == "__main__":
    app.run(debug=True)
