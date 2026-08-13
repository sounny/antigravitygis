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
        self.tools = [AntigravityAssistantTool]


class AntigravityAssistantTool(object):
    def __init__(self):
        """Define the tool (tool name and properties)."""
        self.label = "Antigravity AI Assistant (by Sounny)"
        self.category = "Sounny AI Tools"
        self.description = (
            "AntigravityGIS by Sounny - Interactive AI Copilot running on your Google Antigravity account "
            "for natural language geoprocessing, dataset inspection, and ArcPy workflow automation inside ArcGIS Pro.\n\n"
            "Created by Sounny (sounny.com).\n\n"
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
            displayName="Target Workspace / Geodatabase Path (Optional)",
            name="workspace_path",
            datatype="DEWorkspace",
            parameterType="Optional",
            direction="Input",
        )

        # Parameter 2: Antigravity Account Token / API Key (Optional)
        param_auth = arcpy.Parameter(
            displayName="Antigravity API Key / Token (Optional, defaults to active account session)",
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
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each parameter."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        prompt = parameters[0].valueAsText
        workspace_path = parameters[1].valueAsText
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
