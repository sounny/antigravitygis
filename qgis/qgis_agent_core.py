"""
qgis_agent_core.py - QGIS PyQGIS Integration for AntigravityGIS by Sounny
Created by Sounny (sounny.com)
"""

import sys
import os
import json
import datetime
from typing import Dict, Any, Optional

# Import platform-agnostic core agent
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
for p in [current_dir, parent_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from agent_core import GISAntigravityAgent, inspect_directory_spatial_data, format_graceful_error
except ImportError:
    GISAntigravityAgent = None
    inspect_directory_spatial_data = None
    format_graceful_error = None


def inspect_qgis_active_project() -> str:
    """Inspects all active vector and raster map layers in the current QGIS project.
    
    Returns:
        JSON string containing layer names, geometry types, feature counts, CRS, and project metadata.
    """
    try:
        from qgis.core import QgsProject
        project = QgsProject.instance()
        layers = list(project.mapLayers().values())
        
        results = []
        for l in layers:
            geom_type = "Raster"
            if l.type() == 0:  # Vector
                geom_type = ["Point", "Line", "Polygon", "Unknown"][l.geometryType()] if hasattr(l, "geometryType") and l.geometryType() < 3 else "Vector"
            results.append({
                "id": l.id(),
                "name": l.name(),
                "type": geom_type,
                "crs": l.crs().authid() if l.crs().isValid() else "Unknown",
                "feature_count": l.featureCount() if hasattr(l, "featureCount") else None,
                "extent": str(l.extent().toString()) if hasattr(l, "extent") else None,
                "source": l.source() if hasattr(l, "source") else ""
            })
        return json.dumps({
            "qgis_project": project.fileName() or "Untitled Project",
            "crs": project.crs().authid(),
            "layer_count": len(results),
            "layers": results
        }, indent=2)
    except Exception as e:
        return f"[QGIS Environment Required] Simulated QGIS Active Project Inspection (PyQGIS not imported): {str(e)}"


def describe_qgis_layer(layer_name: str) -> str:
    """Describes fields, geometry type, feature count, and spatial reference of a specific QGIS layer by name."""
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
            "crs": layer.crs().authid() if layer.crs().isValid() else "Unknown",
            "type": "Vector" if layer.type() == 0 else "Raster",
            "fields": fields,
            "feature_count": layer.featureCount() if hasattr(layer, "featureCount") else None,
            "extent": str(layer.extent().toString()) if hasattr(layer, "extent") else None,
        }, indent=2)
    except Exception as e:
        return f"[QGIS Core] Layer description for '{layer_name}': {str(e)}"


def run_pyqgis_code(python_code: str) -> str:
    """Safely executes a snippet of PyQGIS code in the active QGIS Python environment.
    
    Can be used to calculate buffers, add vector layers, execute QGIS processing algorithms,
    zoom to features, or change layer symbology.
    """
    try:
        scope = {}
        try:
            from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer, QgsGeometry, QgsPointXY, QgsFeature
            scope.update({
                "QgsProject": QgsProject,
                "QgsVectorLayer": QgsVectorLayer,
                "QgsRasterLayer": QgsRasterLayer,
                "QgsGeometry": QgsGeometry,
                "QgsPointXY": QgsPointXY,
                "QgsFeature": QgsFeature,
                "project": QgsProject.instance(),
            })
        except ImportError:
            pass

        try:
            import processing
            scope["processing"] = processing
        except ImportError:
            pass

        exec(python_code, scope)
        return "✅ PyQGIS script executed successfully on active QGIS canvas."
    except Exception as e:
        return f"❌ PyQGIS execution failed: {str(e)}"


def zoom_to_qgis_layer(layer_name: str) -> str:
    """Zooms the active QGIS map canvas to the extent of a specified layer."""
    try:
        from qgis.core import QgsProject
        from qgis.utils import iface
        project = QgsProject.instance()
        matched = [l for l in project.mapLayers().values() if l.name().lower() == layer_name.lower()]
        if not matched:
            return f"Layer '{layer_name}' not found."
        if iface and iface.mapCanvas():
            iface.mapCanvas().setExtent(matched[0].extent())
            iface.mapCanvas().refresh()
            return f"✅ Zoomed to layer '{layer_name}'."
        return f"Layer '{layer_name}' extent: {matched[0].extent().toString()}"
    except Exception as e:
        return f"Zoom failed: {str(e)}"


def add_vector_layer_to_qgis(layer_path: str, layer_name: Optional[str] = None) -> str:
    """Loads a vector dataset (Shapefile, GeoJSON, GeoPackage, KML) into the active QGIS project."""
    try:
        from qgis.core import QgsProject, QgsVectorLayer
        if not os.path.exists(layer_path):
            return f"File does not exist: {layer_path}"
        name = layer_name or os.path.splitext(os.path.basename(layer_path))[0]
        vlayer = QgsVectorLayer(layer_path, name, "ogr")
        if not vlayer.isValid():
            return f"Failed to load layer: {layer_path}"
        QgsProject.instance().addMapLayer(vlayer)
        return f"✅ Layer '{name}' successfully added to QGIS project ({vlayer.featureCount()} features)."
    except Exception as e:
        return f"Failed to add layer to QGIS: {str(e)}"


def log_chat_to_qgis_project(prompt: str, response: str, model: str = "gemini-2.5-flash"):
    """Logs conversation history to Antigravity_Chat_History.md in the current QGIS project folder."""
    try:
        from qgis.core import QgsProject
        proj = QgsProject.instance()
        proj_file = proj.fileName()
        proj_dir = os.path.dirname(proj_file) if proj_file else os.path.expanduser("~")
        
        md_path = os.path.join(proj_dir, "Antigravity_Chat_History.md")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (
            f"### Session Turn — {timestamp} (Engine: `{model}`)\n\n"
            f"**User Prompt:**\n> {prompt}\n\n"
            f"**Antigravity Copilot Response:**\n{response}\n\n---\n\n"
        )
        with open(md_path, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


class QGISAntigravityPlugin:
    """QGIS PyQGIS Plugin Harness for AntigravityGIS by Sounny."""
    def __init__(self, iface=None, model: str = "gemini-2.5-flash"):
        self.iface = iface
        self.model = model
        self.agent = GISAntigravityAgent(model=model) if GISAntigravityAgent else None
        
        if self.agent:
            self.agent.register_tool(inspect_qgis_active_project)
            self.agent.register_tool(describe_qgis_layer)
            self.agent.register_tool(run_pyqgis_code)
            self.agent.register_tool(zoom_to_qgis_layer)
            self.agent.register_tool(add_vector_layer_to_qgis)
            if inspect_directory_spatial_data:
                self.agent.register_tool(inspect_directory_spatial_data)

    def run_prompt(self, prompt_text: str, token_callback=None) -> str:
        """Executes natural language spatial prompt inside QGIS."""
        if not self.agent:
            return "Error: Antigravity Agent Core not available. Install google-antigravity SDK."
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.agent.execute_prompt(prompt_text, token_callback=token_callback, model=self.model)
            )
            loop.close()
            log_chat_to_qgis_project(prompt_text, result, self.model)
            return result
        except Exception as e:
            err = format_graceful_error(e) if format_graceful_error else str(e)
            return f"[AntigravityGIS Error] {err}"
