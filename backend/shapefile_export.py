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
    Create a points shapefile from positive samples
    
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
        # Create temporary directory for shapefile components
        with tempfile.TemporaryDirectory() as temp_dir:
            shapefile_path = os.path.join(temp_dir, "positive_samples")
            
            # Create shapefile writer
            w = shapefile.Writer(shapefile_path, shapeType=shapefile.POINT)
            
            # Define fields
            w.field('POOL_ID', 'C', size=50)
            w.field('OBJECTID', 'C', size=20)  # Changed to Character to handle 'Unknown'
            w.field('SUBGRID', 'C', size=20)
            w.field('LONGITUDE', 'N', decimal=6)
            w.field('LATITUDE', 'N', decimal=6)
            w.field('COLL_DATE', 'C', size=20)
            w.field('ADD_DATE', 'C', size=20)
            w.field('WNV', 'C', size=1)  # Y/N
            w.field('SLEV', 'C', size=1)  # Y/N
            w.field('WEEV', 'C', size=1)  # Y/N
            w.field('DISEASES', 'C', size=50)
            
            # Add records
            for sample in samples:
                # Add point geometry
                w.point(sample['x'], sample['y'])
                
                # Add attributes with safe conversion
                objectid_value = sample.get('objectId', 0)
                if isinstance(objectid_value, str) and objectid_value == 'Unknown':
                    objectid_str = 'Unknown'
                else:
                    objectid_str = str(objectid_value)
                
                w.record(
                    POOL_ID=sample.get('agency_pool_num', str(sample.get('objectId', ''))),
                    OBJECTID=objectid_str,  # Use string version
                    SUBGRID=sample.get('subgrid_label', 'Unknown'),
                    LONGITUDE=sample.get('x', 0),
                    LATITUDE=sample.get('y', 0),
                    COLL_DATE=sample.get('collection_date', ''),
                    ADD_DATE=sample.get('add_date', ''),
                    WNV='Y' if sample.get('wnv_positive', False) else 'N',
                    SLEV='Y' if sample.get('slev_positive', False) else 'N',
                    WEEV='Y' if sample.get('weev_positive', False) else 'N',
                    DISEASES=', '.join(sample.get('diseases', []))
                )
            
            # Close the writer explicitly
            try:
                w.close()
            except Exception as close_error:
                logger.warning(f"Error closing points shapefile writer: {close_error}")
            
            # Small delay to ensure files are released
            import time
            time.sleep(0.1)
            
            # Create zip file with all shapefile components
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all shapefile components (.shp, .shx, .dbf, .prj)
                for ext in ['.shp', '.shx', '.dbf']:
                    file_path = shapefile_path + ext
                    if os.path.exists(file_path):
                        zipf.write(file_path, f"positive_samples{ext}")
                
                # Add projection file (.prj) for WGS84
                prj_content = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
                zipf.writestr("positive_samples.prj", prj_content)
                
                # Add metadata file
                metadata = {
                    "title": "Disease Positive Samples",
                    "description": f"WNV/SLEV/WEEV positive mosquito samples from {date_range.get('start_date')} to {date_range.get('end_date')}",
                    "date_created": datetime.now().isoformat(),
                    "sample_count": len(samples),
                    "coordinate_system": "WGS84 (EPSG:4326)",
                    "fields": {
                        "POOL_ID": "Pool identification number",
                        "OBJECTID": "Feature object ID",
                        "SUBGRID": "Associated subgrid label",
                        "LONGITUDE": "Longitude coordinate",
                        "LATITUDE": "Latitude coordinate",
                        "COLL_DATE": "Collection date",
                        "ADD_DATE": "Date added to system",
                        "WNV": "West Nile Virus positive (Y/N)",
                        "SLEV": "St. Louis Encephalitis Virus positive (Y/N)",
                        "WEEV": "Western Equine Encephalitis Virus positive (Y/N)",
                        "DISEASES": "List of diseases detected"
                    }
                }
                zipf.writestr("metadata.json", json.dumps(metadata, indent=2))
            
            zip_buffer.seek(0)
            log_result("create_points_shapefile", True, f"Created shapefile with {len(samples)} points")
            return zip_buffer
            
    except Exception as e:
        logger.error(f"Error creating points shapefile: {e}")
        raise RuntimeError(f"Failed to create points shapefile: {str(e)}")

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
        # Get unique subgrid labels from samples
        subgrid_labels = list(set([
            sample.get('subgrid_label') 
            for sample in samples 
            if sample.get('subgrid_label') and sample.get('subgrid_label') != 'Unknown'
        ]))
        
        if not subgrid_labels:
            raise RuntimeError("No valid subgrid labels found in samples")
        
        logger.info(f"Exporting {len(subgrid_labels)} unique subgrids: {subgrid_labels}")
        
        # Access subgrid layer
        subgrid_layer, _ = get_layer_from_item(gis, SUBGRID_LAYER_ID)
        
        # Query subgrids
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
        with tempfile.TemporaryDirectory() as temp_dir:
            shapefile_path = os.path.join(temp_dir, "associated_subgrids")
            
            # Create shapefile writer
            w = shapefile.Writer(shapefile_path, shapeType=shapefile.POLYGON)
            
            # Define fields (based on subgrid layer attributes)
            w.field('GRIDLABEL', 'C', size=20)
            w.field('OBJECTID', 'C', size=20)  # Changed to Character
            w.field('POS_COUNT', 'N', decimal=0)  # Count of positive samples in this subgrid
            w.field('DISEASES', 'C', size=100)    # Diseases found in this subgrid
            w.field('DATE_RANGE', 'C', size=50)   # Date range of analysis
            
            # Process each subgrid feature
            for feature in subgrid_features.features:
                attrs = feature.attributes
                geom = feature.geometry
                
                if not geom:
                    logger.warning(f"No geometry for subgrid {attrs.get('GridLabel')}")
                    continue
                
                grid_label = attrs.get('GridLabel')
                
                # Count positive samples and diseases in this subgrid
                subgrid_samples = [s for s in samples if s.get('subgrid_label') == grid_label]
                pos_count = len(subgrid_samples)
                diseases_in_subgrid = list(set([
                    disease 
                    for sample in subgrid_samples 
                    for disease in sample.get('diseases', [])
                ]))
                
                # Convert geometry to shapefile format
                try:
                    # Handle different geometry formats from ArcGIS API
                    if hasattr(geom, 'type'):
                        geom_type = geom.type
                    elif isinstance(geom, dict) and 'type' in geom:
                        geom_type = geom['type']
                    elif isinstance(geom, dict) and 'rings' in geom:
                        # This is an ArcGIS Polygon format
                        geom_type = 'Polygon'
                    else:
                        logger.warning(f"Unknown geometry format for {grid_label}: {type(geom)}")
                        continue
                    
                    if geom_type == 'Polygon' or (isinstance(geom, dict) and 'rings' in geom):
                        # Handle ArcGIS polygon geometry format
                        rings = geom.get('rings', [])
                        if not rings:
                            logger.warning(f"No rings in polygon geometry for {grid_label}")
                            continue
                            
                        exterior_ring = rings[0] if rings else []
                        holes = rings[1:] if len(rings) > 1 else []
                        
                        # Add polygon (exterior ring first, then holes)
                        w.poly([exterior_ring] + holes)
                        
                    elif geom_type == 'MultiPolygon':
                        # Handle multipolygon geometry - take the first polygon
                        if isinstance(geom, dict) and geom.get('coordinates'):
                            if geom['coordinates'] and geom['coordinates'][0]:
                                exterior_ring = geom['coordinates'][0][0]
                                holes = geom['coordinates'][0][1:] if len(geom['coordinates'][0]) > 1 else []
                                w.poly([exterior_ring] + holes)
                            else:
                                logger.warning(f"Invalid MultiPolygon geometry for {grid_label}")
                                continue
                        else:
                            logger.warning(f"Invalid MultiPolygon format for {grid_label}")
                            continue
                    else:
                        logger.warning(f"Unsupported geometry type {geom_type} for {grid_label}")
                        continue
                        
                except Exception as geom_error:
                    logger.warning(f"Error processing geometry for {grid_label}: {geom_error}")
                    continue
                
                # Add attributes with safe conversion
                objectid_value = attrs.get('OBJECTID', 0)
                objectid_str = str(objectid_value) if objectid_value is not None else '0'
                
                w.record(
                    GRIDLABEL=grid_label or 'Unknown',
                    OBJECTID=objectid_str,  # Use string version
                    POS_COUNT=pos_count,
                    DISEASES=', '.join(diseases_in_subgrid),
                    DATE_RANGE=f"{date_range.get('start_date')} to {date_range.get('end_date')}"
                )
            
            # Close the writer explicitly
            try:
                w.close()
            except Exception as close_error:
                logger.warning(f"Error closing polygons shapefile writer: {close_error}")
            
            # Small delay to ensure files are released
            import time
            time.sleep(0.1)
            
            # Create zip file with all shapefile components
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all shapefile components
                for ext in ['.shp', '.shx', '.dbf']:
                    file_path = shapefile_path + ext
                    if os.path.exists(file_path):
                        zipf.write(file_path, f"associated_subgrids{ext}")
                
                # Add projection file (.prj) for WGS84
                prj_content = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
                zipf.writestr("associated_subgrids.prj", prj_content)
                
                # Add metadata file
                metadata = {
                    "title": "Associated Subgrids",
                    "description": f"Subgrid polygons containing disease positive samples from {date_range.get('start_date')} to {date_range.get('end_date')}",
                    "date_created": datetime.now().isoformat(),
                    "subgrid_count": len(subgrid_features.features),
                    "unique_subgrids": subgrid_labels,
                    "coordinate_system": "WGS84 (EPSG:4326)",
                    "fields": {
                        "GRIDLABEL": "Subgrid identification label",
                        "OBJECTID": "Feature object ID",
                        "POS_COUNT": "Number of positive samples in this subgrid",
                        "DISEASES": "List of diseases detected in this subgrid",
                        "DATE_RANGE": "Date range of analysis"
                    }
                }
                zipf.writestr("metadata.json", json.dumps(metadata, indent=2))
            
            zip_buffer.seek(0)
            log_result("create_polygons_shapefile", True, f"Created shapefile with {len(subgrid_features.features)} polygons")
            return zip_buffer
            
    except Exception as e:
        logger.error(f"Error creating polygons shapefile: {e}")
        raise RuntimeError(f"Failed to create polygons shapefile: {str(e)}")
