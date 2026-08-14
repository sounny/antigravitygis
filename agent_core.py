"""
agent_core.py - Core Antigravity GIS Agent Engine
Version: 1.0.0
Created by Moulay Anwar Sounny-Slitine, PhD

This module provides a platform-agnostic Antigravity Agent wrapper that can be embedded into:
  - ArcGIS Pro Python Toolboxes (.pyt)
  - QGIS Python Plugins
  - Standalone ArcPy / PyQGIS scripts
"""

import asyncio
import json
import os
import sys
import urllib.request
from typing import Callable, Optional, Dict, Any, List

__version__ = "1.0.0"

try:
    from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
except ImportError:
    Agent = None
    LocalAgentConfig = None
    CapabilitiesConfig = None


def check_for_updates() -> Optional[Dict[str, Any]]:
    """
    Checks the GitHub repository for the latest released version of AntigravityGIS.
    Returns update metadata if a newer version is available, or None.
    """
    try:
        url = "https://raw.githubusercontent.com/sounny/antigravitygis/main/version.json"
        req = urllib.request.Request(url, headers={"User-Agent": "AntigravityGIS-Updater"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            latest_ver = data.get("version", __version__)
            if latest_ver > __version__:
                return {
                    "current_version": __version__,
                    "latest_version": latest_ver,
                    "update_available": True,
                    "notes": data.get("notes", ""),
                    "update_command": "irm https://raw.githubusercontent.com/sounny/antigravitygis/main/install.ps1 | iex",
                }
    except Exception:
        pass
    return None


class GISAntigravityAgent:
    """
    Modular Antigravity Agent instance configured for GIS automation tasks.
    Decoupled from specific desktop UI platforms so it can serve both ArcGIS Pro and QGIS.
    """

    def __init__(self, system_instructions: Optional[str] = None, api_key: Optional[str] = None):
        if system_instructions is None:
            self.system_instructions = (
                "You are an expert AI GIS Assistant for ArcGIS Pro and QGIS.\n"
                "You have access to live desktop GIS tools:\n"
                "- When the user asks to add/make a point, pin a city, or map a coordinate, use 'create_point_feature' with the exact latitude, longitude, and name. This automatically creates the point feature class and adds it directly into their active ArcGIS Pro Map view!\n"
                "- When the user asks to load or visualize a dataset, use 'add_data_to_active_map'.\n"
                "- When the user asks to inspect a geodatabase or folder, use 'inspect_arcgis_workspace' or 'inspect_directory_spatial_data'.\n"
                "- When the user asks for geoprocessing (Buffer, Clip, Dissolve, Merge), use 'run_arcpy_geoprocessing'."
            )
        else:
            self.system_instructions = system_instructions

        self.api_key = api_key or os.environ.get("ANTIGRAVITY_API_KEY") or os.environ.get("GEMINI_API_KEY")

        self.custom_tools: Dict[str, Callable] = {
            "inspect_directory_spatial_data": inspect_directory_spatial_data,
            "inspect_arcgis_workspace": inspect_arcgis_workspace,
            "describe_arcgis_dataset": describe_arcgis_dataset,
            "run_arcpy_geoprocessing": run_arcpy_geoprocessing,
            "create_point_feature": create_point_feature,
            "add_data_to_active_map": add_data_to_active_map,
        }

    def register_tool(self, func: Callable):
        """Register a custom GIS function (ArcPy or PyQGIS wrapper) as an agent tool."""
        self.custom_tools[func.__name__] = func

    def _build_config(self) -> Optional[Any]:
        """Builds a fresh LocalAgentConfig equipped with all registered GIS tools."""
        if LocalAgentConfig is None or CapabilitiesConfig is None:
            return None

        tools_list = list(self.custom_tools.values())
        
        retry_cfg = None
        try:
            from google.antigravity import RetryConfig, ModelAPIRetryConfig
            retry_cfg = RetryConfig(
                api_retry=ModelAPIRetryConfig(
                    max_retries=3,
                    initial_sleep_duration_ms=2000,
                    exponential_multiplier=2.0
                )
            )
        except Exception:
            pass

        return LocalAgentConfig(
            system_instructions=self.system_instructions,
            capabilities=CapabilitiesConfig(),
            tools=tools_list,
            api_key=self.api_key,
            retry_config=retry_cfg,
        )

    async def execute_prompt(
        self, prompt: str, token_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Executes a natural language GIS prompt against the Antigravity Agent.
        Optionally invokes a token_callback for real-time UI streaming in ArcGIS/QGIS.
        """
        config = self._build_config()
        if Agent is None or config is None:
            err_msg = (
                "Google Antigravity SDK is not available. Please install 'google-antigravity' "
                "and ensure you are logged into your Google Antigravity account (agy auth login)."
            )
            if token_callback:
                token_callback(err_msg)
            return err_msg

        full_response = []

        try:
            async with Agent(config) as agent:
                response = await agent.chat(prompt)

                async for token in response:
                    token_str = str(token)
                    full_response.append(token_str)
                    if token_callback:
                        token_callback(token_str)
        except Exception as err:
            err_str = str(err)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                clean_err = (
                    "\n⚠️ [Rate Limit Reached (Free Tier: 5 requests/min)]\n"
                    "Google Antigravity is processing requests. Please wait ~30 seconds before sending your next prompt, "
                    "or enter a custom Gemini API Key in the tool's 3rd parameter."
                )
            elif "503" in err_str:
                clean_err = (
                    "\n⚠️ [Temporary Service Busy (HTTP 503)]\n"
                    "The model is experiencing high demand. Please try again in a few seconds."
                )
            else:
                clean_err = f"\nAntigravity Agent Notice: {err_str}"
            
            if token_callback:
                token_callback(clean_err)
            return clean_err

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
            elif ext in [".geojson", ".json"]:
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


def create_point_feature(latitude: float, longitude: float, name: str, output_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Creates a point feature at specified lat/long coordinates and automatically adds it directly to the active ArcGIS Pro map.
    """
    try:
        import arcpy
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        target_gdb = aprx.defaultGeodatabase or arcpy.env.workspace or os.path.expanduser("~")
        
        safe_name = "".join(c if c.isalnum() else "_" for c in name).strip("_")
        fc_name = arcpy.ValidateTableName(output_name or f"Point_{safe_name}", target_gdb)
        out_fc = os.path.join(target_gdb, fc_name)

        if arcpy.Exists(out_fc):
            arcpy.management.Delete(out_fc)

        sr = arcpy.SpatialReference(4326)  # WGS84
        arcpy.management.CreateFeatureclass(target_gdb, fc_name, "POINT", spatial_reference=sr)
        arcpy.management.AddField(out_fc, "Name", "TEXT", field_length=100)

        with arcpy.da.InsertCursor(out_fc, ["SHAPE@XY", "Name"]) as cursor:
            cursor.insertRow([(float(longitude), float(latitude)), str(name)])

        added_to_map = False
        active_map = aprx.activeMap or (aprx.listMaps()[0] if aprx.listMaps() else None)
        if active_map:
            active_map.addDataFromPath(out_fc)
            added_to_map = True

        return {
            "status": "Success",
            "feature_class": out_fc,
            "latitude": latitude,
            "longitude": longitude,
            "name": name,
            "added_to_map": added_to_map,
            "message": f"Successfully created point for '{name}' and added it directly to your active ArcGIS Pro map view!",
        }
    except ImportError:
        return {"error": "ArcPy library is not available in this Python environment."}
    except Exception as err:
        return {"error": f"Create point feature failed: {str(err)}"}


def add_data_to_active_map(data_path: str, layer_name: Optional[str] = None) -> Dict[str, Any]:
    """Adds an existing dataset, feature class, shapefile, or GeoJSON directly to the active ArcGIS Pro map."""
    try:
        import arcpy
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        active_map = aprx.activeMap or (aprx.listMaps()[0] if aprx.listMaps() else None)
        if not active_map:
            return {"error": "No active map found in the current ArcGIS Pro project."}

        layer = active_map.addDataFromPath(data_path)
        if layer_name and layer:
            layer.name = layer_name
        return {"status": "Success", "message": f"Added '{data_path}' directly to active map '{active_map.name}'."}
    except ImportError:
        return {"error": "ArcPy library is not available in this Python environment."}
    except Exception as err:
        return {"error": f"Failed to add data to active map: {str(err)}"}


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
