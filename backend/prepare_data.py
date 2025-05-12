# backend/prepare_data.py

import pandas as pd
from io import BytesIO

def prepare_data(file_storage):
    """
    Reads the uploaded CSV (a Werkzeug FileStorage),
    sums the last three columns into 'total_abundance',
    and returns a BytesIO buffer containing the new CSV.
    """
    # 1) Read into DataFrame
    df = pd.read_csv(file_storage)

    # 2) Sum the last three columns
    #    (regardless of their names)
    df['total_abundance'] = df.iloc[:, -3:].sum(axis=1)

    # 3) Write to a BytesIO buffer
    buf = BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf
