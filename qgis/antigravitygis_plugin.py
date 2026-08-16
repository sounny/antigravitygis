# -*- coding: utf-8 -*-
"""
antigravitygis_plugin.py - Next-Gen QGIS Plugin UI for AntigravityGIS by Sounny
Created by Sounny (sounny.com)

Provides a modern, dockable AI Copilot panel inside QGIS Desktop
powered by Google Antigravity, PyQGIS, and Google Gemini.
"""

import asyncio
import os
import sys
import re
import html

from qgis.PyQt.QtWidgets import (
    QAction, QDockWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QTextBrowser, QLineEdit, QPushButton, QWidget, QLabel,
    QComboBox, QInputDialog, QMessageBox, QFrame, QScrollArea
)
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal, QUrl
from qgis.PyQt.QtGui import QFont, QTextCursor
from qgis.core import Qgis, QgsSettings, QgsProject

# Ensure parent directory is in sys.path to locate agent_core
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
for p in [current_dir, parent_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from agent_core import GISAntigravityAgent, inspect_directory_spatial_data, format_graceful_error
except ImportError:
    GISAntigravityAgent = None
    inspect_directory_spatial_data = None
    format_graceful_error = None

try:
    from .qgis_agent_core import (
        inspect_qgis_active_project,
        describe_qgis_layer,
        run_pyqgis_code,
        zoom_to_qgis_layer,
        add_vector_layer_to_qgis,
        log_chat_to_qgis_project,
    )
except ImportError:
    try:
        from qgis_agent_core import (
            inspect_qgis_active_project,
            describe_qgis_layer,
            run_pyqgis_code,
            zoom_to_qgis_layer,
            add_vector_layer_to_qgis,
            log_chat_to_qgis_project,
        )
    except ImportError:
        inspect_qgis_active_project = None
        describe_qgis_layer = None
        run_pyqgis_code = None
        zoom_to_qgis_layer = None
        add_vector_layer_to_qgis = None
        log_chat_to_qgis_project = None


class PromptTextEdit(QTextEdit):
    """Multi-line text editor where Enter sends and Shift+Enter inserts newline."""
    returnPressed = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.returnPressed.emit()
        else:
            super().keyPressEvent(event)


class AgentWorker(QThread):
    """Background thread to run the async Antigravity agent without blocking QGIS UI."""
    token_received = pyqtSignal(str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, agent, prompt, model_name="gemini-2.5-flash"):
        super().__init__()
        self.agent = agent
        self.prompt = prompt
        self.model_name = model_name

    def run(self):
        try:
            def on_token(token):
                self.token_received.emit(token)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.agent.execute_prompt(self.prompt, token_callback=on_token, model=self.model_name)
            )
            loop.close()

            if log_chat_to_qgis_project:
                log_chat_to_qgis_project(self.prompt, result, self.model_name)

            self.finished_signal.emit(result)
        except Exception as e:
            err_msg = format_graceful_error(e) if format_graceful_error else str(e)
            self.error_signal.emit(err_msg)


