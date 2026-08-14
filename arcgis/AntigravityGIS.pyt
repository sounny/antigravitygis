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
        self.tools = [LaunchChatGuiTool, AntigravityAssistantTool, ConfigureApiKeyTool]


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
            os.environ["GEMINI_API_KEY"] = auth_token
            arcpy.AddMessage("Account: Custom Google AI Studio API Key applied.")
        else:
            # Auto-detect permanent key from Windows Registry if not passed in parameter
            discovered_key = None
            if sys.platform == "win32":
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

            if discovered_key:
                arcpy.AddMessage("Account: Authenticated via permanent Google AI Studio API Key.")
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
                        asyncio.run, agent_runner.execute_prompt(full_prompt, token_callback=log_token, workspace=workspace_path)
                    ).result()
            else:
                output_text = asyncio.run(
                    agent_runner.execute_prompt(full_prompt, token_callback=log_token, workspace=workspace_path)
                )

            # Flush any remaining buffer
            if line_buffer:
                remaining = "".join(line_buffer).strip()
                if remaining:
                    arcpy.AddMessage(remaining)

            is_notice = any(k in output_text for k in ["⚠️", "🔑", "Notice:", "Required]"])
            arcpy.AddMessage("\n=================================================")
            if is_notice:
                arcpy.AddWarning("  Antigravity GIS Task Completed with Notice")
            else:
                arcpy.AddMessage("  Antigravity GIS Task Completed Successfully")
            arcpy.AddMessage("=================================================")
        except Exception as e:
            from agent_core import format_graceful_error
            arcpy.AddWarning(format_graceful_error(e))


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
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        # Prepopulate with existing key if set
        existing = os.environ.get("GEMINI_API_KEY") or os.environ.get("ANTIGRAVITY_API_KEY")
        if not existing and sys.platform == "win32":
            try:
                import winreg
                reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ)
                for var_name in ["GEMINI_API_KEY", "ANTIGRAVITY_API_KEY"]:
                    try:
                        val, _ = winreg.QueryValueEx(reg_key, var_name)
                        if val and val.strip():
                            existing = val.strip()
                            break
                    except Exception:
                        pass
                winreg.CloseKey(reg_key)
            except Exception:
                pass
        if existing:
            param_key.value = existing
        return [param_key]

    def isLicensable(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        api_key = parameters[0].valueAsText
        if not api_key:
            arcpy.AddError("Error: API Key cannot be empty.")
            return

        arcpy.AddMessage("=================================================")
        arcpy.AddMessage("  AntigravityGIS — Permanent API Key Configuration")
        arcpy.AddMessage("=================================================")

        try:
            # Set in active process memory
            os.environ["GEMINI_API_KEY"] = api_key
            os.environ["ANTIGRAVITY_API_KEY"] = api_key

            # Set permanently in Windows User Environment via native Windows Registry (zero console windows)
            if sys.platform == "win32":
                import winreg
                reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(reg_key, "GEMINI_API_KEY", 0, winreg.REG_EXPAND_SZ, api_key)
                winreg.SetValueEx(reg_key, "ANTIGRAVITY_API_KEY", 0, winreg.REG_EXPAND_SZ, api_key)
                winreg.CloseKey(reg_key)

            arcpy.AddMessage("✅ SUCCESS: Your Google AI Studio API Key has been saved permanently to your Windows User Environment!")
            arcpy.AddMessage("All AntigravityGIS tools will now run with high-throughput quota automatically without requiring key re-entry.")
            arcpy.AddMessage("=================================================")
        except Exception as e:
            arcpy.AddError(f"Failed to set Windows environment variable: {str(e)}")


class LaunchChatGuiTool(object):
    def __init__(self):
        """Define the tool (tool name and properties)."""
        self.label = "Launch Antigravity AI Chat Dialog"
        self.category = "Sounny AI Tools"
        self.description = (
            "Opens the interactive Antigravity AI Copilot Chat Dialog for ArcGIS Pro.\n\n"
            "Features:\n"
            "• Interactive conversational chat feed with speech bubbles\n"
            "• 1-Click '▶ Run in ArcPy' code block execution directly in your map view\n"
            "• Dynamic Model Engine switching (Gemini 2.5 Flash / Gemini 2.5 Pro)\n"
            "• Multi-turn memory, direct map drawing, and automatic geodatabase audit logging"
        )
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define rich, interactive parameters for the Geoprocessing Tool dialog."""
        # 0. Initial Prompt (Optional)
        param_prompt = arcpy.Parameter(
            displayName="Initial Prompt / Question (Optional)",
            name="initial_prompt",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        param_prompt.value = ""

        # 1. Model Engine Selector
        param_model = arcpy.Parameter(
            displayName="AI Model Engine",
            name="model_engine",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        param_model.filter.type = "ValueList"
        param_model.filter.list = [
            "⚡ Gemini 2.5 Flash (Fast Spatial)",
            "🧠 Gemini 2.5 Pro (Deep Spatial Reasoning)",
            "🚀 Gemini 2.0 Flash",
        ]
        param_model.value = "⚡ Gemini 2.5 Flash (Fast Spatial)"

        # 2. Interface Theme
        param_theme = arcpy.Parameter(
            displayName="Interface Theme",
            name="ui_theme",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        param_theme.filter.type = "ValueList"
        param_theme.filter.list = [
            "ArcGIS Pro Light (Calcite Default)",
            "ArcGIS Pro Dark (Titanium)",
        ]
        param_theme.value = "ArcGIS Pro Light (Calcite Default)"

        # 3. Target Workspace
        param_workspace = arcpy.Parameter(
            displayName="Target Geodatabase / Workspace (Defaults to Active Project)",
            name="workspace_path",
            datatype="DEWorkspace",
            parameterType="Optional",
            direction="Input",
        )
        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            if aprx and aprx.defaultGeodatabase:
                param_workspace.value = aprx.defaultGeodatabase
        except Exception:
            pass

        # 4. Optional API Key Override
        param_key = arcpy.Parameter(
            displayName="Google AI Studio API Key (Optional — auto-loads permanent key)",
            name="api_key",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        return [param_prompt, param_model, param_theme, param_workspace, param_key]

    def isLicensable(self):
        return True

    def updateParameters(self, parameters):
        """Auto-populate default workspace if available."""
        if len(parameters) > 3 and not parameters[3].value:
            try:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                if aprx and aprx.defaultGeodatabase:
                    parameters[3].value = aprx.defaultGeodatabase
            except Exception:
                pass
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        initial_prompt = parameters[0].valueAsText if len(parameters) > 0 and parameters[0].valueAsText else ""
        raw_model = parameters[1].valueAsText if len(parameters) > 1 and parameters[1].valueAsText else "flash"
        raw_theme = parameters[2].valueAsText if len(parameters) > 2 and parameters[2].valueAsText else "light"
        workspace_path = parameters[3].valueAsText if len(parameters) > 3 and parameters[3].valueAsText else ""
        custom_key = parameters[4].valueAsText if len(parameters) > 4 and parameters[4].valueAsText else ""

        model_code = "gemini-2.5-flash"
        if "Pro" in raw_model:
            model_code = "gemini-2.5-pro"
        elif "2.0" in raw_model:
            model_code = "gemini-2.0-flash"

        theme_code = "dark" if "Dark" in raw_theme else "light"

        arcpy.AddMessage("=================================================")
        arcpy.AddMessage("  Launching Antigravity AI Copilot Chat Dialog")
        arcpy.AddMessage(f"  Model: {model_code} | Theme: {theme_code}")
        arcpy.AddMessage("=================================================")

        import subprocess

        current_folder = os.path.dirname(os.path.abspath(__file__))
        chat_script = os.path.join(current_folder, "chat_gui.py")
        if not os.path.exists(chat_script):
            chat_script = os.path.join(os.path.dirname(current_folder), "chat_gui.py")

        if not os.path.exists(chat_script):
            arcpy.AddError(f"Could not locate chat_gui.py in {current_folder}. Please run update.")
            return

        # Find windowless Python executable (pythonw.exe) strictly
        pythonw_candidates = [
            os.path.expanduser(r"~\AppData\Local\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\pythonw.exe"),
            r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\pythonw.exe",
            os.path.join(sys.prefix, "pythonw.exe"),
            os.path.join(sys.exec_prefix, "pythonw.exe"),
            os.path.join(os.path.dirname(sys.executable), "pythonw.exe"),
        ]
        target_bin = None
        for cand in pythonw_candidates:
            if os.path.exists(cand):
                target_bin = cand
                break
        if not target_bin:
            target_bin = sys.executable.replace("python.exe", "pythonw.exe")

        script_dir = os.path.dirname(chat_script)
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{script_dir};{env.get('PYTHONPATH', '')}"

        cmd_args = [
            target_bin,
            chat_script,
            "--model", model_code,
            "--theme", theme_code,
        ]
        if initial_prompt:
            cmd_args.extend(["--prompt", initial_prompt])
        if workspace_path:
            cmd_args.extend(["--workspace", workspace_path])
        if custom_key:
            cmd_args.extend(["--key", custom_key])

        si = None
        creation_flags = 0
        if sys.platform == "win32":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0  # SW_HIDE
            # CREATE_NO_WINDOW (0x08000000) | CREATE_NEW_PROCESS_GROUP (0x00000200) | DETACHED_PROCESS (0x00000008)
            creation_flags = 0x08000000 | 0x00000200 | 0x00000008

        subprocess.Popen(
            cmd_args,
            cwd=script_dir,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=si,
            creationflags=creation_flags,
            close_fds=True if sys.platform != "win32" else False,
        )

        arcpy.AddMessage(f"✅ Launched Antigravity AI Copilot Chat Dialog silently!")
        arcpy.AddMessage("=================================================")
