"""
Shapefile Export Module
Handles export of positive samples and associated subgrids as shapefiles for ArcGIS Pro
"""

import os
import tempfile
import zipfile
from datetime import datetime
from io import BytesIO
import json
import time

# Import shapefile library (you may need to install pyshp: pip install pyshp)
try:
    import shapefile
except ImportError:
    print("Warning: pyshp not installed. Install with: pip install pyshp")
    shapefile = None

from arcgis.features import FeatureLayer
from utils import get_layer_from_item, log_request, log_result
from disease_maps import SUBGRID_LAYER_ID

import logging
logger = logging.getLogger(__name__)

def create_points_shapefile(gis, samples, date_range):
    """
    Create a points shapefile from positive samples that replicates the original Pools_2025 layer structure
    
    Args:
        gis: Authenticated ArcGIS GIS object
        samples: List of positive sample dictionaries
        date_range: Dict with start_date and end_date
        
    Returns:
        BytesIO: Zipped shapefile
    """
    if not shapefile:
        raise RuntimeError("pyshp library not available. Install with: pip install pyshp")
        
    log_request("create_points_shapefile", {
        "sample_count": len(samples),
        "date_range": date_range
    })
    
    try:
        # Get the original pools layer to query the actual records with all fields
        from disease_maps import POOLS_LAYER_ID
        from utils import get_layer_from_item
        
        pools_layer, layer_info = get_layer_from_item(gis, POOLS_LAYER_ID)
        
        # Get ObjectIDs from our samples to query the original layer
        object_ids = []
        for sample in samples:
            # Try different possible ObjectID field names
            for obj_field in ['objectId', 'OBJECTID', 'ObjectId', 'FID', 'objectid']:
                obj_id_value = sample.get(obj_field)
                if obj_id_value is not None and obj_id_value != 'Unknown':
                    try:
                        obj_id = int(obj_id_value)
                        if obj_id > 0:  # Only include valid ObjectIDs
                            object_ids.append(obj_id)
                            break  # Found a valid ObjectID, move to next sample
                    except (ValueError, TypeError):
                        continue
        
        # If we still don't have ObjectIDs, fall back to using sample data directly
        if not object_ids:
            logger.warning("No valid ObjectIDs found, using sample data directly")
            return create_points_shapefile_from_samples(gis, samples, date_range)
        
        # Query original layer for these specific records to get all original fields
        object_ids_str = ','.join(map(str, object_ids))
        where_clause = f"OBJECTID IN ({object_ids_str})"
        
        original_features = pools_layer.query(
            where=where_clause,
            out_fields='*',
            return_geometry=True
        )
        
        if not original_features.features:
            raise RuntimeError(f"No features found with ObjectIDs: {object_ids_str}")
        
        # Create temporary directory for shapefile components
        with tempfile.TemporaryDirectory() as temp_dir:
            shapefile_path = os.path.join(temp_dir, "Pools_Pos")
            
            # Create shapefile writer
            w = shapefile.Writer(shapefile_path, shapeType=shapefile.POINT)
            
            # Get field info from original layer and replicate the same structure
            # Only include fields that are commonly found and avoid problematic ones
            original_fields = layer_info.get('fields', [])
            
            # Define fields to include (excluding GlobalID, CreationDate, etc.)
            fields_to_include = [
                'OBJECTID', 'agency_code', 'agency_pool_num', 'surv_year', 'pool_id', 
                'collection_id', 'submission_id', 'submission_num', 'submission_user',
                'code', 'name', 'street', 'city', 'zip', 'region', 'site_code', 
                'site_name', 'site_street', 'site_city', 'site_zip', 'site_region',
                'calculated_neighborhood', 'calculated_neighborhood_distanc', 
                'calculated_city', 'calculated_city_distance', 'calculated_subcounty',
                'calculated_county', 'calculated_state', 'longitude', 'latitude',
                'collection_date', 'disease_week', 'trap_type', 'lure', 'species',
                'sex', 'sex_condition', 'num_count', 'other_sites', 'group_', 
                'comments', 'test_agency', 'WNV', 'SLEV', 'WEEV'
            ]
            
            # Create shapefile fields matching the original layer structure
            for field_name in fields_to_include:
                if field_name in original_fields:
                    if field_name == 'OBJECTID':
                        w.field(field_name, 'N', decimal=0)
                    elif field_name in ['surv_year', 'collection_id', 'submission_id', 'disease_week', 
                                       'sex_condition', 'num_count', 'WNV', 'SLEV', 'WEEV']:
                        w.field(field_name, 'N', decimal=0)
                    elif field_name in ['longitude', 'latitude', 'calculated_neighborhood_distanc', 
                                       'calculated_city_distance']:
                        w.field(field_name, 'N', decimal=6)
                    elif field_name in ['collection_date', 'add_date', 'submission_add_date']:
                        w.field(field_name, 'C', size=50)  # Use text for dates to avoid conversion issues
                    else:
                        # Default to character field with appropriate size
                        field_size = 255 if 'comment' in field_name.lower() else 50
                        w.field(field_name, 'C', size=field_size)
            
            # Add records from original layer query results
            for feature in original_features.features:
                attrs = feature.attributes
                geom = feature.geometry
                
                # Add point geometry - use coordinates from geometry if available, otherwise from attributes
                if geom and 'x' in geom and 'y' in geom:
                    w.point(geom['x'], geom['y'])
                else:
                    # Fall back to longitude/latitude attributes
                    w.point(
                        attrs.get('longitude', 0), 
                        attrs.get('latitude', 0)
                    )
                
                # Build record with all original fields
                record_values = []
                for field_name in fields_to_include:
                    if field_name in original_fields:
                        value = attrs.get(field_name)
                        
                        # Handle different field types
                        if field_name in ['collection_date', 'add_date', 'submission_add_date']:
                            # Convert dates to string to avoid conversion issues
                            if value is not None:
                                try:
                                    if isinstance(value, (int, float)):
                                        # Convert timestamp to string
                                        from datetime import datetime
                                        date_obj = datetime.fromtimestamp(value / 1000) if value > 1000000000000 else datetime.fromtimestamp(value)
                                        record_values.append(date_obj.strftime('%Y-%m-%d'))
                                    else:
                                        record_values.append(str(value)[:50])  # Truncate long strings
                                except Exception as date_error:
                                    logger.warning(f"Date conversion error for {field_name}: {date_error}")
                                    record_values.append('')
                            else:
                                record_values.append('')
                        elif value is None:
                            record_values.append(0 if field_name in ['OBJECTID', 'surv_year', 'collection_id', 
                                                                    'submission_id', 'disease_week', 'sex_condition', 
                                                                    'num_count', 'WNV', 'SLEV', 'WEEV'] else '')
                        else:
                            record_values.append(value)
                
                w.record(*record_values)
            
            # Close the writer explicitly
            try:
                w.close()
            except Exception as close_error:
                logger.warning(f"Error closing points shapefile writer: {close_error}")
            
            # Small delay to ensure files are released
            time.sleep(0.1)
            
            # Generate filename with today's date
            today = datetime.now().strftime("%m%d%Y")
            
            # Create zip file with all shapefile components
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all shapefile components (.shp, .shx, .dbf, .prj)
                for ext in ['.shp', '.shx', '.dbf']:
                    file_path = shapefile_path + ext
                    if os.path.exists(file_path):
                        zipf.write(file_path, f"Pools_Pos_{today}{ext}")
                
                # Add projection file (.prj) for WGS84
                prj_content = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
                zipf.writestr(f"Pools_Pos_{today}.prj", prj_content)
                
                # Add metadata file
                metadata = {
                    "title": "Disease Positive Samples",
                    "description": f"WNV/SLEV/WEEV positive mosquito samples from {date_range.get('start_date')} to {date_range.get('end_date')}",
                    "date_created": datetime.now().isoformat(),
                    "sample_count": len(samples),
                    "coordinate_system": "WGS84 (EPSG:4326)",
                    "note": "This shapefile replicates the original Pools_2025 layer structure for positive samples only",
                    "fields": "Same field structure as original Pools_2025 layer"
                }
                zipf.writestr("metadata.json", json.dumps(metadata, indent=2))
            
            zip_buffer.seek(0)
            log_result("create_points_shapefile", True, f"Created shapefile with {len(samples)} points")
            return zip_buffer
            
    except Exception as e:
        logger.error(f"Error creating points shapefile: {e}")
        raise RuntimeError(f"Failed to create points shapefile: {str(e)}")

