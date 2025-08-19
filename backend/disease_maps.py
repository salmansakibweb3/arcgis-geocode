"""
Disease Map Generation Module
Handles analysis of disease positive samples and automated map creation for CMAD
"""

from datetime import datetime
from arcgis.features import FeatureLayerCollection, FeatureLayer
import logging
from utils import get_layer_from_item, build_date_range_query, log_request, log_result

# For now, disable WebMap functionality until we resolve the import issue
WebMap = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration constants
POOLS_LAYER_ID = "d2a9cfa0aa4e4b0e8a2c30da319957fe"

# Layer IDs for map generation
SUBGRID_LAYER_ID = "e8656893998e497fa8161f87d053a725"  # From your existing spray notifications
STREETS_LAYER_ID = "66d53bd3197a40ab8e7cbc480dccd326"  # Streets layer
PARCELS_LAYER_ID = "a79412466ab2401fa21f1728ac116a87"  # Land parcels layer
TRS_LAYER_ID = "2531b1151ebd4cb9b90ef91b33811d0b"      # TRS zones layer

def get_pools_layer(gis):
    """
    Get the pools layer from ArcGIS Online
    
    Args:
        gis: Authenticated ArcGIS GIS object
        
    Returns:
        FeatureLayer: The pools feature layer
        dict: Layer information
    """
    try:
        pools_layer, layer_info = get_layer_from_item(gis, POOLS_LAYER_ID)
        logger.info(f"Available fields: {layer_info['fields']}")
        return pools_layer, layer_info
        
    except Exception as e:
        logger.error(f"Error accessing pools layer: {e}")
        raise RuntimeError(f"Failed to access pools layer: {str(e)}")

def identify_disease_fields(field_names):
    """
    Identify disease-related fields in the pools layer
    
    Args:
        field_names: List of field names from the layer
        
    Returns:
        dict: Mapping of disease types to field names
    """
    disease_field_patterns = {
        'WNV': ['wnv', 'WNV', 'west_nile', 'West_Nile', 'WEST_NILE'],
        'SLEV': ['slev', 'SLEV', 'st_louis', 'St_Louis', 'ST_LOUIS'],
        'WEEV': ['weev', 'WEEV', 'western_equine', 'Western_Equine', 'WESTERN_EQUINE']
    }
    
    found_disease_fields = {}
    for disease, patterns in disease_field_patterns.items():
        for pattern in patterns:
            if pattern in field_names:
                found_disease_fields[disease] = pattern
                break
    
    logger.info(f"Found disease fields: {found_disease_fields}")
    return found_disease_fields

def identify_date_fields(field_names):
    """
    Identify date-related fields in the pools layer
    
    Args:
        field_names: List of field names from the layer
        
    Returns:
        list: Available date fields
    """
    date_field_candidates = [
        'add_date', 'Add_Date', 'ADD_DATE',
        'collection_date', 'Collection_Date', 'COLLECTION_DATE',
        'date_added', 'Date_Added', 'DATE_ADDED',
        'sample_date', 'Sample_Date', 'SAMPLE_DATE'
    ]
    
    existing_date_fields = [field for field in date_field_candidates if field in field_names]
    logger.info(f"Found date fields: {existing_date_fields}")
    return existing_date_fields

def find_subgrid_for_point(subgrid_layer, longitude, latitude):
    """
    Find the subgrid that contains a given point
    
    Args:
        subgrid_layer: The subgrid feature layer
        longitude: Point longitude
        latitude: Point latitude
        
    Returns:
        str: GridLabel of the containing subgrid, or None if not found
    """
    try:
        if not subgrid_layer:
            return None
            
        # Create point geometry for spatial query
        point_geometry = {
            "x": longitude,
            "y": latitude,
            "spatialReference": {"wkid": 4326}  # WGS84
        }
        
        # Find intersecting subgrids
        intersecting_subgrids = subgrid_layer.query(
            geometry_filter={
                'geometry': point_geometry,
                'geometryType': 'esriGeometryPoint',
                'spatialRel': 'esriSpatialRelIntersects'
            },
            out_fields='GridLabel',
            return_geometry=False,
            result_record_count=1  # Only need the first match
        )
        
        if intersecting_subgrids.features:
            grid_label = intersecting_subgrids.features[0].attributes.get('GridLabel')
            return grid_label
        else:
            return None
            
    except Exception as e:
        logger.warning(f"Error finding subgrid for point {longitude}, {latitude}: {e}")
        return None

