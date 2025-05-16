# backend/update_layer.py
import os
import tempfile
from arcgis.features import FeatureLayerCollection

def process_update_layer(gis, uploaded_file, layer_item_id, logger=print):
    """
    Reads the uploaded CSV, discovers the original CSV via serviceItemId,
    writes a temp CSV under that exact filename, overwrites the layer,
    and returns a plain dict indicating success.
    """
    logger("[update_layer] Start processing")

    # 1) Read the raw upload bytes
    data = uploaded_file.read()
    logger(f"[update_layer] Read {len(data)} bytes from upload")

    # 2) Load the layer + collection
    layer_item = gis.content.get(layer_item_id)
    if not layer_item:
        raise ValueError(f"Layer item {layer_item_id} not found")
    flc = FeatureLayerCollection.fromitem(layer_item)
    logger(f"[update_layer] Got FeatureLayerCollection for item {layer_item.id}")

    # 3) Find the original CSV filename via serviceItemId
    sid = flc.properties.serviceItemId
    if not sid:
        raise RuntimeError("serviceItemId missing on this Feature Layer")
    source_item = gis.content.get(sid)
    original_name = source_item.name
    if not original_name.lower().endswith(".csv"):
        original_name += ".csv"
    logger(f"[update_layer] Original CSV filename from AGOL: {original_name}")

    # 4) Write to a temp file under that exact name
    tmp_path = os.path.join(tempfile.gettempdir(), original_name)
    with open(tmp_path, "wb") as f:
        f.write(data)
    logger(f"[update_layer] Wrote temp CSV to: {tmp_path}")

    # 5) Overwrite the hosted layer
    logger(f"[update_layer] Overwriting layer {layer_item.id}")
    raw_result = flc.manager.overwrite(tmp_path)
    logger(f"[update_layer] Raw overwrite return: {raw_result!r}")

    # 6) Return a simple dict so Flask can JSONify it safely
    return {"success": True}
