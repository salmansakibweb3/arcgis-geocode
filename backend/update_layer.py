# backend/update_layer.py
import os
import tempfile
import pandas as pd
from arcgis.features import FeatureLayerCollection

def process_update_layer(gis, uploaded_file, layer_item_id, logger=print):
    """
    Reads the uploaded CSV (a Werkzeug FileStorage), 
    finds the original CSV item name in AGOL, 
    writes a temp CSV with the exact same filename,
    and overwrites the hosted feature layer.
    
    Returns the overwrite() result dict, or raises on error.
    """
    logger("[update_layer] Start processing")

    # 1) Read bytes from upload
    data = uploaded_file.read()
    logger(f"[update_layer] Read {len(data)} bytes from upload")

    # 2) Fetch the Feature Layer item
    layer_item = gis.content.get(layer_item_id)
    if not layer_item:
        raise ValueError(f"Layer item {layer_item_id} not found")
    logger(f"[update_layer] Got layer_item: {layer_item}")

    # 3) Find the CSV item that originally published this service
    #    Search by title & owner & type CSV
    query = (
        f'title:"{layer_item.title}" '
        f'AND owner:{gis.users.me.username} '
        'AND type:"CSV"'
    )
    csv_items = gis.content.search(query=query, max_items=1)
    if not csv_items:
        raise ValueError("Original CSV item not found in AGOL")
    csv_item = csv_items[0]
    base_name = csv_item.name  # no extension
    logger(f"[update_layer] Found source CSV: {csv_item.id} as '{base_name}'")

    # 4) Build the exact filename (with .csv)
    filename = base_name if base_name.lower().endswith('.csv') else f"{base_name}.csv"
    logger(f"[update_layer] Using filename: {filename}")

    # 5) Write the upload to a temp file with that filename
    temp_csv = os.path.join(tempfile.gettempdir(), filename)
    with open(temp_csv, 'wb') as f:
        f.write(data)
    logger(f"[update_layer] Wrote temp CSV to: {temp_csv}")

    # 6) Overwrite the hosted feature layer
    flc = FeatureLayerCollection.fromitem(layer_item)
    logger(f"[update_layer] Overwriting layer ID: {layer_item.id}")
    result = flc.manager.overwrite(temp_csv)
    logger(f"[update_layer] Overwrite result: {result}")

    return result