def analyze_disease_positives(gis, start_date, end_date, date_field='add_date'):
    """
    Analyze disease positive samples within a date range
    
    Args:
        gis: Authenticated ArcGIS GIS object
        start_date: Start date (YYYY-MM-DD format)
        end_date: End date (YYYY-MM-DD format)
        date_field: Field name to use for date filtering
        
    Returns:
        dict: Analysis results including positive samples and metadata
    """
    log_request("analyze_disease_positives", {
        "start_date": start_date,
        "end_date": end_date,
        "date_field": date_field
    })
    
    try:
        # Get the pools layer
        pools_layer, layer_info = get_pools_layer(gis)
        
        # Identify disease and date fields
        disease_fields = identify_disease_fields(layer_info["fields"])
        date_fields = identify_date_fields(layer_info["fields"])
        
        if not disease_fields:
            raise RuntimeError("No disease fields found in the pools layer")
        
        if date_field not in layer_info["fields"]:
            raise RuntimeError(f"Date field '{date_field}' not found. Available date fields: {date_fields}")
        
        # Build date filter query using utility
        date_where = build_date_range_query(start_date, end_date, date_field)
        logger.info(f"Date WHERE clause: {date_where}")
        
        # Query samples within date range
        try:
            all_samples = pools_layer.query(
                where=date_where,
                out_fields='*',
                return_geometry=True,
                result_record_count=1000  # Adjust as needed
            )
            
            logger.info(f"Found {len(all_samples.features)} samples in date range")
            
        except Exception as query_error:
            logger.error(f"Error querying samples: {query_error}")
            # Test if layer is accessible
            try:
                test_count = pools_layer.query(where="1=1", return_count_only=True)
                logger.info(f"Layer is accessible with {test_count} total records")
                raise RuntimeError(f"Date query failed. Check date field '{date_field}'. Available fields: {', '.join(layer_info['fields'])}")
            except:
                raise RuntimeError(f"Layer query error: {str(query_error)}")
        
        # Process samples and identify positives
        positive_samples = []
        
        # Get subgrid layer for spatial queries
        try:
            subgrid_layer, subgrid_info = get_layer_from_item(gis, SUBGRID_LAYER_ID)
            logger.info(f"Subgrid layer accessed: {subgrid_info['title']}")
        except Exception as e:
            logger.warning(f"Could not access subgrid layer: {e}")
            subgrid_layer = None
        
        for feature in all_samples.features:
            attrs = feature.attributes
            geometry = feature.geometry
            
            # Check for positive results (1 = positive, 0 = negative)
            diseases_positive = []
            for disease, field_name in disease_fields.items():
                if attrs.get(field_name) == 1:
                    diseases_positive.append(disease)
            
            # If any disease is positive, add to results
            if diseases_positive:
                # Use latitude and longitude fields directly from attributes
                longitude = attrs.get('longitude')
                latitude = attrs.get('latitude')
                
                # Skip if no valid coordinates
                if longitude is None or latitude is None:
                    continue
                
                # Find which subgrid this point falls in
                subgrid_label = find_subgrid_for_point(subgrid_layer, longitude, latitude)
                
                positive_samples.append({
                    'objectId': attrs.get('OBJECTID', attrs.get('objectid', attrs.get('FID', 'Unknown'))),
                    'agency_pool_num': attrs.get('agency_pool_num', attrs.get('Agency_Pool_Num', 'Unknown')),
                    'x': longitude,
                    'y': latitude,
                    'subgrid_label': subgrid_label or 'Unknown',
                    'collection_date': attrs.get('collection_date', attrs.get('Collection_Date', 'Unknown')),
                    'add_date': attrs.get('add_date', attrs.get('Add_Date', 'Unknown')),
                    'wnv_positive': 'WNV' in diseases_positive,
                    'slev_positive': 'SLEV' in diseases_positive,
                    'weev_positive': 'WEEV' in diseases_positive,
                    'diseases': diseases_positive
                })
        
        logger.info(f"Identified {len(positive_samples)} positive samples")
        
        # Return comprehensive results
        result = {
            "status": "success",
            "message": f"Analysis completed for {layer_info['title']}",
            "total_samples": len(all_samples.features),
            "positive_samples": len(positive_samples),
            "samples": positive_samples,
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            },
            "layer_info": {
                "title": layer_info["title"],
                "feature_count": layer_info["total_features"],
                "fields": layer_info["fields"],
                "found_date_fields": date_fields,
                "found_disease_fields": disease_fields
            }
        }
        
        log_result("analyze_disease_positives", True, f"{len(positive_samples)} positives found")
        return result
        
    except Exception as e:
        logger.error(f"Disease analysis failed: {e}")
        log_result("analyze_disease_positives", False, str(e))
        raise RuntimeError(f"Analysis failed: {str(e)}")

