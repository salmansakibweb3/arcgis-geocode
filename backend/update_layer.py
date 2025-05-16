# backend/update_layer.py
import os
import tempfile
from arcgis.features import FeatureLayerCollection

def process_update_layer(gis, uploaded_file, layer_item_id, logger=print):
    """
    Reads the uploaded CSV, tries serviceItemId to get the original CSV name,
    falls back to content.search if needed, writes a temp CSV under that filename,
    then overwrites the hosted feature layer and returns {"success": True}.
    """
    logger("[update_layer] Start processing")

    # 1) Read upload bytes
    data = uploaded_file.read()
    logger(f"[update_layer] Read {len(data)} bytes from upload")

    # 2) Load layer and collection
    layer_item = gis.content.get(layer_item_id)
    if not layer_item:
        raise ValueError(f"Layer item {layer_item_id} not found")
    flc = FeatureLayerCollection.fromitem(layer_item)
    logger(f"[update_layer] Got FeatureLayerCollection for item {layer_item.id}")

    # 3) Attempt serviceItemId lookup
    sid = getattr(flc.properties, "serviceItemId", None)
    original_name = None
    if sid:
        source_item = gis.content.get(sid)
        if source_item:
            original_name = source_item.name
            logger(f"[update_layer] serviceItemId lookup name = {original_name!r}")

    # 4) Fallback if name is missing
    if not original_name:
        logger("[update_layer] serviceItemId name was None; falling back to content.search")
        query = (
            f'title:"{layer_item.title}" '
            f'AND owner:{gis.users.me.username} '
            'AND type:"CSV"'
        )
        items = gis.content.search(query=query, max_items=1)
        if not items:
            raise RuntimeError("Cannot determine original CSV filename for overwrite")
        original_name = items[0].name
        logger(f"[update_layer] Fallback CSV item name = {original_name!r}")

    # 5) Validate and normalize filename
    if not isinstance(original_name, str) or not original_name.strip():
        raise RuntimeError(f"Invalid original_name: {original_name!r}")
    if not original_name.lower().endswith(".csv"):
        original_name += ".csv"
    logger(f"[update_layer] Final filename for overwrite: {original_name}")

    # 6) Write temp file under that name
    tmp_path = os.path.join(tempfile.gettempdir(), original_name)
    with open(tmp_path, "wb") as f:
        f.write(data)
    logger(f"[update_layer] Wrote temp CSV to: {tmp_path}")

    # 7) Perform overwrite
    logger(f"[update_layer] Overwriting layer {layer_item.id}")
    raw = flc.manager.overwrite(tmp_path)
    logger(f"[update_layer] Raw overwrite return: {raw!r}")

    # 8) Return a simple dict so Flask can JSONify safely
    return {"success": True}
