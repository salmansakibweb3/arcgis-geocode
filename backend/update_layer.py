# backend/update_layer.py

import os
import tempfile

def process_update_layer(gis, uploaded_file, layer_item_id, csv_item_id, logger=print):
    """
    1) Write the uploaded CSV to a temp file (preserving its original filename).
    2) Load the CSV item by the exact csv_item_id you passed in.
    3) Call csv_item.update(...) and then csv_item.publish(overwrite=True).
    """

    logger("[update_layer] Start processing")

    # 1) Read bytes & preserve client filename
    data = uploaded_file.read()
    fn = uploaded_file.filename or "data.csv"
    if not fn.lower().endswith(".csv"):
        fn += ".csv"
    logger(f"[update_layer] Using filename: {fn!r}")

    # 2) Write to temp under that name
    tmp = os.path.join(tempfile.gettempdir(), fn)
    with open(tmp, "wb") as f:
        f.write(data)
    logger(f"[update_layer] Wrote temp CSV to: {tmp}")

    # 3) Fetch the CSV item directly by ID
    csv_item = gis.content.get(csv_item_id)
    if not csv_item:
        raise RuntimeError(f"CSV item {csv_item_id} not found")
    logger(f"[update_layer] Got CSV item: {csv_item.id} (name={csv_item.name!r})")

    # 4) Update its data, then re‐publish the hosted feature layer
    logger("[update_layer] Calling csv_item.update()")
    csv_item.update({}, tmp)

    logger("[update_layer] Calling csv_item.publish(overwrite=True)")
    pub = csv_item.publish(overwrite=True)
    logger(f"[update_layer] publish() returned: {pub!r}")

    return {"success": True}
