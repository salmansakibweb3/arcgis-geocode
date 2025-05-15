# backend/update_layer.py
import os
import tempfile
from arcgis.features import FeatureLayerCollection

def process_update_layer(gis, uploaded_file, layer_item_id, logger=print):
    """
    Reads the uploaded CSV (a Werkzeug FileStorage),
    discovers the original CSV item name via serviceItemId,
    writes a temp CSV with that exact filename,
    and overwrites the hosted feature layer.
    Returns the overwrite() result dict, or raises on error.
    """
    logger("[update_layer] Start processing")

    # 1) Read raw bytes
    data = uploaded_file.read()
    logger(f"[update_layer] Read {len(data)} bytes from upload")

    # 2) Fetch the layer item & collection
    layer_item = gis.content.get(layer_item_id)
    if not layer_item:
        raise ValueError(f"Layer item {layer_item_id} not found")
    flc = FeatureLayerCollection.fromitem(layer_item)
    logger(f"[update_layer] Got FeatureLayerCollection for item {layer_item.id}")

    # 3) Pull the original CSV item via serviceItemId
    sid = flc.properties.serviceItemId
    if not sid:
        raise RuntimeError("serviceItemId missing on this Feature Layer")
    source_item = gis.content.get(sid)
    if not source_item:
        raise RuntimeError(f"Cannot load source item {sid}")
    original_name = source_item.name
    # Ensure we have a .csv extension
    if not original_name.lower().endswith(".csv"):
        original_name = f"{original_name}.csv"
    logger(f"[update_layer] Original CSV filename from AGOL: {original_name}")

    # 4) Write to a temp file under that exact name
    tmp_path = os.path.join(tempfile.gettempdir(), original_name)
    with open(tmp_path, "wb") as f:
        f.write(data)
    logger(f"[update_layer] Wrote temp CSV to: {tmp_path}")

    # 5) Overwrite the hosted layer
    logger(f"[update_layer] Overwriting layer {layer_item.id} with {original_name}")
    try:
        result = flc.manager.overwrite(tmp_path)
        logger(f"[update_layer] Overwrite succeeded: {result}")
        return result
    except Exception as e:
        logger(f"[update_layer] Overwrite failed: {e!r}")
        raise
