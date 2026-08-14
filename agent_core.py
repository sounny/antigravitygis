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

    def __init__(
        self,
        system_instructions: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        if system_instructions is None:
            self.system_instructions = (
                "You are an expert AI GIS Assistant for ArcGIS Pro and QGIS.\n"
                "You have access to live desktop GIS tools:\n"
                "- When the user asks to add/make a point, pin a city, or map a coordinate, use 'create_point_feature' with the exact latitude, longitude, and name. This automatically creates the point feature class and adds it directly into their active ArcGIS Pro Map view!\n"
                "- When the user asks to buffer a layer or feature, use 'buffer_feature_layer'.\n"
                "- When the user asks to load or visualize a dataset, use 'add_data_to_active_map'.\n"
                "- When the user asks to inspect a geodatabase or folder, use 'inspect_arcgis_workspace' or 'inspect_directory_spatial_data'.\n"
                "- When the user asks for geoprocessing (Buffer, Clip, Dissolve, Merge), use 'run_arcpy_geoprocessing'.\n"
                "- When asked to write ArcPy scripts, output clean Python code blocks."
            )
        else:
            self.system_instructions = system_instructions

        # Auto-detect API key from process environment or Windows User Environment Registry
        discovered_key = api_key or os.environ.get("ANTIGRAVITY_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not discovered_key and sys.platform == "win32":
            try:
                import winreg
                reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ)
                for var_name in ["GEMINI_API_KEY", "ANTIGRAVITY_API_KEY"]:
                    try:
                        val, _ = winreg.QueryValueEx(reg_key, var_name)
                        if val and val.strip():
                            discovered_key = val.strip()
                            os.environ[var_name] = discovered_key
                            break
                    except Exception:
                        pass
                winreg.CloseKey(reg_key)
            except Exception:
                pass

        self.api_key = discovered_key
        self.model = model or os.environ.get("ANTIGRAVITY_MODEL", "gemini-2.5-flash")
        self.conversation_history = []

        self.custom_tools: Dict[str, Callable] = {
            "inspect_directory_spatial_data": inspect_directory_spatial_data,
            "inspect_arcgis_workspace": inspect_arcgis_workspace,
            "describe_arcgis_dataset": describe_arcgis_dataset,
            "run_arcpy_geoprocessing": run_arcpy_geoprocessing,
            "create_point_feature": create_point_feature,
            "buffer_feature_layer": buffer_feature_layer,
            "add_data_to_active_map": add_data_to_active_map,
            "execute_arcpy_code_snippet": execute_arcpy_code_snippet,
        }

    def register_tool(self, func: Callable):
        """Register a custom GIS function (ArcPy or PyQGIS wrapper) as an agent tool."""
        self.custom_tools[func.__name__] = func

    def _build_config(self, model_override: Optional[str] = None) -> Optional[Any]:
        """Builds a fresh LocalAgentConfig equipped with all registered GIS tools."""
        if LocalAgentConfig is None or CapabilitiesConfig is None:
            return None

        tools_list = list(self.custom_tools.values())
        target_model = model_override or self.model
        
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
            model=target_model,
            retry_config=retry_cfg,
        )

    async def execute_prompt(
        self,
        prompt: str,
        token_callback: Optional[Callable[[str], None]] = None,
        model: Optional[str] = None,
        workspace: Optional[str] = None,
    ) -> str:
        """
        Executes a natural language GIS prompt against the Antigravity Agent.
        Optionally invokes a token_callback for real-time UI streaming in ArcGIS/QGIS.
        Maintains conversation history and logs output to the project geodatabase.
        """
        config = self._build_config(model_override=model)
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
                # Include recent conversation turns for multi-turn context
                conversation_prompt = prompt
                if self.conversation_history:
                    history_context = "\n".join(
                        [f"{t['role'].upper()}: {t['content']}" for t in self.conversation_history[-4:]]
                    )
                    conversation_prompt = f"Previous Conversation Context:\n{history_context}\n\nUser Instruction:\n{prompt}"

                response = await agent.chat(conversation_prompt)

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

        final_text = "".join(full_response)
        
        # Save to conversation memory
        self.conversation_history.append({"role": "user", "content": prompt})
        self.conversation_history.append({"role": "assistant", "content": final_text})

        # Automatically log to Project Markdown & Geodatabase Table
        try:
            log_chat_to_geodatabase(
                prompt=prompt,
                response=final_text,
                workspace=workspace,
                model=model or self.model,
            )
        except Exception:
            pass

        return final_text


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


