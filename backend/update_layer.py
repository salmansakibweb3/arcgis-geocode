# backend/update_layer.py

import os
import tempfile
from arcgis.features import FeatureLayerCollection

def process_update_layer(
    gis,
    uploaded_file,
    layer_item_id,
    csv_item_id=None,
    logger=print
):
    """
    1) Writes uploaded CSV to a temp file (preserving its original filename).
    2) Attempts flc.manager.overwrite(tmp_file).
    3) If overwrite() fails (e.g. the 'replicas' bug), falls back to:
         csv_item.update({}, tmp_file)
         csv_item.publish(overwrite=True)
    4) Returns {"success": True, "method": "<used_method>"}.
    """

    logger("[update_layer] Start processing")

    # 1) Read upload & preserve the client filename
    data = uploaded_file.read()
    fn = uploaded_file.filename or "data.csv"
    if not fn.lower().endswith(".csv"):
        fn += ".csv"
    logger(f"[update_layer] Using filename: {fn!r}")

    # 2) Dump to temp file under that name
    tmp_path = os.path.join(tempfile.gettempdir(), fn)
    with open(tmp_path, "wb") as f:
        f.write(data)
    logger(f"[update_layer] Wrote temp CSV to: {tmp_path}")

    # 3) Load the FeatureLayerCollection
    layer_item = gis.content.get(layer_item_id)
    if not layer_item:
        raise RuntimeError(f"Hosted layer item {layer_item_id} not found")
    flc = FeatureLayerCollection.fromitem(layer_item)
    logger(f"[update_layer] Got FeatureLayerCollection for item {layer_item.id}")

    # 4) Try the native overwrite()
    try:
        logger(f"[update_layer] Attempting flc.manager.overwrite({tmp_path!r})")
        res = flc.manager.overwrite(tmp_path)
        logger(f"[update_layer] overwrite() returned: {res!r}")
        return {"success": True, "method": "overwrite"}
    except Exception as overwrite_err:
        err_msg = str(overwrite_err)
        logger(f"[update_layer] overwrite() failed: {err_msg!r}")

        # Fallback to update + publish if it's the known replicas bug (or any overwrite failure)
        logger("[update_layer] Falling back to csv_item.update() + publish(overwrite=True)")

        # 5) Locate the CSV item to update
        if csv_item_id:
            csv_item = gis.content.get(csv_item_id)
            logger(f"[update_layer] Using csv_item_id: {csv_item_id}")
        else:
            # optional dynamic lookup if you ever want csv_item_id to be None
            sid = getattr(flc.properties, "serviceItemId", None)
            csv_item = gis.content.get(sid) if sid else None
            if not csv_item:
                # last‐ditch search by title
                q = (
                    f'title:"{layer_item.title}" '
                    f'AND owner:{gis.users.me.username} '
                    'AND type:"CSV"'
                )
                found = gis.content.search(q, max_items=1)
                if not found:
                    raise RuntimeError("Could not locate CSV item to update")
                csv_item = found[0]
            logger(f"[update_layer] Dynamically found CSV item: {csv_item.id}")

        if not csv_item:
            raise RuntimeError("CSV item lookup failed; cannot update")

        logger("[update_layer] Calling csv_item.update({}, {tmp_path!r})")
        csv_item.update({}, tmp_path)

        logger("[update_layer] Calling csv_item.publish(overwrite=True)")
        pub = csv_item.publish(overwrite=True)
        logger(f"[update_layer] publish() returned: {pub!r}")

        return {"success": True, "method": "update+publish"}
