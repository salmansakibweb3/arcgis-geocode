# backend/update_layer.py
import os
import tempfile
from arcgis.features import FeatureLayerCollection

def process_update_layer(gis, uploaded_file, layer_item_id, logger=print):
    """
    1) Reads the uploaded CSV bytes.
    2) Discovers the original CSV item via serviceItemId (with content.search fallback).
    3) Writes a temp CSV named exactly as the original.
    4) Attempts flc.manager.overwrite(temp_csv).
       • If you hit the AttributeError about .replicas, falls back to:
         source_csv_item.update(...) + source_csv_item.publish(overwrite=True)
    5) Returns a simple {"success": True}.
    """
    logger("[update_layer] Start processing")

    # 1) Read the upload
    data = uploaded_file.read()
    logger(f"[update_layer] Read {len(data)} bytes from upload")

    # 2) Load the layer and its FeatureLayerCollection
    layer_item = gis.content.get(layer_item_id)
    if not layer_item:
        raise RuntimeError(f"Layer item {layer_item_id} not found")
    flc = FeatureLayerCollection.fromitem(layer_item)
    logger(f"[update_layer] Got FeatureLayerCollection for item {layer_item.id}")

    # 3) Find original CSV item name
    sid = getattr(flc.properties, "serviceItemId", None)
    source_csv = None
    if sid:
        source_csv = gis.content.get(sid)
        logger(f"[update_layer] serviceItemId → CSV item id = {sid!r}")
    if not source_csv:
        # fallback to content.search
        logger("[update_layer] Falling back to content.search for CSV item")
        q = (
            f'title:"{layer_item.title}" '
            f'AND owner:{gis.users.me.username} '
            'AND type:"CSV"'
        )
        results = gis.content.search(query=q, max_items=1)
        if not results:
            raise RuntimeError("Cannot locate the original CSV item in AGOL")
        source_csv = results[0]
        logger(f"[update_layer] content.search → CSV item id = {source_csv.id!r}")

    name = source_csv.name or ""
    logger(f"[update_layer] source_csv.name = {name!r}")
    if not name.lower().endswith(".csv"):
        name = f"{name}.csv"
    logger(f"[update_layer] Final CSV filename = {name!r}")

    # 4) Dump the upload into a temp file named exactly that
    tmp = os.path.join(tempfile.gettempdir(), name)
    with open(tmp, "wb") as fp:
        fp.write(data)
    logger(f"[update_layer] Wrote temp CSV to: {tmp}")

    # 5) Try the normal overwrite()
    try:
        logger(f"[update_layer] Attempting flc.manager.overwrite({tmp!r})")
        res = flc.manager.overwrite(tmp)
        logger(f"[update_layer] overwrite() returned: {res!r}")
        return {"success": True}
    except AttributeError as ae:
        msg = str(ae)
        logger(f"[update_layer] overwrite() AttributeError: {msg!r}")
        if "replicas" in msg:
            # the known bug: fallback to CSV.update + publish
            logger("[update_layer] Falling back to source_csv.update() + publish(overwrite=True)")
            source_csv.update({}, tmp)
            pub = source_csv.publish(overwrite=True)
            logger(f"[update_layer] publish() returned: {pub!r}")
            return {"success": True}
        # if it was a different attribute error, re-raise
        raise

    except Exception:
        # any other failure, let it bubble up
        raise