def validate_map_layers(gis):
    """
    Validate that all required layers for map generation are accessible
    
    Args:
        gis: Authenticated ArcGIS GIS object
        
    Returns:
        dict: Validation results for all layers
    """
    from utils import validate_layer_access
    
    layer_configs = {
        "pools": POOLS_LAYER_ID,
        "subgrids": SUBGRID_LAYER_ID,
        "streets": STREETS_LAYER_ID,
        "parcels": PARCELS_LAYER_ID,
        "trs_zones": TRS_LAYER_ID
    }
    
    validation_results = {
        "all_accessible": True,
        "layers": {},
        "summary": {}
    }
    
    for layer_name, layer_id in layer_configs.items():
        logger.info(f"Validating {layer_name} layer: {layer_id}")
        result = validate_layer_access(gis, layer_id)
        validation_results["layers"][layer_name] = result
        
        if not result["accessible"]:
            validation_results["all_accessible"] = False
            logger.error(f"{layer_name} layer validation failed: {result['message']}")
        else:
            logger.info(f"{layer_name} layer validated successfully")
    
    # Create summary
    accessible_count = sum(1 for r in validation_results["layers"].values() if r["accessible"])
    total_layers = len(layer_configs)
    
    validation_results["summary"] = {
        "accessible_layers": accessible_count,
        "total_layers": total_layers,
        "ready_for_map_generation": validation_results["all_accessible"]
    }
    
    return validation_results