class AntigravityGISPlugin:
    """Main QGIS Plugin class for AntigravityGIS by Sounny."""

    def __init__(self, iface):
        self.iface = iface
        self.dock_widget = None
        self.action = None
        self.agent = None
        self.worker = None
        self.current_model = "gemini-2.5-flash"
        self._auto_discover_api_key()

    def _auto_discover_api_key(self):
        """Auto-detects API key from QgsSettings or Windows Registry."""
        settings = QgsSettings()
        key = settings.value("AntigravityGIS/api_key", "")
        if key:
            os.environ["GEMINI_API_KEY"] = str(key)
            os.environ["ANTIGRAVITY_API_KEY"] = str(key)
            return

        if sys.platform == "win32":
            try:
                import winreg
                reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ)
                for var_name in ["GEMINI_API_KEY", "ANTIGRAVITY_API_KEY"]:
                    try:
                        val, _ = winreg.QueryValueEx(reg_key, var_name)
                        if val and val.strip():
                            os.environ[var_name] = val.strip()
                            break
                    except Exception:
                        pass
                winreg.CloseKey(reg_key)
            except Exception:
                pass

    def initGui(self):
        """Called by QGIS when the plugin UI should be initialized."""
        self.action = QAction("AntigravityGIS AI Copilot", self.iface.mainWindow())
        self.action.setStatusTip("Open the AntigravityGIS AI Copilot panel")
        self.action.triggered.connect(self.toggle_panel)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("AntigravityGIS", self.action)

    def unload(self):
        """Called by QGIS when the plugin is unloaded."""
        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget = None
        if self.action:
            self.iface.removePluginMenu("AntigravityGIS", self.action)
            self.iface.removeToolBarIcon(self.action)

    def toggle_panel(self):
        """Toggle the AI Copilot dock panel."""
        if self.dock_widget and self.dock_widget.isVisible():
            self.dock_widget.hide()
            return

        if not self.dock_widget:
            self._create_dock_widget()

        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
        self.dock_widget.show()

    def _create_dock_widget(self):
        """Build the AI Copilot dock widget UI."""
        self.dock_widget = QDockWidget("AntigravityGIS by Sounny", self.iface.mainWindow())
        self.dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Header Bar with Brand & Model Selector
        top_bar = QHBoxLayout()
        header_title = QLabel("AntigravityGIS")
        header_title.setStyleSheet("font-weight: 800; font-size: 15px; color: #0079c1;")
        top_bar.addWidget(header_title)

        top_bar.addStretch()

        # Model Selector Dropdown
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "⚡ Gemini 2.5 Flash",
            "🧠 Gemini 2.5 Pro",
            "🔮 Claude 3.7 Sonnet",
            "🚀 Gemini 2.0 Flash",
            "💭 Gemini 2.0 Flash Thinking",
            "🌟 Gemini 1.5 Pro"
        ])
        self.model_combo.setStyleSheet(
            "padding: 3px 8px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 11px;"
        )
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        top_bar.addWidget(self.model_combo)

        # API Key Settings Button
        self.key_btn = QPushButton("🔑")
        self.key_btn.setToolTip("Configure Google AI Studio API Key")
        self.key_btn.setStyleSheet(
            "padding: 3px 8px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 12px; background:#f8fafc;"
        )
        self.key_btn.clicked.connect(self._configure_api_key)
        top_bar.addWidget(self.key_btn)

        layout.addLayout(top_bar)

        # Privacy Warning Banner
        warning = QLabel(
            "⚠️ AI Copilot: Queries processed via Google Antigravity & PyQGIS."
        )
        warning.setStyleSheet("color: #d97706; font-size: 10px; font-weight: 500;")
        layout.addWidget(warning)

        # 2. Quick Action Chips Bar
        chips_layout = QHBoxLayout()
        chips = [
            ("📍 Layers", "Inspect all active map layers in this QGIS project"),
            ("🔍 Describe", "Describe schema and spatial reference of the active layer"),
            ("⚡ Buffer", "Generate PyQGIS code to buffer the selected layer by 10km"),
            ("📁 Data Scan", "Scan directory for spatial datasets and shapefiles"),
        ]
        for label, prompt in chips:
            btn = QPushButton(label)
            btn.setToolTip(prompt)
            btn.setStyleSheet(
                "background: #f1f5f9; color: #0f172a; border: 1px solid #e2e8f0; "
                "border-radius: 12px; padding: 3px 8px; font-size: 11px; font-weight: 600;"
            )
            btn.clicked.connect(lambda checked, p=prompt: self._on_chip_clicked(p))
            chips_layout.addWidget(btn)
        chips_layout.addStretch()
        layout.addLayout(chips_layout)

        # 3. Rich Chat Output Browser
        self.chat_browser = QTextBrowser()
        self.chat_browser.setOpenExternalLinks(False)
        self.chat_browser.anchorClicked.connect(self._handle_chat_link)
        self.chat_browser.setStyleSheet(
            "background: #ffffff; color: #1e293b; font-family: 'Segoe UI', sans-serif; "
            "font-size: 12px; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px;"
        )
        self.chat_browser.setHtml(
            "<div style='color:#64748b; font-size:12px;'>"
            "👋 <b>Welcome to AntigravityGIS AI Copilot for QGIS!</b><br>"
            "Ask questions, inspect active map layers, or request PyQGIS automation scripts."
            "</div>"
        )
        layout.addWidget(self.chat_browser)

        # 4. Multi-line Input Box with Shift+Enter Support
        self.prompt_input = PromptTextEdit()
        self.prompt_input.setPlaceholderText("Type a spatial instruction... (Enter to Send, Shift+Enter for newline)")
        self.prompt_input.setFixedHeight(65)
        self.prompt_input.setStyleSheet(
            "padding: 8px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 12px; background: #ffffff;"
        )
        self.prompt_input.returnPressed.connect(self.run_prompt)
        layout.addWidget(self.prompt_input)

        # 5. Bottom Action Controls
        bottom_bar = QHBoxLayout()
        self.clear_btn = QPushButton("Clear Chat")
        self.clear_btn.setStyleSheet(
            "background: transparent; color: #64748b; border: 1px solid #e2e8f0; "
            "border-radius: 4px; padding: 5px 12px; font-size: 11px;"
        )
        self.clear_btn.clicked.connect(self._clear_chat)
        bottom_bar.addWidget(self.clear_btn)

        bottom_bar.addStretch()

        self.run_btn = QPushButton("▶ Run AI Copilot")
        self.run_btn.setStyleSheet(
            "background: #0079c1; color: white; font-weight: bold; padding: 6px 18px; "
            "border: none; border-radius: 4px; font-size: 12px;"
        )
        self.run_btn.clicked.connect(self.run_prompt)
        bottom_bar.addWidget(self.run_btn)

        layout.addLayout(bottom_bar)
        container.setLayout(layout)
        self.dock_widget.setWidget(container)

    def _on_model_changed(self, index):
        models = [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "claude-3-7-sonnet",
            "gemini-2.0-flash",
            "gemini-2.0-flash-thinking",
            "gemini-1.5-pro"
        ]
        if index < len(models):
            self.current_model = models[index]
            if self.agent:
                self.agent.model = self.current_model

    def _configure_api_key(self):
        current_key = os.environ.get("GEMINI_API_KEY", "")
        key, ok = QInputDialog.getText(
            self.dock_widget,
            "Google AI Studio API Key",
            "Enter your free Google AI Studio API Key:\n(Get at https://aistudio.google.com/apikey)",
            QLineEdit.Normal,
            current_key
        )
        if ok and key.strip():
            api_key = key.strip()
            os.environ["GEMINI_API_KEY"] = api_key
            os.environ["ANTIGRAVITY_API_KEY"] = api_key
            settings = QgsSettings()
            settings.setValue("AntigravityGIS/api_key", api_key)
            if sys.platform == "win32":
                try:
                    import winreg
                    reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(reg_key, "GEMINI_API_KEY", 0, winreg.REG_EXPAND_SZ, api_key)
                    winreg.SetValueEx(reg_key, "ANTIGRAVITY_API_KEY", 0, winreg.REG_EXPAND_SZ, api_key)
                    winreg.CloseKey(reg_key)
                except Exception:
                    pass
            QMessageBox.information(self.dock_widget, "Saved", "API Key saved permanently!")

    def _on_chip_clicked(self, prompt: str):
        self.prompt_input.setPlainText(prompt)
        self.run_prompt()

    def _clear_chat(self):
        self.chat_browser.setHtml(
            "<div style='color:#64748b; font-size:12px;'>"
            "Chat cleared. Ready for your next spatial prompt."
            "</div>"
        )

    def run_prompt(self):
        """Execute the user's prompt through the Antigravity Agent."""
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            return

        if GISAntigravityAgent is None:
            self.chat_browser.append(
                "<div style='color:#ef4444; font-weight:bold;'>"
                "❌ [ERROR] google-antigravity SDK not installed. "
                "Run the AntigravityGIS QGIS installer or pip install google-antigravity."
                "</div>"
            )
            return

        # Initialize agent on first use
        if self.agent is None:
            self.agent = GISAntigravityAgent(
                model=self.current_model,
                system_instructions=(
                    "You are an AI GIS Assistant running inside QGIS Desktop via Google Antigravity and PyQGIS. "
                    "Help the user inspect map layers, analyze spatial features, run PyQGIS automation, "
                    "and execute processing algorithms on the active canvas."
                )
            )
            if inspect_qgis_active_project:
                self.agent.register_tool(inspect_qgis_active_project)
            if describe_qgis_layer:
                self.agent.register_tool(describe_qgis_layer)
            if run_pyqgis_code:
                self.agent.register_tool(run_pyqgis_code)
            if zoom_to_qgis_layer:
                self.agent.register_tool(zoom_to_qgis_layer)
            if add_vector_layer_to_qgis:
                self.agent.register_tool(add_vector_layer_to_qgis)
            if inspect_directory_spatial_data:
                self.agent.register_tool(inspect_directory_spatial_data)

        # Append User Bubble
        escaped_prompt = html.escape(prompt)
        user_html = (
            f"<div style='margin-top:12px; margin-bottom:8px;'>"
            f"<div style='background:#0079c1; color:#ffffff; padding:8px 12px; "
            f"border-radius:12px 12px 2px 12px; display:inline-block; font-weight:500;'>"
            f"{escaped_prompt}</div></div>"
        )
        self.chat_browser.append(user_html)
        self.prompt_input.clear()
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Thinking...")

        # Current assistant response accumulator
        self.current_ai_text = []

        # Run agent in background thread
        self.worker = AgentWorker(self.agent, prompt, model_name=self.current_model)
        self.worker.token_received.connect(self._on_token)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.error_signal.connect(self._on_error)
        self.worker.start()

    def _on_token(self, token):
        self.current_ai_text.append(token)

    def _on_finished(self, result):
        full_text = "".join(self.current_ai_text) or result
        formatted_html = self._format_ai_response(full_text)
        self.chat_browser.append(formatted_html)
        self.run_btn.setEnabled(True)
        self.run_btn.setText("▶ Run AI Copilot")

    def _on_error(self, error_msg):
        escaped_err = html.escape(error_msg).replace("\n", "<br>")
        err_html = (
            f"<div style='background:#fef2f2; border:1px solid #fecaca; color:#991b1b; "
            f"padding:8px 12px; border-radius:6px; margin:8px 0; font-size:11px;'>"
            f"{escaped_err}</div>"
        )
        self.chat_browser.append(err_html)
        self.run_btn.setEnabled(True)
        self.run_btn.setText("▶ Run AI Copilot")

    def _format_ai_response(self, text: str) -> str:
        """Formats markdown code blocks into rich HTML with 1-Click PyQGIS run links."""
        # Check if text is a diagnostic notice
        if any(k in text for k in ["⚠️", "🔑", "⏳", "⚡", "Notice:"]):
            escaped = html.escape(text).replace("\n", "<br>")
            return (
                f"<div style='background:#fffbeb; border:1px solid #fde68a; color:#92400e; "
                f"padding:10px 12px; border-radius:6px; margin:8px 0; font-size:11.5px;'>"
                f"{escaped}</div>"
            )

        # Parse Python code blocks ```python ... ```
        def replace_code(match):
            code = match.group(1).strip()
            escaped_code = html.escape(code)
            # Encode code for QUrl handler
            encoded_code = QUrl.toPercentEncoding(code).data().decode('utf-8')
            return (
                f"<div style='background:#0f172a; border:1px solid #334155; border-radius:6px; margin:8px 0;'>"
                f"<div style='background:#1e293b; color:#94a3b8; padding:4px 10px; font-size:10px; font-family:monospace; "
                f"display:flex; justify-content:space-between;'>"
                f"<span>PYTHON / PYQGIS</span>"
                f"<a href='runpyqgis:{encoded_code}' style='color:#38bdf8; text-decoration:none; font-weight:bold;'>▶ Run in PyQGIS</a>"
                f"</div>"
                f"<pre style='margin:0; padding:10px; color:#34d399; font-family:Consolas, monospace; font-size:11px; "
                f"white-space:pre-wrap; overflow-x:auto;'>{escaped_code}</pre>"
                f"</div>"
            )

        processed = re.sub(r'```(?:python)?\s*\n(.*?)```', replace_code, text, flags=re.DOTALL)
        
        # Format remaining newlines
        processed_lines = []
        in_pre = False
        for part in processed.split("<pre"):
            if not in_pre:
                processed_lines.append(part.replace("\n", "<br>"))
                in_pre = True
            else:
                subparts = part.split("</pre>")
                processed_lines.append("<pre" + subparts[0] + "</pre>" + (subparts[1].replace("\n", "<br>") if len(subparts) > 1 else ""))

        html_body = "".join(processed_lines)
        return (
            f"<div style='background:#f8fafc; border:1px solid #e2e8f0; color:#0f172a; "
            f"padding:10px 12px; border-radius:12px 12px 12px 2px; margin:6px 0; line-height:1.5;'>"
            f"{html_body}</div>"
        )

    def _handle_chat_link(self, url: QUrl):
        url_str = url.toString()
        if url_str.startswith("runpyqgis:"):
            raw_code = url_str[len("runpyqgis:"):]
            code = QUrl.fromPercentEncoding(raw_code.encode('utf-8'))
            if run_pyqgis_code:
                result = run_pyqgis_code(code)
                self.chat_browser.append(
                    f"<div style='color:#059669; font-size:11px; font-weight:bold; margin:4px 0;'>{result}</div>"
                )
            else:
                QMessageBox.warning(self.dock_widget, "Notice", "PyQGIS execution tool not available.")
