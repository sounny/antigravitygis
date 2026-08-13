"""
qgis_agent_core.py - QGIS PyQGIS Integration for AntigravityGIS by Sounny
Created by Sounny (sounny.com)
"""

import sys
import os
import json

# Import platform-agnostic core agent
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
for p in [current_dir, parent_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from agent_core import GISAntigravityAgent
except ImportError:
    GISAntigravityAgent = None


def inspect_qgis_active_project() -> str:
    """Inspects all active vector and raster map layers in the current QGIS project.
    
    Returns:
        JSON string containing layer names, geometry types, feature counts, and CRS.
    """
    try:
        from qgis.core import QgsProject
        project = QgsProject.instance()
        layers = project.mapLayers().values()
        
        results = []
        for l in layers:
            results.append({
                "id": l.id(),
                "name": l.name(),
                "type": "Vector" if l.type() == 0 else "Raster",
                "crs": l.crs().authid(),
                "feature_count": l.featureCount() if hasattr(l, "featureCount") else None,
                "extent": str(l.extent().toString()) if hasattr(l, "extent") else None
            })
        return json.dumps({"qgis_project": project.fileName() or "Untitled", "layer_count": len(results), "layers": results}, indent=2)
    except Exception as e:
        return f"[QGIS Environment Required] Simulated QGIS Active Project Inspection (PyQGIS not imported): {str(e)}"


def describe_qgis_layer(layer_name: str) -> str:
    """Describes fields, geometry type, and spatial reference of a specific QGIS layer by name."""
    try:
        from qgis.core import QgsProject
        project = QgsProject.instance()
        matched = [l for l in project.mapLayers().values() if l.name().lower() == layer_name.lower()]
        
        if not matched:
            return f"Error: Layer '{layer_name}' not found in active QGIS project."
        
        layer = matched[0]
        fields = [f.name() for f in layer.fields()] if hasattr(layer, "fields") else []
        return json.dumps({
            "name": layer.name(),
            "crs": layer.crs().authid(),
            "fields": fields,
            "feature_count": layer.featureCount() if hasattr(layer, "featureCount") else None
        }, indent=2)
    except Exception as e:
        return f"[QGIS Core] Layer description for '{layer_name}': {str(e)}"


class QGISAntigravityPlugin:
    """QGIS PyQGIS Plugin Harness for AntigravityGIS by Sounny."""
    def __init__(self, iface=None):
        self.iface = iface
        self.agent = GISAntigravityAgent() if GISAntigravityAgent else None
        
        if self.agent:
            self.agent.register_tool(inspect_qgis_active_project)
            self.agent.register_tool(describe_qgis_layer)

    def run_prompt(self, prompt_text: str) -> str:
        """Executes natural language spatial prompt inside QGIS."""
        if not self.agent:
            return "Error: Antigravity Agent Core not available. Install google-antigravity SDK."
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.agent.execute_prompt(prompt_text))
            loop.close()
            return result
        except Exception as e:
            return f"[AntigravityGIS Error] Agent execution failed: {str(e)}"
