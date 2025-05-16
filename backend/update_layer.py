# backend/update_layer.py
import os
import tempfile
from arcgis.features import FeatureLayerCollection

def process_update_layer(gis, uploaded_file, layer_item_id, logger=print):
    logger("[update_layer] Start processing")

    # 1) Read upload
    data = uploaded_file.read()
    logger(f"[update_layer] Read {len(data)} bytes from upload")

    # 2) Load layer & collection
    layer_item = gis.content.get(layer_item_id)
    if not layer_item:
        raise ValueError(f"Layer item {layer_item_id} not found")
    flc = FeatureLayerCollection.fromitem(layer_item)
    logger(f"[update_layer] Got FeatureLayerCollection for item {layer_item.id}")

    # 3) Determine filename (serviceItemId + fallback)
    sid = getattr(flc.properties, "serviceItemId", None)
    name = None
    if sid:
        source_item = gis.content.get(sid)
        if source_item:
            name = source_item.name
            logger(f"[update_layer] serviceItemId lookup name = {name!r}")
    if not name:
        logger("[update_layer] Falling back to content.search")
        q = (
            f'title:"{layer_item.title}" '
            f'AND owner:{gis.users.me.username} '
            'AND type:"CSV"'
        )
        items = gis.content.search(q, max_items=1)
        if not items:
            raise RuntimeError("Cannot determine original CSV filename")
        name = items[0].name
        logger(f"[update_layer] Fallback name = {name!r}")

    if not isinstance(name, str) or not name.strip():
        raise RuntimeError(f"Invalid filename: {name!r}")
    if not name.lower().endswith(".csv"):
        name += ".csv"
    logger(f"[update_layer] Final overwrite filename: {name}")

    # 4) Write temp file
    tmp = os.path.join(tempfile.gettempdir(), name)
    with open(tmp, "wb") as f:
        f.write(data)
    logger(f"[update_layer] Wrote temp CSV to: {tmp}")

    # 5) Overwrite and debug the raw return
    logger(f"[update_layer] Calling overwrite() on {layer_item.id}")
    raw = flc.manager.overwrite(tmp)
    logger(f"[update_layer] overwrite() returned type={type(raw)!r}")
    logger(f"[update_layer] overwrite() returned repr: {raw!r}")

    # 6) Return a safe, JSON-serializable dict
    return {"success": True}
