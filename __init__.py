# -*- coding: utf-8 -*-
"""
DuckGIS - High-performance DuckDB Spatial Studio & Cloud GeoParquet Engine for QGIS
"""

def classFactory(iface):
    """
    QGIS Plugin class factory entry point.
    Called by QGIS when the plugin is loaded into memory.
    """
    from duckgis_plugin import DuckGISPlugin
    return DuckGISPlugin(iface)
