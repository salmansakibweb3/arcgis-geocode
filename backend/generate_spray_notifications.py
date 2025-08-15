# backend/generate_spray_notifications.py

import pandas as pd
from datetime import datetime
import tempfile
import os
from io import BytesIO
from arcgis.features import FeatureLayer
from arcgis.geometry import Geometry

def generate_spray_notifications(
    gis,
    selected_subgrids,
    buffer_distance=300,
    logger=print
):
    """
    Generate spray notifications CSV using distance-based spatial queries instead of buffer polygons.
    This approach is more reliable than creating buffer geometries with the ArcGIS Python API.
    
    Args:
        gis: Authenticated ArcGIS GIS object
        selected_subgrids: List of subgrid numbers/IDs to process
        buffer_distance: Buffer distance in feet (default 300)
        logger: Logging function
        
    Returns:
        BytesIO buffer containing the CSV data
    """
    
    logger("[spray_notifications] Starting spray notifications generation")
    
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
        
        # 5. Use a much simpler approach: distance-based queries with geographic functions
        logger(f"[spray_notifications] Using distance-based SQL queries (most reliable approach)")
        
        # Convert feet to meters for distance calculations
        buffer_meters = buffer_distance * 0.3048
        logger(f"[spray_notifications] Buffer distance: {buffer_distance} feet = {buffer_meters:.2f} meters")
        
        all_residents = []
        
        for i, subgrid_geom in enumerate(subgrid_geometries):
            logger(f"[spray_notifications] Processing subgrid {i+1}/{len(subgrid_geometries)}")
            
            try:
                # Try multiple spatial relationship approaches
                approaches = [
                    ('intersects', 'esriSpatialRelIntersects'),
                    ('contains', 'esriSpatialRelContains'), 
                    ('within', 'esriSpatialRelWithin'),
                    ('overlaps', 'esriSpatialRelOverlaps')
                ]
                
                best_result = []
                best_count = 0
                
                for approach_name, spatial_rel in approaches:
                    try:
                        query_result = resident_layer.query(
                            geometry_filter={
                                'geometry': subgrid_geom,
                                'geometryType': 'esriGeometryPolygon',
                                'spatialRel': spatial_rel
                            },
                            out_fields='*',
                            return_geometry=False
                        )
                        
                        result_count = len(query_result.features)
                        logger(f"[spray_notifications] {approach_name} query returned {result_count} residents")
                        
                        if result_count > best_count:
                            best_result = query_result.features
                            best_count = result_count
                            logger(f"[spray_notifications] New best result: {approach_name} with {result_count} residents")
                        
                    except Exception as approach_error:
                        logger(f"[spray_notifications] {approach_name} approach failed: {approach_error}")
                        continue
                
                # Now try expanded envelope approach for buffer effect
                try:
                    logger(f"[spray_notifications] Trying expanded envelope for buffer effect...")
                    
                    # Get geometry extent and expand it
                    geom_extent = subgrid_geom.extent
                    
                    # Handle both tuple and dict formats safely
                    if hasattr(geom_extent, '__len__') and len(geom_extent) == 4:
                        # Tuple format: (xmin, ymin, xmax, ymax)
                        xmin, ymin, xmax, ymax = geom_extent
                        sr = subgrid_geom.spatial_reference
                    else:
                        # Already handled as dict in previous approach
                        logger(f"[spray_notifications] Complex extent format, skipping envelope expansion")
                        xmin = ymin = xmax = ymax = None
                        sr = None
                    
                    if xmin is not None:
                        # Convert buffer distance to degrees (rough approximation)
                        buffer_degrees = buffer_distance / 364000.0
                        
                        # Create expanded envelope geometry
                        expanded_envelope = {
                            'xmin': xmin - buffer_degrees,
                            'ymin': ymin - buffer_degrees, 
                            'xmax': xmax + buffer_degrees,
                            'ymax': ymax + buffer_degrees,
                            'spatialReference': sr
                        }
                        
                        envelope_query = resident_layer.query(
                            geometry_filter={
                                'geometry': expanded_envelope,
                                'geometryType': 'esriGeometryEnvelope',
                                'spatialRel': 'esriSpatialRelIntersects'
                            },
                            out_fields='*',
                            return_geometry=False
                        )
                        
                        envelope_count = len(envelope_query.features)
                        logger(f"[spray_notifications] Expanded envelope returned {envelope_count} residents")
                        
                        if envelope_count > best_count:
                            best_result = envelope_query.features
                            best_count = envelope_count
                            logger(f"[spray_notifications] New best result: expanded envelope with {envelope_count} residents")
                    
                except Exception as envelope_error:
                    logger(f"[spray_notifications] Expanded envelope failed: {envelope_error}")
                
                if best_result:
                    all_residents.extend(best_result)
                    logger(f"[spray_notifications] Added {len(best_result)} residents from subgrid {i+1}")
                else:
                    logger(f"[spray_notifications] No residents found for subgrid {i+1} with any approach")
                
            except Exception as query_error:
                logger(f"[spray_notifications] All query approaches failed on subgrid {i+1}: {query_error}")
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
