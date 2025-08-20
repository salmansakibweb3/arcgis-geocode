# backend/generate_spray_notifications.py

import pandas as pd
from datetime import datetime
import tempfile
import os
import time
from io import BytesIO
from arcgis.features import FeatureLayer
from arcgis.geometry import Geometry

def retry_query(func, max_retries=3, delay=2, logger=print):
    """Retry a query function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            logger(f"[retry] Query attempt {attempt+1} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
    return None

def generate_spray_notifications(
    gis,
    selected_subgrids,
    buffer_distance=300,
    logger=print
):
    """
    Generate spray notifications CSV using OPTIMIZED spatial queries for production.
    Optimized to avoid timeouts in production environments like Render.
    
    Args:
        gis: Authenticated ArcGIS GIS object
        selected_subgrids: List of subgrid numbers/IDs to process
        buffer_distance: Buffer distance in feet (default 300)
        logger: Logging function
        
    Returns:
        BytesIO buffer containing the CSV data
    """
    
    logger("[spray_notifications] Starting spray notifications generation (OPTIMIZED)")
    
    # Layer IDs
    SUBGRID_LAYER_ID = "e8656893998e497fa8161f87d053a725"
    RESIDENT_NOTICES_LAYER_ID = "cd84fc9ddca2406f85c185a5841be65b"
    
    # Fields to include in output
    desired_fields = [
        "OBJECTID", "TYPE", "NAME", "DATEADDED", "COMMENTS",
        "ZONE", "ZONE2", "DONOTSPRAY", "ADDRESS", 
        "PHONENUMBE", "AddStatus", "Email"
    ]
    
    try:
        # 1. Access subgrid layer
        logger(f"[spray_notifications] Accessing subgrid layer: {SUBGRID_LAYER_ID}")
        subgrid_item = gis.content.get(SUBGRID_LAYER_ID)
        if not subgrid_item:
            raise RuntimeError(f"Could not access subgrid layer: {SUBGRID_LAYER_ID}")
        
        subgrid_layer = subgrid_item.layers[0]
        logger(f"[spray_notifications] Subgrid layer: '{subgrid_layer.properties.name}' (Type: {subgrid_item.type})")
        
        # 2. Query selected subgrids
        subgrid_where_clause = f"GridLabel IN ({','.join([repr(sg) for sg in selected_subgrids])})"
        logger(f"[spray_notifications] Querying subgrids with: {subgrid_where_clause}")
        
        subgrid_features = subgrid_layer.query(
            where=subgrid_where_clause,
            out_fields='*',
            return_geometry=True
        )
        
        if not subgrid_features.features:
            raise RuntimeError(f"No subgrid features found for: {selected_subgrids}")
        
        logger(f"[spray_notifications] Found {len(subgrid_features.features)} subgrid features")
        
        # 3. Process subgrid geometries for spatial queries
        subgrid_geometries = []
        
        for i, feature in enumerate(subgrid_features.features):
            logger(f"[spray_notifications] Processing subgrid feature {i+1}/{len(subgrid_features.features)}")
            
            feature_geom = feature.geometry
            if feature_geom:
                try:
                    geom_obj = Geometry(feature_geom)
                    subgrid_geometries.append(geom_obj)
                    logger(f"[spray_notifications] Geometry added for spatial query")
                except Exception as e:
                    logger(f"[spray_notifications] Error processing geometry: {e}")
                    continue
            else:
                logger(f"[spray_notifications] WARNING: No geometry for feature {i+1}")
        
        logger(f"[spray_notifications] Collected {len(subgrid_geometries)} subgrid geometries")
        
        # 4. Access resident notices layer
        logger(f"[spray_notifications] Accessing resident notices layer: {RESIDENT_NOTICES_LAYER_ID}")
        resident_item = gis.content.get(RESIDENT_NOTICES_LAYER_ID)
        if not resident_item:
            raise RuntimeError(f"Could not access resident notices layer: {RESIDENT_NOTICES_LAYER_ID}")
            
        resident_layer = resident_item.layers[0]
        logger(f"[spray_notifications] Resident notices layer: '{resident_layer.properties.name}' (Type: {resident_item.type})")
        
        # 5. OPTIMIZED: Single combined query approach for production
        logger(f"[spray_notifications] Using OPTIMIZED single-query approach for production")
        
        # Convert feet to meters for distance calculations
        buffer_meters = buffer_distance * 0.3048
        logger(f"[spray_notifications] Buffer distance: {buffer_distance} feet = {buffer_meters:.2f} meters")
        
        all_residents = []
        processed_resident_ids = set()  # Avoid duplicates
        
        # Calculate overall bounding box for ALL subgrids at once
        all_extents = []
        for geom in subgrid_geometries:
            try:
                extent = geom.extent
                if hasattr(extent, '__len__') and len(extent) == 4:
                    all_extents.append(extent)
                elif isinstance(extent, dict) and all(k in extent for k in ['xmin', 'ymin', 'xmax', 'ymax']):
                    all_extents.append([extent['xmin'], extent['ymin'], extent['xmax'], extent['ymax']])
            except Exception as e:
                logger(f"[spray_notifications] Warning: Could not get extent for geometry: {e}")
        
        if not all_extents:
            logger(f"[spray_notifications] No valid extents found, cannot proceed")
            raise RuntimeError("No valid geometry extents found for subgrids")
        
        # Calculate combined bounding box for ALL subgrids
        min_x = min(extent[0] for extent in all_extents)
        min_y = min(extent[1] for extent in all_extents)
        max_x = max(extent[2] for extent in all_extents)
        max_y = max(extent[3] for extent in all_extents)
        
        # Add buffer to the combined envelope  
        buffer_degrees = buffer_distance / 364000.0  # Rough conversion
        combined_envelope = {
            'xmin': min_x - buffer_degrees,
            'ymin': min_y - buffer_degrees,
            'xmax': max_x + buffer_degrees,
            'ymax': max_y + buffer_degrees,
            'spatialReference': {'wkid': 4326}  # WGS84
        }
        
        logger(f"[spray_notifications] Querying ALL residents within combined envelope (single query)...")
        logger(f"[spray_notifications] Combined envelope: [{min_x:.6f}, {min_y:.6f}, {max_x:.6f}, {max_y:.6f}] + {buffer_distance}ft buffer")
        
        try:
            # SINGLE QUERY for all residents in the area WITH RETRY
            def do_combined_query():
                return resident_layer.query(
                    geometry_filter={
                        'geometry': combined_envelope,
                        'geometryType': 'esriGeometryEnvelope',
                        'spatialRel': 'esriSpatialRelIntersects'
                    },
                    out_fields='*',
                    return_geometry=False,
                    max_record_count=5000  # Increase limit for large areas
                )
            
            all_query = retry_query(do_combined_query, max_retries=3, logger=logger)
            all_residents = all_query.features if all_query else []
            logger(f"[spray_notifications] Single query found {len(all_residents)} residents in combined area")
            
        except Exception as query_error:
            logger(f"[spray_notifications] Combined query failed after retries, falling back to individual queries: {query_error}")
            all_residents = []
        
        # Fallback with retries if main query failed
        if not all_residents:
            logger(f"[spray_notifications] No residents from combined query, trying individual queries with retries...")
            
            for i, subgrid_geom in enumerate(subgrid_geometries):
                logger(f"[spray_notifications] Fallback query for subgrid {i+1}/{len(subgrid_geometries)}")
                try:
                    # Define individual query function for retry
                    def do_individual_query():
                        return resident_layer.query(
                            geometry_filter={
                                'geometry': subgrid_geom,
                                'geometryType': 'esriGeometryPolygon',
                                'spatialRel': 'esriSpatialRelIntersects'
                            },
                            out_fields='*',
                            return_geometry=False
                        )
                    
                    individual_query = retry_query(do_individual_query, max_retries=2, logger=logger)
                    
                    if individual_query:
                        for resident in individual_query.features:
                            resident_id = resident.attributes.get('OBJECTID')
                            if resident_id not in processed_resident_ids:
                                all_residents.append(resident)
                                processed_resident_ids.add(resident_id)
                        
                        logger(f"[spray_notifications] Subgrid {i+1} query found {len(individual_query.features)} residents")
                    else:
                        logger(f"[spray_notifications] All retries failed for subgrid {i+1}")
                    
                except Exception as individual_error:
                    logger(f"[spray_notifications] Individual query failed for subgrid {i+1}: {individual_error}")
                    continue
        
        logger(f"[spray_notifications] Found {len(all_residents)} total resident records")
        
        # 6. Convert to DataFrame for processing
        logger(f"[spray_notifications] Converting {len(all_residents)} records to DataFrame")
        
        if not all_residents:
            logger(f"[spray_notifications] No residents found within buffer distance")
            empty_df = pd.DataFrame(columns=desired_fields)
            csv_buffer = BytesIO()
            empty_df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            today = datetime.today().strftime("%m%d%Y")
            filename = f"Spray_Notifications_{today}.csv"
            return {
                'csv_buffer': csv_buffer,
                'filename': filename
            }
        
        # Extract attributes from features
        records = []
        for feature in all_residents:
            if hasattr(feature, 'attributes'):
                records.append(feature.attributes)
        
        logger(f"[spray_notifications] Successfully processed {len(records)} records")
        
        # Create DataFrame
        df = pd.DataFrame(records)
        logger(f"[spray_notifications] DataFrame created with shape: {df.shape}")
        
        # Filter to only include the desired fields that exist in the data
        available_desired_fields = [field for field in desired_fields if field in df.columns]
        logger(f"[spray_notifications] Filtering to desired fields: {available_desired_fields}")
        
        if available_desired_fields:
            df = df[available_desired_fields]
            logger(f"[spray_notifications] Filtered DataFrame shape: {df.shape}")
        else:
            logger(f"[spray_notifications] Warning: None of the desired fields found in data")
        
        # Convert DATEADDED timestamp to readable date format
        if 'DATEADDED' in df.columns:
            logger(f"[spray_notifications] Converting DATEADDED column from timestamp to date format")
            
            def convert_timestamp_to_date(timestamp_ms):
                try:
                    if pd.isna(timestamp_ms) or timestamp_ms == '' or timestamp_ms is None:
                        return ''
                    timestamp_sec = int(timestamp_ms) / 1000
                    date_obj = datetime.fromtimestamp(timestamp_sec)
                    return date_obj.strftime('%m/%d/%Y')
                except (ValueError, OSError, OverflowError) as e:
                    logger(f"[spray_notifications] Date conversion error for value {timestamp_ms}: {e}")
                    return str(timestamp_ms)
            
            df['DATEADDED'] = df['DATEADDED'].apply(convert_timestamp_to_date)
        
        # Remove duplicates
        dedup_fields = [f for f in ['TYPE', 'NAME', 'PHONENUMBE', 'Email'] if f in df.columns]
        logger(f"[spray_notifications] Deduplicating on fields: {dedup_fields}")
        
        if dedup_fields:
            initial_count = len(df)
            df = df.drop_duplicates(subset=dedup_fields, keep='first')
            removed_count = initial_count - len(df)
            logger(f"[spray_notifications] Removed {removed_count} duplicate records")
        
        # 7. Generate CSV
        today = datetime.today().strftime("%m%d%Y")
        filename = f"Spray_Notifications_{today}.csv"
        
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        logger(f"[spray_notifications] Successfully generated {filename} with {len(df)} records")
        
        # Return dictionary with csv_buffer and filename as expected by Flask endpoint
        return {
            'csv_buffer': csv_buffer,
            'filename': filename
        }
        
    except Exception as e:
        logger(f"[spray_notifications] Error: {e}")
        raise RuntimeError(f"Spray notifications generation failed: {e}")
