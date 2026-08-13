"""
agent_core.py - Core Antigravity GIS Agent Engine

This module provides a platform-agnostic Antigravity Agent wrapper that can be embedded into:
  - ArcGIS Pro Python Toolboxes (.pyt)
  - QGIS Python Plugins
  - Standalone ArcPy / PyQGIS scripts
"""

import asyncio
import os
import sys
from typing import Callable, Optional, Dict, Any

try:
    from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
except ImportError:
    Agent = None
    LocalAgentConfig = None
    CapabilitiesConfig = None


class GISAntigravityAgent:
    """
    Modular Antigravity Agent instance configured for GIS automation tasks.
    Decoupled from specific desktop UI platforms so it can serve both ArcGIS Pro and QGIS.
    """

    def __init__(self, system_instructions: Optional[str] = None):
        if system_instructions is None:
            system_instructions = (
                "You are an expert AI GIS Assistant capable of performing spatial analysis, "
                "inspecting datasets, writing geoprocessing scripts, and auditing spatial metadata "
                "for both ArcGIS Pro (ArcPy) and QGIS (PyQGIS/GDAL)."
            )

        if LocalAgentConfig and CapabilitiesConfig:
            self.config = LocalAgentConfig(
                system_instructions=system_instructions,
                capabilities=CapabilitiesConfig(),
            )
        else:
            self.config = None

        self.custom_tools: Dict[str, Callable] = {}

    def register_tool(self, func: Callable):
        """Register a custom GIS function (ArcPy or PyQGIS wrapper) as an agent tool."""
        self.custom_tools[func.__name__] = func

    async def execute_prompt(
        self, prompt: str, token_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Executes a natural language GIS prompt against the Antigravity Agent.
        Optionally invokes a token_callback for real-time UI streaming in ArcGIS/QGIS.
        """
        if Agent is None or self.config is None:
            err_msg = (
                "Google Antigravity SDK is not available. Please install 'google-antigravity' "
                "and ensure you are logged into your Google Antigravity account (agy auth login)."
            )
            if token_callback:
                token_callback(err_msg)
            return err_msg

        full_response = []

        async with Agent(self.config) as agent:
            # Attach custom registered GIS tools to the active agent session
            for tool_func in self.custom_tools.values():
                agent.register_tool(tool_func)

            response = await agent.chat(prompt)

            async for token in response:
                full_response.append(token)
                if token_callback:
                    token_callback(token)

        return "".join(full_response)


# Built-in generic spatial tools that work across environments
def inspect_directory_spatial_data(directory_path: str) -> Dict[str, Any]:
    """Scans a file directory for shapefiles, GeoJSON, KML, and File Geodatabases."""
    if not os.path.exists(directory_path):
        return {"error": f"Directory path '{directory_path}' does not exist."}

    found_files = {
        "shapefiles": [],
        "geodatabases": [],
        "geojson": [],
        "kml_kmz": [],
        "rasters": [],
    }

    for root, dirs, files in os.walk(directory_path):
        for d in dirs:
            if d.endswith(".gdb"):
                found_files["geodatabases"].append(os.path.join(root, d))
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            full_p = os.path.join(root, f)
            if ext == ".shp":
                found_files["shapefiles"].append(full_p)
            elif ext == ".geojson" or ext == ".json":
                found_files["geojson"].append(full_p)
            elif ext in [".kml", ".kmz"]:
                found_files["kml_kmz"].append(full_p)
            elif ext in [".tif", ".tiff", ".img", ".dem"]:
                found_files["rasters"].append(full_p)

    return found_files


# Built-in ArcPy tools for ArcGIS Pro Add-on integration
def inspect_arcgis_workspace(workspace_path: str) -> Dict[str, Any]:
    """Inspects an ArcGIS workspace / File Geodatabase using ArcPy and returns dataset summaries."""
    try:
        import arcpy
        arcpy.env.workspace = workspace_path
        fcs = arcpy.ListFeatureClasses() or []
        tables = arcpy.ListTables() or []
        rasters = arcpy.ListRasters() or []
        
        feature_details = []
        for fc in fcs:
            try:
                count = int(arcpy.management.GetCount(fc)[0])
                desc = arcpy.Describe(fc)
                shape_type = getattr(desc, "shapeType", "Unknown")
                sr = getattr(getattr(desc, "spatialReference", None), "name", "Unknown")
                feature_details.append({
                    "name": fc,
                    "record_count": count,
                    "geometry_type": shape_type,
                    "spatial_reference": sr,
                })
            except Exception as e:
                feature_details.append({"name": fc, "error": str(e)})

        return {
            "workspace": workspace_path,
            "feature_classes": feature_details,
            "table_count": len(tables),
            "raster_count": len(rasters),
        }
    except ImportError:
        return {"error": "ArcPy library is not available in this Python environment."}
    except Exception as err:
        return {"error": f"ArcPy inspection failed: {str(err)}"}


def describe_arcgis_dataset(dataset_path: str) -> Dict[str, Any]:
    """Retrieves field names, types, spatial reference, and extent for an ArcGIS dataset."""
    try:
        import arcpy
        if not arcpy.Exists(dataset_path):
            return {"error": f"Dataset '{dataset_path}' does not exist or is inaccessible."}

        desc = arcpy.Describe(dataset_path)
        fields = arcpy.ListFields(dataset_path) or []
        field_info = [{"name": f.name, "type": f.type, "length": getattr(f, "length", None)} for f in fields]

        extent = getattr(desc, "extent", None)
        extent_dict = {}
        if extent:
            extent_dict = {
                "XMin": extent.XMin,
                "YMin": extent.YMin,
                "XMax": extent.XMax,
                "YMax": extent.YMax,
            }

        return {
            "dataset": dataset_path,
            "dataType": getattr(desc, "dataType", "Unknown"),
            "datasetType": getattr(desc, "datasetType", "Unknown"),
            "spatialReference": getattr(getattr(desc, "spatialReference", None), "name", "Unknown"),
            "extent": extent_dict,
            "field_count": len(field_info),
            "fields": field_info,
        }
    except ImportError:
        return {"error": "ArcPy library is not available in this Python environment."}
    except Exception as err:
        return {"error": f"Dataset describe failed: {str(err)}"}


def run_arcpy_geoprocessing(tool_name: str, **kwargs) -> Dict[str, Any]:
    """Executes a specified ArcPy geoprocessing tool with key-value parameters."""
    try:
        import arcpy
        gp_func = getattr(arcpy.management, tool_name, None) or getattr(arcpy.analysis, tool_name, None)
        if not gp_func:
            return {"error": f"ArcPy tool '{tool_name}' not found under management or analysis modules."}
        
        result = gp_func(**kwargs)
        return {
            "status": "Success",
            "tool": tool_name,
            "output": str(result),
        }
    except ImportError:
        return {"error": "ArcPy library is not available in this Python environment."}
    except Exception as err:
        return {"error": f"Geoprocessing tool '{tool_name}' failed: {str(err)}"}


def check_and_prompt_antigravity_login() -> Dict[str, Any]:
    """
    Checks if active Antigravity credentials exist.
    If missing, attempts to launch 1-click browser login or provides actionable instructions.
    """
    import subprocess
    user_home = os.path.expanduser("~")
    antigravity_dir = os.path.join(user_home, ".gemini", "antigravity")
    
    if os.environ.get("ANTIGRAVITY_API_KEY") or os.path.exists(antigravity_dir):
        return {"status": "authenticated", "message": "Google Antigravity session active."}

    # Attempt to invoke agy auth login
    try:
        proc = subprocess.run(["agy", "auth", "login"], capture_output=True, text=True, timeout=10)
        if proc.returncode == 0:
            return {"status": "authenticated", "message": "Successfully authenticated with Google Antigravity!"}
    except Exception:
        pass

    return {
        "status": "unauthenticated",
        "message": (
            "No active Google Antigravity session found. "
            "Please run 'agy auth login' in your terminal or log into the Antigravity Desktop App."
        ),
    }