def find_affected_subgrids(gis, positive_samples):
    """
    Find subgrids that contain disease positive samples
    
    Args:
        gis: Authenticated ArcGIS GIS object
        positive_samples: List of positive sample dictionaries with coordinates
        
    Returns:
        dict: Subgrid information with associated positive samples
    """
    logger.info("Finding affected subgrids for positive samples")
    
    try:
        # Access subgrid layer using utility function
        from utils import get_layer_from_item
        subgrid_layer, subgrid_info = get_layer_from_item(gis, SUBGRID_LAYER_ID)
        
        affected_subgrids = []
        
        for sample in positive_samples:
            # Create point geometry for spatial query
            point_geometry = {
                "x": sample["x"],
                "y": sample["y"],
                "spatialReference": {"wkid": 4326}  # Assuming WGS84, adjust if needed
            }
            
            # Find intersecting subgrids
            intersecting_subgrids = subgrid_layer.query(
                geometry_filter={
                    'geometry': point_geometry,
                    'spatialRel': 'esriSpatialRelIntersects'
                },
                out_fields='GridLabel,OBJECTID',
                return_geometry=True
            )
            
            for subgrid in intersecting_subgrids.features:
                grid_label = subgrid.attributes.get('GridLabel')
                if grid_label:
                    # Check if we already have this subgrid
                    existing_subgrid = next((sg for sg in affected_subgrids if sg['grid_label'] == grid_label), None)
                    
                    if not existing_subgrid:
                        affected_subgrids.append({
                            'grid_label': grid_label,
                            'geometry': subgrid.geometry,
                            'positive_samples': [sample]
                        })
                    else:
                        existing_subgrid['positive_samples'].append(sample)
        
        logger.info(f"Found {len(affected_subgrids)} affected subgrids")
        return affected_subgrids
        
    except Exception as e:
        logger.error(f"Error finding affected subgrids: {e}")
        raise RuntimeError(f"Failed to find affected subgrids: {str(e)}")
    """
    Find subgrids that contain disease positive samples
    
    Args:
        gis: Authenticated ArcGIS GIS object
        positive_samples: List of positive sample dictionaries with coordinates
        
    Returns:
        dict: Subgrid information with associated positive samples
    """
    logger.info("Finding affected subgrids for positive samples")
    
    try:
        # Access subgrid layer
        subgrid_item = gis.content.get(SUBGRID_LAYER_ID)
        if not subgrid_item:
            raise RuntimeError(f"Subgrid layer {SUBGRID_LAYER_ID} not found")
        
        subgrid_layer = FeatureLayerCollection.fromitem(subgrid_item).layers[0]
        
        affected_subgrids = []
        
        for sample in positive_samples:
            # Create point geometry for spatial query
            point_geometry = {
                "x": sample["x"],
                "y": sample["y"],
                "spatialReference": {"wkid": 4326}  # Assuming WGS84, adjust if needed
            }
            
            # Find intersecting subgrids
            intersecting_subgrids = subgrid_layer.query(
                geometry_filter={
                    'geometry': point_geometry,
                    'spatialRel': 'esriSpatialRelIntersects'
                },
                out_fields='GridLabel,OBJECTID',
                return_geometry=True
            )
            
            for subgrid in intersecting_subgrids.features:
                grid_label = subgrid.attributes.get('GridLabel')
                if grid_label:
                    # Check if we already have this subgrid
                    existing_subgrid = next((sg for sg in affected_subgrids if sg['grid_label'] == grid_label), None)
                    
                    if not existing_subgrid:
                        affected_subgrids.append({
                            'grid_label': grid_label,
                            'geometry': subgrid.geometry,
                            'positive_samples': [sample]
                        })
                    else:
                        existing_subgrid['positive_samples'].append(sample)
        
        logger.info(f"Found {len(affected_subgrids)} affected subgrids")
        return affected_subgrids
        
    except Exception as e:
        logger.error(f"Error finding affected subgrids: {e}")
        raise RuntimeError(f"Failed to find affected subgrids: {str(e)}")

