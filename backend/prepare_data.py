# backend/prepare_data.py

import pandas as pd
from io import BytesIO

def prepare_data(file_storage):
    """
    Reads the uploaded CSV (a Werkzeug FileStorage),
    sums all 'females' columns into 'total_abundance',
    and returns a BytesIO buffer containing the new CSV.
    
    Handles variable female column structures:
    - females - mixed
    - females - unfed  
    - females - gravid
    - females - bloodfed
    """
    # 1) Read into DataFrame
    df = pd.read_csv(file_storage)

    # 2) Find all columns that start with 'females'
    female_columns = [col for col in df.columns if col.lower().startswith('females')]
    
    # 3) Calculate total_abundance from all female columns
    if female_columns:
        # Convert to numeric, replacing any non-numeric values with 0
        female_data = df[female_columns].apply(pd.to_numeric, errors='coerce').fillna(0)
        df['total_abundance'] = female_data.sum(axis=1)
        print(f"[prepare_data] Found female columns: {female_columns}")
        print(f"[prepare_data] Calculated total_abundance from {len(female_columns)} female columns")
    else:
        # Fallback: if no 'females' columns found, set total_abundance to 0
        df['total_abundance'] = 0
        print("[prepare_data] WARNING: No female columns found, setting total_abundance to 0")

    # 4) Write to a BytesIO buffer
    buf = BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf
