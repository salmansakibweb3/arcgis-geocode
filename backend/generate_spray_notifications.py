# backend/generate_spray_notifications.py

import pandas as pd
from datetime import datetime
import tempfile
import os
from io import BytesIO
from arcgis.features import FeatureLayer
from arcgis.geometry import buffer, Geometry, Point
from arcgis.geometry.filters import intersects, within, contains

def generate_spray_notifications(
    gis,
    selected_subgrids,
    buffer_distance=300,
    logger=print
):
    """
    Generate spray notifications CSV by selecting subgrids and buffering against resident notices.
    
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
    RESIDENT_NOTICES_LAYER_ID = "cd84fc9ddca2406f85c185a5841be65b"  # Hosted feature layer: Resident_Notices_2025
    # RESIDENT_NOTICES_SUBLAYER = 31  # Not needed for hosted feature layer
    
    # Fields to extract from resident notices
    desired_fields = [
        "OBJECTID", "TYPE", "NAME", "DATEADDED", "COMMENTS",
        "ZONE", "ZONE2", "DONOTSPRAY", "ADDRESS",
        "PHONENUMBE", "AddStatus", "Email"
    ]
    
    try:
        # 1. Get the subgrid layer
        logger(f"[spray_notifications] Accessing subgrid layer: {SUBGRID_LAYER_ID}")
        subgrid_item = gis.content.get(SUBGRID_LAYER_ID)
        if not subgrid_item:
            raise RuntimeError(f"Could not access subgrid layer: {SUBGRID_LAYER_ID}")
        
        logger(f"[spray_notifications] Subgrid layer: '{subgrid_item.title}' (Type: {subgrid_item.type})")
        subgrid_layer = FeatureLayer.fromitem(subgrid_item)
        
        # 2. Query selected subgrids using GridLabel
        # Convert list to SQL-compatible string format
        gridlabel_list = "','".join([str(sg) for sg in selected_subgrids])
        where_clause = f"GridLabel IN ('{gridlabel_list}')"
        logger(f"[spray_notifications] Querying subgrids with: {where_clause}")
        
        subgrid_features = subgrid_layer.query(where=where_clause, return_geometry=True)
        if len(subgrid_features.features) == 0:
            raise RuntimeError(f"No subgrids found for GridLabels: {selected_subgrids}")
        
        logger(f"[spray_notifications] Found {len(subgrid_features.features)} subgrid features")
        
        # 3. Read actual spatial reference from geometries and create buffers accordingly
        logger(f"[spray_notifications] Reading actual spatial reference from subgrid geometries")
        
        # Get the first feature to determine the actual spatial reference
        first_feature = subgrid_features.features[0]
        actual_sr = first_feature.geometry.get('spatialReference', {'wkid': 4326})
        actual_wkid = actual_sr.get('wkid', 4326)
        
        logger(f"[spray_notifications] Actual geometry spatial reference: WKID {actual_wkid}")
        
        # Determine buffer units and distance based on actual spatial reference
        if actual_wkid == 4326:  # WGS84 - Geographic coordinate system
            # For geographic coordinates, convert feet to approximate degrees
            # This is rough but functional for small areas
            buffer_distance_degrees = buffer_distance * 0.0000305  # Very rough approximation: ~300 feet ≈ 0.00915 degrees
            buffer_distance_final = buffer_distance_degrees
            buffer_unit = 9036  # Degrees
            logger(f"[spray_notifications] Using geographic coordinates (WGS84)")
            logger(f"[spray_notifications] Buffer distance: {buffer_distance} feet ≈ {buffer_distance_degrees:.8f} degrees")
        else:  # Projected coordinate system (3857 or other)
            # For projected coordinates, convert feet to meters
            buffer_distance_meters = buffer_distance * 0.3048
            buffer_distance_final = buffer_distance_meters
            buffer_unit = 9001  # Meters
            logger(f"[spray_notifications] Using projected coordinates (WKID {actual_wkid})")
            logger(f"[spray_notifications] Buffer distance: {buffer_distance} feet = {buffer_distance_meters:.2f} meters")
        
        # Create buffered geometries using the actual spatial reference
        buffered_geometries = []
        
        for i, feature in enumerate(subgrid_features.features):
            logger(f"[spray_notifications] Processing subgrid feature {i+1}/{len(subgrid_features.features)}")
            
            # Get geometry and preserve its original spatial reference
            feature_geom = feature.geometry
            if feature_geom:
                # Ensure geometry has its original spatial reference
                if 'spatialReference' not in feature_geom:
                    feature_geom['spatialReference'] = actual_sr
                
                original_sr = feature_geom['spatialReference']
                logger(f"[spray_notifications] Feature geometry SR: WKID {original_sr.get('wkid', 'Unknown')}")
                
                # Create Geometry object
                geom_obj = Geometry(feature_geom)
                
                # Create buffer using ArcGIS geometry service with correct units
                try:
                    logger(f"[spray_notifications] Creating buffer: {buffer_distance_final} units (unit code: {buffer_unit})")
                    
                    # Use the buffer geometry service with original spatial reference
                    buffered_geom = buffer(
                        geometries=[geom_obj],
                        distances=[buffer_distance_final],
                        unit=buffer_unit,
                        buffer_sr=original_sr,
                        out_sr=original_sr  # Keep same SR as input
                    )[0]
                    
                    logger(f"[spray_notifications] Buffer created successfully")
                    buffered_geometries.append(buffered_geom)
                    
                except Exception as buffer_error:
                    logger(f"[spray_notifications] Buffer error: {buffer_error}")
                    logger(f"[spray_notifications] Using original geometry instead")
                    buffered_geometries.append(geom_obj)
            else:
                logger(f"[spray_notifications] WARNING: No geometry for feature {i+1}")
        
        logger(f"[spray_notifications] Created {len(buffered_geometries)} buffer geometries")
        
        # 4. Get resident notices layer (standalone shapefile)
        logger(f"[spray_notifications] Accessing resident notices layer: {RESIDENT_NOTICES_LAYER_ID}")
        resident_item = gis.content.get(RESIDENT_NOTICES_LAYER_ID)
        if not resident_item:
            raise RuntimeError(f"Could not access resident notices layer: {RESIDENT_NOTICES_LAYER_ID}")
        
        logger(f"[spray_notifications] Resident notices layer: '{resident_item.title}' (Type: {resident_item.type})")
        # Access the standalone layer directly (no sublayer needed)
        resident_layer = FeatureLayer.fromitem(resident_item)
        
        # 5. Query residents within buffered areas using matching spatial reference
        logger(f"[spray_notifications] Querying residents within buffered geometries using consistent spatial reference")
        intersected_residents = []
        
        # Use the same spatial reference as the geometries
        logger(f"[spray_notifications] Using consistent spatial reference: WKID {actual_wkid}")
        
        # First, test total records to confirm connection
        total_residents = resident_layer.query(where="1=1", return_count_only=True)
        logger(f"[spray_notifications] Total residents in layer: {total_residents}")
        
        for i, buffer_geom in enumerate(buffered_geometries):
            logger(f"[spray_notifications] Processing buffer {i+1}/{len(buffered_geometries)}")
            
            try:
                # Import geometry filters (correct way according to ESRI docs)
                from arcgis.geometry.filters import intersects as intersects_filter
                
                # Ensure buffer geometry has consistent spatial reference
                buffer_dict = buffer_geom if isinstance(buffer_geom, dict) else buffer_geom.__geo_interface__
                
                # Ensure spatial reference matches the original
                if 'spatialReference' not in buffer_dict:
                    buffer_dict['spatialReference'] = actual_sr
                
                buffer_sr_wkid = buffer_dict['spatialReference'].get('wkid', actual_wkid)
                logger(f"[spray_notifications] Buffer geometry SR: WKID {buffer_sr_wkid}")
                
                # Create geometry filter using ESRI's approach with matching spatial reference
                geometry_filter = intersects_filter(buffer_dict, sr=actual_wkid)
                
                logger(f"[spray_notifications] Executing spatial query with geometry filter...")
                
                # Execute spatial query
                residents_in_buffer = resident_layer.query(
                    geometry_filter=geometry_filter,
                    out_fields=",".join(desired_fields),
                    return_geometry=False
                )
                
                logger(f"[spray_notifications] Spatial query returned {len(residents_in_buffer.features)} residents")
                
                # Check if we got a reasonable result
                if len(residents_in_buffer.features) == total_residents:
                    logger(f"[spray_notifications] WARNING: Query returned ALL residents - spatial filter may not be working")
                    
                    # Try alternative approach with extent-based query
                    if hasattr(buffer_geom, 'extent'):
                        extent = buffer_geom.extent
                        extent_dict = {
                            "xmin": extent['xmin'],
                            "ymin": extent['ymin'], 
                            "xmax": extent['xmax'],
                            "ymax": extent['ymax'],
                            "spatialReference": actual_sr
                        }
                        
                        logger(f"[spray_notifications] Trying extent-based query with consistent SR")
                        
                        from arcgis.geometry.filters import contains as contains_filter
                        extent_filter = contains_filter(extent_dict, sr=actual_wkid)
                        
                        residents_extent = resident_layer.query(
                            geometry_filter=extent_filter,
                            out_fields=",".join(desired_fields),
                            return_geometry=False
                        )
                        
                        logger(f"[spray_notifications] Extent query returned {len(residents_extent.features)} residents")
                        
                        if len(residents_extent.features) < total_residents:
                            logger(f"[spray_notifications] Using extent-based results")
                            residents_in_buffer = residents_extent
                
                intersected_residents.extend(residents_in_buffer.features)
                logger(f"[spray_notifications] Added {len(residents_in_buffer.features)} residents from buffer {i+1}")
                
            except Exception as query_error:
                logger(f"[spray_notifications] Query error on buffer {i+1}: {str(query_error)}")
                logger(f"[spray_notifications] Error type: {type(query_error)}")
                
                # Fallback to basic geometry query
                try:
                    logger(f"[spray_notifications] Trying fallback spatial query...")
                    residents_fallback = resident_layer.query(
                        geometry_filter=buffer_geom,
                        spatial_rel='intersects',
                        out_fields=",".join(desired_fields),
                        return_geometry=False
                    )
                    logger(f"[spray_notifications] Fallback query returned {len(residents_fallback.features)} residents")
                    intersected_residents.extend(residents_fallback.features)
                    
                except Exception as fallback_error:
                    logger(f"[spray_notifications] Fallback query also failed: {str(fallback_error)}")
                    raise query_error
        
        logger(f"[spray_notifications] Found {len(intersected_residents)} total resident records")
        
        # 6. Convert to DataFrame
        logger(f"[spray_notifications] Converting {len(intersected_residents)} records to DataFrame")
        records = []
        
        for i, feature in enumerate(intersected_residents):
            try:
                record = {}
                for field in desired_fields:
                    record[field] = feature.attributes.get(field, None)
                records.append(record)
                
                if i == 0:  # Log first record for debugging
                    logger(f"[spray_notifications] Sample record fields: {list(record.keys())}")
                    
            except Exception as record_error:
                logger(f"[spray_notifications] Error processing record {i+1}: {str(record_error)}")
                raise record_error
        
        logger(f"[spray_notifications] Successfully processed {len(records)} records")
        df = pd.DataFrame(records)
        logger(f"[spray_notifications] DataFrame created with shape: {df.shape}")
        logger(f"[spray_notifications] DataFrame columns: {list(df.columns)}")
        
        # 7. Remove duplicates based on core identity fields
        dedup_fields = ["TYPE", "NAME", "PHONENUMBE", "Email"]
        available_dedup_fields = [f for f in dedup_fields if f in df.columns]
        
        logger(f"[spray_notifications] Deduplication fields available: {available_dedup_fields}")
        logger(f"[spray_notifications] All DataFrame columns: {list(df.columns)}")
        
        if available_dedup_fields:
            logger(f"[spray_notifications] Deduplicating on fields: {available_dedup_fields}")
            df_dedup = df.drop_duplicates(subset=available_dedup_fields, keep="first")
            logger(f"[spray_notifications] Removed {len(df) - len(df_dedup)} duplicate records")
        else:
            df_dedup = df
            logger("[spray_notifications] No deduplication fields available, keeping all records")
        
        # 8. Generate CSV with timestamp
        today = datetime.today().strftime("%m%d%Y")
        filename = f"Spray_Notifications_{today}.csv"
        
        # 9. Create BytesIO buffer
        buf = BytesIO()
        df_dedup.to_csv(buf, index=False)
        buf.seek(0)
        
        logger(f"[spray_notifications] Successfully generated {filename} with {len(df_dedup)} records")
        
        return {
            "csv_buffer": buf,
            "filename": filename,
            "total_records": len(df_dedup),
            "subgrids_processed": len(subgrid_features.features),
            "buffer_distance": buffer_distance
        }
        
    except Exception as e:
        logger(f"[spray_notifications] Error: {str(e)}")
        raise RuntimeError(f"Spray notifications generation failed: {str(e)}")