def generate_disease_maps(gis, positive_samples, export_format="webmap", buffer_factor=1.2):
    """
    Generate individual maps for each subgrid containing disease positives
    
    Args:
        gis: Authenticated ArcGIS GIS object
        positive_samples: List of positive sample dictionaries
        export_format: Format for map output ("webmap" or "pdf")
        buffer_factor: Buffer factor for map extent (1.2 = 20% buffer)
        
    Returns:
        dict: Map generation results
    """
    logger.info("Starting automated map generation")
    
    try:
        # Validate all layers are accessible
        validation = validate_map_layers(gis)
        if not validation["all_accessible"]:
            failed_layers = [name for name, result in validation["layers"].items() if not result["accessible"]]
            raise RuntimeError(f"Required layers not accessible: {', '.join(failed_layers)}")
        
        # Find affected subgrids
        affected_subgrids = find_affected_subgrids(gis, positive_samples)
        
        if not affected_subgrids:
            return {
                "status": "success",
                "message": "No affected subgrids found",
                "maps_created": 0,
                "affected_subgrids": 0,
                "maps": []
            }
        
        # Check if WebMap is available
        if WebMap is None:
            logger.warning("WebMap not available, using alternative approach")
            return generate_maps_alternative_approach(gis, affected_subgrids, positive_samples)
        
        # Access all required layers
        from utils import get_layer_from_item
        
        pools_layer, _ = get_layer_from_item(gis, POOLS_LAYER_ID)
        subgrid_layer, _ = get_layer_from_item(gis, SUBGRID_LAYER_ID)
        streets_layer, _ = get_layer_from_item(gis, STREETS_LAYER_ID)
        parcels_layer, _ = get_layer_from_item(gis, PARCELS_LAYER_ID)
        trs_layer, _ = get_layer_from_item(gis, TRS_LAYER_ID)
        
        generated_maps = []
        
        for i, subgrid_info in enumerate(affected_subgrids):
            logger.info(f"Creating map {i+1}/{len(affected_subgrids)} for grid {subgrid_info['grid_label']}")
            
            try:
                # Create web map
                disease_map = WebMap(gis)
                
                # Add all layers to the map
                disease_map.add_layer(parcels_layer)  # Add parcels first (background)
                disease_map.add_layer(streets_layer)  # Add streets
                disease_map.add_layer(trs_layer)      # Add TRS zones
                disease_map.add_layer(subgrid_layer)  # Add subgrids
                disease_map.add_layer(pools_layer)    # Add pools (disease points on top)
                
                # Calculate extent for this subgrid
                subgrid_extent = subgrid_info['geometry']
                if 'extent' in subgrid_extent:
                    extent_info = subgrid_extent['extent']
                else:
                    # Calculate extent from geometry rings if needed
                    rings = subgrid_extent.get('rings', [[]])
                    if rings and rings[0]:
                        x_coords = [point[0] for point in rings[0]]
                        y_coords = [point[1] for point in rings[0]]
                        extent_info = {
                            'xmin': min(x_coords),
                            'ymin': min(y_coords),
                            'xmax': max(x_coords),
                            'ymax': max(y_coords),
                            'spatialReference': subgrid_extent.get('spatialReference', {'wkid': 4326})
                        }
                
                # Add buffer to extent
                width = extent_info['xmax'] - extent_info['xmin']
                height = extent_info['ymax'] - extent_info['ymin']
                
                buffered_extent = {
                    'xmin': extent_info['xmin'] - (width * (buffer_factor - 1) / 2),
                    'ymin': extent_info['ymin'] - (height * (buffer_factor - 1) / 2),
                    'xmax': extent_info['xmax'] + (width * (buffer_factor - 1) / 2),
                    'ymax': extent_info['ymax'] + (height * (buffer_factor - 1) / 2),
                    'spatialReference': extent_info['spatialReference']
                }
                
                disease_map.extent = buffered_extent
                
                # Create map title and metadata
                today = datetime.now().strftime('%Y-%m-%d')
                positive_count = len(subgrid_info['positive_samples'])
                diseases_found = set()
                for sample in subgrid_info['positive_samples']:
                    diseases_found.update(sample['diseases'])
                diseases_str = ', '.join(sorted(diseases_found))
                
                map_title = f"Disease Positive Map - Grid {subgrid_info['grid_label']} - {today}"
                map_snippet = f"Grid {subgrid_info['grid_label']} contains {positive_count} disease positive(s): {diseases_str}"
                
                # Save the web map
                saved_map = disease_map.save({
                    'title': map_title,
                    'snippet': map_snippet,
                    'tags': ['disease-monitoring', 'automated', f'grid-{subgrid_info["grid_label"]}', today, 'cmad']
                })
                
                generated_maps.append({
                    'grid_label': subgrid_info['grid_label'],
                    'map_item': saved_map,
                    'map_id': saved_map.id,
                    'positive_count': positive_count,
                    'diseases': list(diseases_found),
                    'map_url': f"https://www.arcgis.com/home/webmap/viewer.html?webmap={saved_map.id}",
                    'map_created': True
                })
                
                logger.info(f"Created web map for grid {subgrid_info['grid_label']}: {saved_map.title}")
                
            except Exception as map_error:
                logger.error(f"Error creating map for grid {subgrid_info['grid_label']}: {map_error}")
                generated_maps.append({
                    'grid_label': subgrid_info['grid_label'],
                    'positive_count': len(subgrid_info['positive_samples']),
                    'map_created': False,
                    'error': str(map_error)
                })
                continue
        
        successful_maps = [m for m in generated_maps if m.get('map_created', False)]
        
        return {
            "status": "success",
            "message": f"Generated {len(successful_maps)} maps for {len(affected_subgrids)} affected subgrids",
            "maps_created": len(successful_maps),
            "affected_subgrids": len(affected_subgrids),
            "maps": generated_maps,
            "layer_validation": validation["summary"]
        }
        
    except Exception as e:
        logger.error(f"Map generation failed: {e}")
        raise RuntimeError(f"Failed to generate maps: {str(e)}")

