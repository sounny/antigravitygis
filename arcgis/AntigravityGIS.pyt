# -*- coding: utf-8 -*-
"""
AntigravityGIS.pyt - ArcGIS Pro Python Toolbox Extension

AntigravityGIS by Sounny
Integrates Google Antigravity AI Agents directly into the ArcGIS Pro Geoprocessing Pane.
Runs off the user's active Google Antigravity account & SDK session.
"""

import asyncio
import os
import sys
import arcpy

# Ensure both current directory and parent directory are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import importlib
if "agent_core" in sys.modules:
    try:
        importlib.invalidate_caches()
        importlib.reload(sys.modules["agent_core"])
    except Exception:
        pass

import_error_msg = None
try:
    from agent_core import (
        __version__,
        check_for_updates,
        GISAntigravityAgent,
        inspect_directory_spatial_data,
        inspect_arcgis_workspace,
        describe_arcgis_dataset,
        run_arcpy_geoprocessing,
        check_and_prompt_antigravity_login,
    )
except Exception as err:
    import_error_msg = str(err)
    __version__ = "1.0.0"
    check_for_updates = None
    GISAntigravityAgent = None
    check_and_prompt_antigravity_login = None


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the .pyt file)."""
        self.label = f"AntigravityGIS (v{__version__})"
        self.alias = "AntigravityGIS"
        self.tools = [AntigravityAssistantTool, ConfigureApiKeyTool]


class AntigravityAssistantTool(object):
    def __init__(self):
        """Define the tool (tool name and properties)."""
        self.label = "Antigravity AI Assistant (by Sounny)"
        self.category = "Sounny AI Tools"
        self.description = (
            "AntigravityGIS by Moulay Anwar Sounny-Slitine, PhD\n\n"
            "Enterprise AI Copilot running on Google Antigravity for spatial analysis, "
            "geoprocessing automation, dataset inspection, and ArcPy workflows inside ArcGIS Pro.\n\n"
            "🔑 GOOGLE AI STUDIO API KEY:\n"
            "Get your free high-throughput API key at https://aistudio.google.com/apikey and paste it into Parameter 3 below "
            "for instant 1,000+ requests/min quota.\n\n"
            "⚠️ AI DATA PRIVACY WARNING: You are interacting with an AI model. Be cautious when processing "
            "sensitive, confidential, or proprietary spatial datasets. Ensure compliance with your organization's "
            "data security and privacy policies."
        )
        self.canRunInBackground = False


    def getParameterInfo(self):
        """Define parameter definitions for the Geoprocessing Tool dialog."""
        # Parameter 0: Prompt
        param_prompt = arcpy.Parameter(
            displayName="Prompt / Natural Language Spatial Instruction",
            name="prompt",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        param_prompt.value = "Inspect feature classes in the target workspace and count records."

        # Parameter 1: Workspace Path
        param_workspace = arcpy.Parameter(
            displayName="Target Workspace / Geodatabase Path (Defaults to Project GDB)",
            name="workspace_path",
            datatype="DEWorkspace",
            parameterType="Optional",
            direction="Input",
        )
        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            if aprx.defaultGeodatabase:
                param_workspace.value = aprx.defaultGeodatabase
        except Exception:
            pass

        # Parameter 2: Google AI Studio API Key / Token (Optional)
        param_auth = arcpy.Parameter(
            displayName="Google AI Studio API Key (Optional — get at aistudio.google.com/apikey)",
            name="auth_token",
            datatype="GPStringHidden",
            parameterType="Optional",
            direction="Input",
        )

        return [param_prompt, param_workspace, param_auth]

    def isLicensable(self):
        """Return True if tool is licensable to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal validation is performed."""
        if len(parameters) > 1 and not parameters[1].altered and not parameters[1].value:
            try:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                if aprx.defaultGeodatabase:
                    parameters[1].value = aprx.defaultGeodatabase
            except Exception:
                pass
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each parameter."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        prompt = parameters[0].valueAsText
        workspace_path = parameters[1].valueAsText
        if not workspace_path:
            try:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                workspace_path = aprx.defaultGeodatabase or arcpy.env.workspace
            except Exception:
                pass
        auth_token = parameters[2].valueAsText if len(parameters) > 2 else None

        arcpy.AddMessage("=================================================")
        arcpy.AddMessage(f"  AntigravityGIS v{__version__} by Sounny — AI Copilot")
        arcpy.AddMessage("=================================================")

        # Check for updates in background
        if check_for_updates:
            update_info = check_for_updates()
            if update_info and update_info.get("update_available"):
                arcpy.AddWarning(
                    f"💡 Notice: New AntigravityGIS version v{update_info['latest_version']} is available! "
                    f"(Current: v{update_info['current_version']})\n"
                    f"To update, run in PowerShell: {update_info['update_command']}"
                )

        arcpy.AddWarning(
            "⚠️ AI & DATA PRIVACY NOTICE: Prompts and queries are processed by Google Antigravity. "
            "Avoid sharing personally identifiable information (PII), confidential, or unreleased data. "
            "Always verify AI-generated geoprocessing outputs before production use."
        )
        arcpy.AddMessage(f"User Prompt: {prompt}")


        if workspace_path:
            arcpy.AddMessage(f"Target Workspace: {workspace_path}")

        if auth_token:
            os.environ["ANTIGRAVITY_API_KEY"] = auth_token
            arcpy.AddMessage("Account: Custom Antigravity API Key applied.")
        else:
            arcpy.AddMessage("Account: Authenticating via active Google Antigravity account session...")
            if check_and_prompt_antigravity_login:

                auth_res = check_and_prompt_antigravity_login()
                if auth_res.get("status") != "authenticated":
                    arcpy.AddWarning(f"[AUTHENTICATION NOTICE] {auth_res.get('message')}")

        if GISAntigravityAgent is None:
            details = f" ({import_error_msg})" if import_error_msg else ""
            arcpy.AddError(
                f"Error: Could not import 'agent_core' or 'google-antigravity'{details}. "
                "Please run Install-AntigravityGIS.bat (or Install-AntigravityGIS.ps1) to install dependencies."
            )
            return

        # Initialize Antigravity GIS Agent
        agent_runner = GISAntigravityAgent(
            system_instructions=(
                "You are an AI GIS Assistant running directly inside ArcGIS Pro via your active Google Antigravity account. "
                "Help the user inspect datasets, analyze spatial features, execute ArcPy geoprocessing commands, "
                "and automate spatial workflows."
            )
        )

        # Register ArcPy tools with the Antigravity Agent
        agent_runner.register_tool(inspect_arcgis_workspace)
        agent_runner.register_tool(describe_arcgis_dataset)
        agent_runner.register_tool(run_arcpy_geoprocessing)
        agent_runner.register_tool(inspect_directory_spatial_data)

        # Log streaming buffer for ArcGIS Pro Geoprocessing messages window
        line_buffer = []

        def log_token(token: str):
            sys.stdout.write(token)
            line_buffer.append(token)
            if "\n" in token:
                msg = "".join(line_buffer).strip()
                if msg:
                    arcpy.AddMessage(msg)
                line_buffer.clear()

        # Execute async agent loop safely in any host environment
        try:
            full_prompt = prompt
            if workspace_path:
                full_prompt += f"\nTarget Workspace Path: {workspace_path}"

            arcpy.AddMessage("\n--- Processing with Antigravity Agent ---")

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    output_text = pool.submit(
                        asyncio.run, agent_runner.execute_prompt(full_prompt, token_callback=log_token)
                    ).result()
            else:
                output_text = asyncio.run(
                    agent_runner.execute_prompt(full_prompt, token_callback=log_token)
                )

            # Flush any remaining buffer
            if line_buffer:
                remaining = "".join(line_buffer).strip()
                if remaining:
                    arcpy.AddMessage(remaining)

            arcpy.AddMessage("\n=================================================")
            arcpy.AddMessage("  Antigravity GIS Task Completed Successfully")
            arcpy.AddMessage("=================================================")
        except Exception as e:
            arcpy.AddError(f"Antigravity Execution Failure: {str(e)}")


class ConfigureApiKeyTool(object):
    def __init__(self):
        """Define the tool (tool name and properties)."""
        self.label = "Set Google AI Studio API Key (Permanent)"
        self.category = "Sounny AI Tools"
        self.description = (
            "Saves your Google AI Studio API key permanently to your Windows user environment variables.\n\n"
            "Once saved, all AntigravityGIS tools will automatically use your key with 1,000+ requests/min quota without needing to type it in each time.\n\n"
            "🔑 Get your free API key at: https://aistudio.google.com/apikey"
        )
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions for the Geoprocessing Tool dialog."""
        param_key = arcpy.Parameter(
            displayName="Google AI Studio API Key (Get at https://aistudio.google.com/apikey)",
            name="api_key",
            datatype="GPStringHidden",
            parameterType="Required",
            direction="Input",
        )
        return [param_key]

    def isLicensable(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        api_key = parameters[0].valueAsText.strip() if parameters[0].valueAsText else ""
        if not api_key:
            arcpy.AddError("Error: API Key cannot be empty.")
            return

        arcpy.AddMessage("=================================================")
        arcpy.AddMessage("  AntigravityGIS — Permanent API Key Configuration")
        arcpy.AddMessage("=================================================")

        import subprocess
        try:
            # Set in active process memory
            os.environ["GEMINI_API_KEY"] = api_key
            os.environ["ANTIGRAVITY_API_KEY"] = api_key

            # Set permanently in Windows User Environment via powershell
            cmd = f"[System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', '{api_key}', 'User'); [System.Environment]::SetEnvironmentVariable('ANTIGRAVITY_API_KEY', '{api_key}', 'User')"
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, check=True)

            arcpy.AddMessage("✅ SUCCESS: Your Google AI Studio API Key has been saved permanently to your Windows User Environment!")
            arcpy.AddMessage("All AntigravityGIS tools will now run with high-throughput quota automatically without requiring key re-entry.")
            arcpy.AddMessage("=================================================")
        except Exception as e:
            arcpy.AddError(f"Failed to set Windows environment variable: {str(e)}")