def create_points_shapefile_from_samples(gis, samples, date_range):
    """
    Fallback function to create points shapefile directly from sample data
    when ObjectIDs are not available for querying the original layer
    """
    if not shapefile:
        raise RuntimeError("pyshp library not available. Install with: pip install pyshp")
    
    try:
        # Create temporary directory for shapefile components
        with tempfile.TemporaryDirectory() as temp_dir:
            shapefile_path = os.path.join(temp_dir, "Pools_Pos")
            
            # Create shapefile writer
            w = shapefile.Writer(shapefile_path, shapeType=shapefile.POINT)
            
            # Define basic fields from what we have in samples
            w.field('OBJECTID', 'N', decimal=0)
            w.field('POOL_NUM', 'C', size=50)
            w.field('LONGITUDE', 'N', decimal=6)
            w.field('LATITUDE', 'N', decimal=6)
            w.field('COLL_DATE', 'C', size=50)
            w.field('WNV', 'N', decimal=0)
            w.field('SLEV', 'N', decimal=0)
            w.field('WEEV', 'N', decimal=0)
            w.field('DISEASES', 'C', size=50)
            
            # Add records from sample data
            for i, sample in enumerate(samples):
                # Add point geometry
                w.point(sample['x'], sample['y'])
                
                # Create record with available data
                w.record(
                    OBJECTID=i + 1,  # Use sequential ID as fallback
                    POOL_NUM=sample.get('agency_pool_num', ''),
                    LONGITUDE=sample.get('x', 0),
                    LATITUDE=sample.get('y', 0),
                    COLL_DATE=str(sample.get('collection_date', ''))[:50],
                    WNV=1 if sample.get('wnv_positive', False) else 0,
                    SLEV=1 if sample.get('slev_positive', False) else 0,
                    WEEV=1 if sample.get('weev_positive', False) else 0,
                    DISEASES=', '.join(sample.get('diseases', []))
                )
            
            # Close the writer
            w.close()
            
            # Small delay to ensure files are released
            time.sleep(0.1)
            
            # Generate filename with today's date
            today = datetime.now().strftime("%m%d%Y")
            
            # Create zip file with all shapefile components
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all shapefile components (.shp, .shx, .dbf, .prj)
                for ext in ['.shp', '.shx', '.dbf']:
                    file_path = shapefile_path + ext
                    if os.path.exists(file_path):
                        zipf.write(file_path, f"Pools_Pos_{today}{ext}")
                
                # Add projection file (.prj) for WGS84
                prj_content = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
                zipf.writestr(f"Pools_Pos_{today}.prj", prj_content)
                
                # Add metadata file
                metadata = {
                    "title": "Disease Positive Samples",
                    "description": f"WNV/SLEV/WEEV positive mosquito samples from {date_range.get('start_date')} to {date_range.get('end_date')}",
                    "date_created": datetime.now().isoformat(),
                    "sample_count": len(samples),
                    "coordinate_system": "WGS84 (EPSG:4326)",
                    "note": "Fallback shapefile created from sample data (ObjectIDs not available)",
                    "fields": "Basic fields from sample data"
                }
                zipf.writestr("metadata.json", json.dumps(metadata, indent=2))
            
            zip_buffer.seek(0)
            log_result("create_points_shapefile", True, f"Created fallback shapefile with {len(samples)} points")
            return zip_buffer
            
    except Exception as e:
        logger.error(f"Error creating fallback points shapefile: {e}")
        raise RuntimeError(f"Failed to create fallback points shapefile: {str(e)}")