def generate_maps_alternative_approach(gis, affected_subgrids, positive_samples):
    """
    Alternative map generation approach when WebMap is not available
    This creates a summary and provides layer information for manual map creation
    """
    logger.info("Using alternative map generation approach")
    
    try:
        generated_maps = []
        
        for subgrid_info in affected_subgrids:
            positive_count = len(subgrid_info['positive_samples'])
            diseases_found = set()
            for sample in subgrid_info['positive_samples']:
                diseases_found.update(sample['diseases'])
            
            # Calculate extent information
            subgrid_extent = subgrid_info['geometry']
            extent_info = None
            
            if 'extent' in subgrid_extent:
                extent_info = subgrid_extent['extent']
            else:
                # Calculate extent from geometry rings
                rings = subgrid_extent.get('rings', [[]])
                if rings and rings[0]:
                    x_coords = [point[0] for point in rings[0]]
                    y_coords = [point[1] for point in rings[0]]
                    extent_info = {
                        'xmin': min(x_coords),
                        'ymin': min(y_coords),
                        'xmax': max(x_coords),
                        'ymax': max(y_coords),
                        'spatialReference': subgrid_extent.get('spatialReference', {'wkid': 4326})
                    }
            
            generated_maps.append({
                'grid_label': subgrid_info['grid_label'],
                'positive_count': positive_count,
                'diseases': list(diseases_found),
                'extent': extent_info,
                'positive_samples': subgrid_info['positive_samples'],
                'map_created': False,
                'reason': 'WebMap not available - use provided extent and layer IDs to create maps manually',
                'layer_ids': {
                    'pools': POOLS_LAYER_ID,
                    'subgrids': SUBGRID_LAYER_ID,
                    'streets': STREETS_LAYER_ID,
                    'parcels': PARCELS_LAYER_ID,
                    'trs_zones': TRS_LAYER_ID
                }
            })
        
        return {
            "status": "success",
            "message": f"Identified {len(affected_subgrids)} subgrids for map creation. WebMap not available - see details for manual map creation.",
            "maps_created": 0,
            "affected_subgrids": len(affected_subgrids),
            "maps": generated_maps,
            "note": "Use ArcGIS Pro or ArcGIS Online Map Viewer with the provided layer IDs and extents to create maps manually"
        }
        
    except Exception as e:
        logger.error(f"Alternative map generation failed: {e}")
        raise RuntimeError(f"Failed to generate map information: {str(e)}")

# Configuration helper functions
def configure_map_layers(subgrid_id=None, streets_id=None, parcels_id=None, trs_id=None):
    """
    Configure layer IDs for map generation
    
    Args:
        subgrid_id: Subgrid layer ID
        streets_id: Streets layer ID
        parcels_id: Land parcels layer ID
        trs_id: TRS zones layer ID
    """
    global SUBGRID_LAYER_ID, STREETS_LAYER_ID, PARCELS_LAYER_ID, TRS_LAYER_ID
    
    if subgrid_id:
        SUBGRID_LAYER_ID = subgrid_id
    if streets_id:
        STREETS_LAYER_ID = streets_id
    if parcels_id:
        PARCELS_LAYER_ID = parcels_id
    if trs_id:
        TRS_LAYER_ID = trs_id
    
    logger.info(f"Map layer configuration updated:")
    logger.info(f"  Subgrid: {SUBGRID_LAYER_ID}")
    logger.info(f"  Streets: {STREETS_LAYER_ID}")
    logger.info(f"  Parcels: {PARCELS_LAYER_ID}")
    logger.info(f"  TRS: {TRS_LAYER_ID}")

def get_layer_configuration():
    """
    Get current layer configuration
    
    Returns:
        dict: Current layer IDs
    """
    return {
        "pools_layer_id": POOLS_LAYER_ID,
        "subgrid_layer_id": SUBGRID_LAYER_ID,
        "streets_layer_id": STREETS_LAYER_ID,
        "parcels_layer_id": PARCELS_LAYER_ID,
        "trs_layer_id": TRS_LAYER_ID
    }