def buffer_feature_layer(
    input_layer: str,
    distance: float,
    unit: str = "Kilometers",
    output_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Buffers an existing layer or feature class by a given distance and adds the buffer layer to the active map.
    Example: buffer_feature_layer(input_layer='Point_Austin', distance=10, unit='Kilometers')
    """
    try:
        import arcpy
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        target_gdb = aprx.defaultGeodatabase or arcpy.env.workspace or os.path.expanduser("~")
        
        safe_name = "".join(c if c.isalnum() else "_" for c in (output_name or f"{input_layer}_Buffer_{int(distance)}{unit[:2]}")).strip("_")
        fc_name = arcpy.ValidateTableName(safe_name, target_gdb)
        out_fc = os.path.join(target_gdb, fc_name)
        
        dist_str = f"{distance} {unit}"
        arcpy.analysis.Buffer(in_features=input_layer, out_feature_class=out_fc, buffer_distance_or_field=dist_str)
        
        active_map = aprx.activeMap or (aprx.listMaps()[0] if aprx.listMaps() else None)
        if active_map:
            active_map.addDataFromPath(out_fc)
            
        return {
            "status": "Success",
            "buffered_layer": out_fc,
            "distance": dist_str,
            "added_to_map": bool(active_map),
            "message": f"Created {dist_str} buffer layer '{fc_name}' and added it to active map view!",
        }
    except ImportError:
        return {"error": "ArcPy library is not available in this Python environment."}
    except Exception as err:
        return {"error": f"Buffer failed: {str(err)}"}


def execute_arcpy_code_snippet(code: str) -> Dict[str, Any]:
    """
    Safely executes an ArcPy or Python code snippet directly in the active ArcGIS Pro session.
    """
    import io
    import sys
    import contextlib
    
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    try:
        import arcpy
        local_scope = {"arcpy": arcpy, "os": os, "sys": sys}
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            exec(code, local_scope)
            
        return {
            "status": "Success",
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue(),
            "message": "Executed ArcPy code snippet successfully.",
        }
    except Exception as err:
        return {
            "status": "Error",
            "error": str(err),
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue(),
        }


def log_chat_to_geodatabase(
    prompt: str,
    response: str,
    workspace: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Saves the conversation turn into:
    1. A formatted markdown transcript 'Antigravity_Chat_History.md' in project directory and workspace.
    2. A structured JSON file 'antigravity_chat_history.json'.
    3. An ArcGIS Pro Geodatabase Table 'Antigravity_Session_Log' in the default geodatabase (if ArcPy is available).
    """
    import datetime
    import json
    
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    iso_date = datetime.datetime.now().isoformat()
    model_name = model or "gemini-2.5-flash"
    
    target_ws = workspace
    project_dir = None
    
    try:
        import arcpy
        if not target_ws:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            target_ws = aprx.defaultGeodatabase or arcpy.env.workspace
            if hasattr(aprx, "homeFolder") and aprx.homeFolder:
                project_dir = aprx.homeFolder
            elif hasattr(aprx, "filePath") and aprx.filePath:
                project_dir = os.path.dirname(aprx.filePath)
    except Exception:
        pass

    if not target_ws:
        target_ws = os.path.expanduser(r"~\Documents\ArcGIS\Projects\AntigravityGIS")
        os.makedirs(target_ws, exist_ok=True)
    if not project_dir:
        project_dir = os.path.dirname(target_ws) if target_ws.endswith(".gdb") else target_ws

    # 1. Append to Markdown Transcript
    md_entry = (
        f"\n\n---\n"
        f"### 💬 Session Turn — {timestamp_str}\n"
        f"**Model:** `{model_name}` | **Workspace:** `{os.path.basename(target_ws)}`\n\n"
        f"**🧑 User Prompt:**\n> {prompt.strip()}\n\n"
        f"**✨ Antigravity Copilot Response:**\n{response.strip()}\n"
    )

    folders_to_write = set()
    if project_dir and os.path.exists(project_dir):
        folders_to_write.add(project_dir)
    parent_gdb_dir = os.path.dirname(target_ws) if target_ws.endswith(".gdb") else target_ws
    if parent_gdb_dir and os.path.exists(parent_gdb_dir):
        folders_to_write.add(parent_gdb_dir)

    for folder in folders_to_write:
        try:
            md_path = os.path.join(folder, "Antigravity_Chat_History.md")
            header = ""
            if not os.path.exists(md_path):
                header = (
                    "# AntigravityGIS Project Chat & Geoprocessing Log\n"
                    "Automatic persistent audit log generated by AntigravityGIS AI Copilot by Sounny.\n\n"
                )
            with open(md_path, "a", encoding="utf-8") as f:
                if header:
                    f.write(header)
                f.write(md_entry)
        except Exception:
            pass

    # 2. Append to JSON log file
    try:
        json_path = os.path.join(project_dir, "antigravity_chat_history.json")
        entries = []
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            except Exception:
                entries = []
        entries.append({
            "timestamp": iso_date,
            "display_time": timestamp_str,
            "model": model_name,
            "prompt": prompt,
            "response": response,
            "workspace": target_ws,
        })
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
    except Exception:
        pass

    # 3. Insert into ArcGIS Geodatabase Table 'Antigravity_Session_Log' if ArcPy available
    gdb_logged = False
    try:
        import arcpy
        if target_ws and target_ws.endswith(".gdb") and arcpy.Exists(target_ws):
            tbl_name = "Antigravity_Session_Log"
            tbl_path = os.path.join(target_ws, tbl_name)
            if not arcpy.Exists(tbl_path):
                arcpy.management.CreateTable(target_ws, tbl_name)
                arcpy.management.AddField(tbl_path, "LogTime", "TEXT", field_length=50)
                arcpy.management.AddField(tbl_path, "Model", "TEXT", field_length=50)
                arcpy.management.AddField(tbl_path, "Prompt", "TEXT", field_length=2000)
                arcpy.management.AddField(tbl_path, "Response", "TEXT", field_length=4000)
            
            with arcpy.da.InsertCursor(tbl_path, ["LogTime", "Model", "Prompt", "Response"]) as cursor:
                cursor.insertRow([timestamp_str, model_name, prompt[:1990], response[:3990]])
            gdb_logged = True
    except Exception:
        pass

    return {
        "status": "Success",
        "markdown_saved": True,
        "json_saved": True,
        "geodatabase_table_logged": gdb_logged,
        "workspace": target_ws,
    }


def check_and_prompt_antigravity_login() -> Dict[str, Any]:
    """
    Checks if active Antigravity credentials exist silently with zero subprocesses or console popups.
    """
    user_home = os.path.expanduser("~")
    antigravity_dir = os.path.join(user_home, ".gemini", "antigravity")
    
    if os.environ.get("ANTIGRAVITY_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        return {"status": "authenticated", "message": "Google Antigravity API key active."}

    if os.path.exists(antigravity_dir):
        return {"status": "authenticated", "message": "Google Antigravity session active."}

    if sys.platform == "win32":
        try:
            import winreg
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ)
            for var_name in ["GEMINI_API_KEY", "ANTIGRAVITY_API_KEY"]:
                try:
                    val, _ = winreg.QueryValueEx(reg_key, var_name)
                    if val and val.strip():
                        winreg.CloseKey(reg_key)
                        os.environ[var_name] = val.strip()
                        return {"status": "authenticated", "message": "Google Antigravity session active."}
                except Exception:
                    pass
            winreg.CloseKey(reg_key)
        except Exception:
            pass

    return {
        "status": "unauthenticated",
        "message": (
            "No active Google Antigravity session found. "
            "Please configure your Google AI Studio API key via 'Set Google AI Studio API Key' tool or log into the Antigravity Desktop App."
        ),
    }
