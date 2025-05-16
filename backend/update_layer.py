# backend/update_layer.py
import os
import tempfile
from arcgis.features import FeatureLayerCollection

def process_update_layer(gis, uploaded_file, layer_item_id, logger=print):
    """
    Reads the uploaded CSV, discovers the original CSV via serviceItemId,
    writes a temp CSV under that exact filename, overwrites the layer,
    and returns a simple dict indicating success.
    """
    logger("[update_layer] Start processing")

    # 1) Read the upload bytes
    data = uploaded_file.read()
    logger(f"[update_layer] Read {len(data)} bytes from upload")

    # 2) Load the layer item and build the FeatureLayerCollection
    layer_item = gis.content.get(layer_item_id)
    if not layer_item:
        raise ValueError(f"Layer item {layer_item_id} not found")
    flc = FeatureLayerCollection.fromitem(layer_item)
    logger(f"[update_layer] Got FeatureLayerCollection for item {layer_item.id}")

    # 3) Discover the original CSV via serviceItemId
    sid = flc.properties.serviceItemId
    if not sid:
        raise RuntimeError("serviceItemId missing on this Feature Layer")
    source_item = gis.content.get(sid)
    if not source_item:
        raise RuntimeError(f"Cannot load source item {sid}")
    original_name = source_item.name
    logger(f"[update_layer] source_item.name = {original_name!r}")

    # 4) Guard against None and ensure .csv extension
    if original_name is None:
        raise RuntimeError("AGOL source_item.name came back None")
    if not original_name.lower().endswith(".csv"):
        original_name += ".csv"
    logger(f"[update_layer] Using filename for overwrite: {original_name}")

    # 5) Write the upload to a temp file under that exact name
    tmp_path = os.path.join(tempfile.gettempdir(), original_name)
    with open(tmp_path, "wb") as f:
        f.write(data)
    logger(f"[update_layer] Wrote temp CSV to: {tmp_path}")

    # 6) Perform the overwrite
    logger(f"[update_layer] Overwriting layer {layer_item.id}")
    try:
        raw = flc.manager.overwrite(tmp_path)
        logger(f"[update_layer] Raw overwrite return: {raw!r}")
    except Exception as e:
        logger(f"[update_layer] Overwrite failed: {e!r}")
        raise

    # 7) Return a plain dict for Flask to JSONify
    return {"success": True}
