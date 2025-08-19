"""
Utility functions for the CMAD ArcGIS application
Common helper functions used across multiple modules
"""

import logging
from arcgis.features import FeatureLayerCollection, FeatureLayer

logger = logging.getLogger(__name__)

def get_layer_info(gis, layer_id):
    """
    Retrieve layer information from AGOL using layer ID
    
    Args:
        gis: Authenticated ArcGIS GIS object
        layer_id: The layer ID to get information for
        
    Returns:
        dict: Layer information including title, type, owner, etc.
    """
    try:
        item = gis.content.get(layer_id)
        if not item:
            return {"error": f"Layer {layer_id} not found"}
            
        info = {
            "id": layer_id,
            "title": item.title,
            "type": item.type,
            "owner": item.owner,
            "created": str(item.created) if item.created else None,
            "modified": str(item.modified) if item.modified else None,
            "snippet": item.snippet,
            "description": item.description,
            "tags": item.tags if hasattr(item, 'tags') else [],
        }
        
        # Additional info for feature services/layers
        if hasattr(item, 'url'):
            info["url"] = item.url
            
        return info
        
    except Exception as e:
        logger.error(f"Error getting layer info for {layer_id}: {e}")
        return {"error": f"Failed to get info for layer {layer_id}: {str(e)}"}

def get_layer_from_item(gis, layer_id):
    """
    Get a feature layer from an ArcGIS Online item
    
    Args:
        gis: Authenticated ArcGIS GIS object
        layer_id: The layer ID to access
        
    Returns:
        tuple: (FeatureLayer object, layer info dict)
    """
    try:
        item = gis.content.get(layer_id)
        if not item:
            raise RuntimeError(f"Layer {layer_id} not found")
            
        # Access the layer based on type
        if item.type == "Feature Service":
            layer = FeatureLayerCollection.fromitem(item).layers[0]
        else:
            # Standalone shapefile/feature layer
            layer = FeatureLayer.fromitem(item)
            
        # Get basic layer metadata
        layer_properties = layer.properties
        field_names = [f['name'] for f in layer_properties.fields] if hasattr(layer_properties, 'fields') else []
        
        layer_info = {
            "title": item.title,
            "type": item.type,
            "total_features": layer.query(return_count_only=True),
            "fields": field_names,
            "item_id": layer_id
        }
        
        logger.info(f"Successfully accessed layer: {item.title} ({layer_id})")
        return layer, layer_info
        
    except Exception as e:
        logger.error(f"Error accessing layer {layer_id}: {e}")
        raise RuntimeError(f"Failed to access layer {layer_id}: {str(e)}")

def format_date_for_query(date_string, date_field):
    """
    Format a date string for ArcGIS SQL queries
    
    Args:
        date_string: Date in YYYY-MM-DD format
        date_field: The name of the date field
        
    Returns:
        str: Formatted date query clause
    """
    from datetime import datetime
    
    try:
        # Validate date format
        datetime.strptime(date_string, '%Y-%m-%d')
        return f"date '{date_string}'"
    except ValueError:
        raise ValueError(f"Invalid date format: {date_string}. Expected YYYY-MM-DD")

def build_date_range_query(start_date, end_date, date_field='add_date'):
    """
    Build a date range WHERE clause for ArcGIS queries
    
    Args:
        start_date: Start date (YYYY-MM-DD format)
        end_date: End date (YYYY-MM-DD format)
        date_field: Field name to use for date filtering
        
    Returns:
        str: WHERE clause for date range
    """
    start_formatted = format_date_for_query(start_date, date_field)
    end_formatted = format_date_for_query(end_date, date_field)
    
    return f"{date_field} >= {start_formatted} AND {date_field} <= {end_formatted}"

def validate_layer_access(gis, layer_id):
    """
    Validate that a layer is accessible and return basic info
    
    Args:
        gis: Authenticated ArcGIS GIS object
        layer_id: The layer ID to validate
        
    Returns:
        dict: Validation result with status and info
    """
    try:
        layer, layer_info = get_layer_from_item(gis, layer_id)
        
        # Test basic query capability
        test_count = layer.query(where="1=1", return_count_only=True)
        
        return {
            "accessible": True,
            "layer_info": layer_info,
            "test_query_count": test_count,
            "message": f"Layer '{layer_info['title']}' is accessible with {test_count} features"
        }
        
    except Exception as e:
        return {
            "accessible": False,
            "error": str(e),
            "message": f"Layer {layer_id} is not accessible: {str(e)}"
        }

def log_request(endpoint, parameters):
    """
    Log API request details
    
    Args:
        endpoint: The API endpoint being called
        parameters: Request parameters
    """
    logger.info(f"[API] {endpoint} called with parameters: {parameters}")

def log_result(endpoint, success, details=None):
    """
    Log API result details
    
    Args:
        endpoint: The API endpoint
        success: Whether the operation was successful
        details: Additional details about the result
    """
    status = "SUCCESS" if success else "FAILURE"
    logger.info(f"[API] {endpoint} - {status}: {details or 'No additional details'}")
