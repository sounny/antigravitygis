# -*- coding: utf-8 -*-
"""
AntigravityGIS QGIS Plugin - __init__.py
Created by Sounny (sounny.com)

This module is required by QGIS to load the plugin.
It provides the classFactory() function that QGIS calls to instantiate the plugin.
"""


def classFactory(iface):
    """QGIS Plugin Entry Point — called by QGIS when the plugin is loaded.
    
    Args:
        iface: QgisInterface instance providing access to the QGIS application.
    
    Returns:
        AntigravityGISPlugin instance.
    """
    from .antigravitygis_plugin import AntigravityGISPlugin
    return AntigravityGISPlugin(iface)