def create_polygons_shapefile(gis, samples, date_range):
    """
    Create a polygons shapefile from subgrids associated with positive samples
    
    Args:
        gis: Authenticated ArcGIS GIS object
        samples: List of positive sample dictionaries
        date_range: Dict with start_date and end_date
        
    Returns:
        BytesIO: Zipped shapefile
    """
    if not shapefile:
        raise RuntimeError("pyshp library not available. Install with: pip install pyshp")
        
    log_request("create_polygons_shapefile", {
        "sample_count": len(samples),
        "date_range": date_range
    })
    
    try:
        # Get unique subgrid labels from samples and associated pool numbers
        subgrid_data = {}
        for sample in samples:
            subgrid_label = sample.get('subgrid_label')
            if subgrid_label and subgrid_label != 'Unknown':
                if subgrid_label not in subgrid_data:
                    subgrid_data[subgrid_label] = {
                        'pool_numbers': [],
                        'diseases': [],
                        'sample_count': 0
                    }
                
                # Add pool number
                pool_num = sample.get('agency_pool_num', '')
                if pool_num and pool_num not in subgrid_data[subgrid_label]['pool_numbers']:
                    subgrid_data[subgrid_label]['pool_numbers'].append(pool_num)
                
                # Add diseases
                for disease in sample.get('diseases', []):
                    if disease not in subgrid_data[subgrid_label]['diseases']:
                        subgrid_data[subgrid_label]['diseases'].append(disease)
                
                subgrid_data[subgrid_label]['sample_count'] += 1
        
        if not subgrid_data:
            raise RuntimeError("No valid subgrid labels found in samples")
        
        subgrid_labels = list(subgrid_data.keys())
        logger.info(f"Exporting {len(subgrid_labels)} unique subgrids: {subgrid_labels}")
        
        # Access subgrid layer
        subgrid_layer, subgrid_layer_info = get_layer_from_item(gis, SUBGRID_LAYER_ID)
        
        # Query subgrids with geometry - get all original fields
        subgrid_where_clause = f"GridLabel IN ({','.join([repr(sg) for sg in subgrid_labels])})"
        subgrid_features = subgrid_layer.query(
            where=subgrid_where_clause,
            out_fields='*',
            return_geometry=True
        )
        
        if not subgrid_features.features:
            raise RuntimeError(f"No subgrid features found for labels: {subgrid_labels}")
        
        logger.info(f"Found {len(subgrid_features.features)} subgrid polygons")
        
        # Create temporary directory for shapefile components
        temp_dir = tempfile.mkdtemp(prefix='subgrids_')
        
        # Create temporary directory for shapefile components
        temp_dir = tempfile.mkdtemp(prefix='subgrids_')
        
        try:
            shapefile_path = os.path.join(temp_dir, "Subgrids_Pos")
            
            # Create shapefile writer
            w = shapefile.Writer(shapefile_path, shapeType=shapefile.POLYGON)
            
            # Use a simplified, reliable field structure to avoid type mismatches
            w.field('OBJECTID', 'N', decimal=0)
            w.field('GRIDLABEL', 'C', size=20)
            w.field('TRS', 'C', size=20)
            w.field('DEPOT', 'C', size=20)
            w.field('SPLIT_POP', 'C', size=10)
            w.field('STATUS', 'C', size=20)
            w.field('POS_POOLS', 'C', size=200)  # Pool numbers from positive samples
            
            # Process each subgrid feature
            for feature in subgrid_features.features:
                attrs = feature.attributes
                geom = feature.geometry
                
                if not geom:
                    logger.warning(f"No geometry for subgrid {attrs.get('GridLabel')}")
                    continue
                
                grid_label = attrs.get('GridLabel')
                
                # Convert ArcGIS geometry to shapefile polygon format
                try:
                    if 'rings' in geom:
                        # ArcGIS Polygon format with rings
                        rings = geom['rings']
                        if rings and len(rings) > 0:
                            # Convert coordinates - ensure proper format for pyshp
                            polygon_parts = []
                            for ring in rings:
                                if len(ring) >= 4:  # Valid ring needs at least 4 points (first=last)
                                    # Convert each coordinate pair to [x, y] format
                                    converted_ring = []
                                    for coord in ring:
                                        if len(coord) >= 2:  # Ensure we have x, y coordinates
                                            converted_ring.append([float(coord[0]), float(coord[1])])
                                    
                                    # Ensure ring is closed (first point = last point)
                                    if len(converted_ring) >= 4:
                                        if converted_ring[0] != converted_ring[-1]:
                                            converted_ring.append(converted_ring[0])
                                        polygon_parts.append(converted_ring)
                            
                            if polygon_parts:
                                # Add polygon to shapefile
                                w.poly(polygon_parts)
                                logger.debug(f"Added polygon for {grid_label} with {len(polygon_parts)} rings")
                            else:
                                logger.warning(f"No valid rings for subgrid {grid_label}")
                                continue
                        else:
                            logger.warning(f"Empty rings for subgrid {grid_label}")
                            continue
                    else:
                        logger.warning(f"No 'rings' in geometry for subgrid {grid_label}: {list(geom.keys())}")
                        continue
                    
                    # Create a simple, reliable record
                    try:
                        objectid = int(attrs.get('OBJECTID', attrs.get('ObjectId', attrs.get('FID', 0))))
                    except (ValueError, TypeError):
                        objectid = 0
                    
                    # Pool numbers from positive samples
                    pool_numbers_str = ', '.join(subgrid_data.get(grid_label, {}).get('pool_numbers', []))
                    
                    # Add record with simple string/numeric values
                    w.record(
                        OBJECTID=objectid,
                        GRIDLABEL=str(grid_label or ''),
                        TRS=str(attrs.get('TRS', '')),
                        DEPOT=str(attrs.get('Depot', '')),
                        SPLIT_POP=str(attrs.get('split_pop', '')),
                        STATUS=str(attrs.get('Status', '')),
                        POS_POOLS=pool_numbers_str[:200]
                    )
                    
                except Exception as record_error:
                    logger.warning(f"Error creating record for {grid_label}: {record_error}")
                    # Still add the geometry but with minimal record to avoid shape/record mismatch
                    w.record(
                        OBJECTID=0,
                        GRIDLABEL=str(grid_label or ''),
                        TRS='',
                        DEPOT='',
                        SPLIT_POP='',
                        STATUS='',
                        POS_POOLS=''
                    )
                    continue
            
            # Close the writer explicitly before creating zip file
            try:
                w.close()
                logger.info("Shapefile writer closed successfully")
            except Exception as close_error:
                logger.warning(f"Error closing polygons shapefile writer: {close_error}")
            
            # Set writer to None to ensure it's properly cleaned up
            w = None
            
            # Small delay to ensure files are properly closed and released
            time.sleep(1.0)  # Longer delay for Windows file locking issues
            
            # Generate filename with today's date
            today = datetime.now().strftime("%m%d%Y")
            
            # Create zip file with all shapefile components
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all shapefile components
                for ext in ['.shp', '.shx', '.dbf']:
                    file_path = shapefile_path + ext
                    if os.path.exists(file_path):
                        zipf.write(file_path, f"Subgrids_Pos_{today}{ext}")
                
                # Add projection file (.prj) for WGS84
                prj_content = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
                zipf.writestr(f"Subgrids_Pos_{today}.prj", prj_content)
                
                # Add metadata file
                metadata = {
                    "title": "Associated Subgrids",
                    "description": f"Subgrid polygons containing disease positive samples from {date_range.get('start_date')} to {date_range.get('end_date')}",
                    "date_created": datetime.now().isoformat(),
                    "subgrid_count": len(subgrid_features.features),
                    "unique_subgrids": subgrid_labels,
                    "coordinate_system": "WGS84 (EPSG:4326)",
                    "note": "This shapefile replicates the original Subgrid_2025 layer structure with an additional POS_POOLS field containing pool numbers from positive samples",
                    "fields": {
                        "Original fields": "Same as Subgrid_2025 layer",
                        "POS_POOLS": "Pool numbers from positive disease samples in this subgrid (comma-separated)"
                    }
                }
                zipf.writestr("metadata.json", json.dumps(metadata, indent=2))
            
            zip_buffer.seek(0)
            log_result("create_polygons_shapefile", True, f"Created shapefile with {len(subgrid_features.features)} polygons")
            return zip_buffer
            
        finally:
            # Clean up temporary directory
            try:
                import shutil
                if os.path.exists(temp_dir):
                    # Force close any remaining file handles
                    time.sleep(0.5)
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as cleanup_error:
                logger.warning(f"Error cleaning up temp directory: {cleanup_error}")
            
    except Exception as e:
        logger.error(f"Error creating polygons shapefile: {e}")
        raise RuntimeError(f"Failed to create polygons shapefile: {str(e)}")
