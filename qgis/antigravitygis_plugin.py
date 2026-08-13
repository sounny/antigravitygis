# -*- coding: utf-8 -*-
"""
antigravitygis_plugin.py - QGIS Plugin UI for AntigravityGIS by Sounny
Created by Sounny (sounny.com)

Provides a dockable AI Copilot panel inside QGIS Desktop
powered by Google Antigravity.
"""

import asyncio
import os
import sys

from qgis.PyQt.QtWidgets import (
    QAction, QDockWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QWidget, QLabel
)
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal
from qgis.core import Qgis

# Ensure parent directory is in sys.path to locate agent_core
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from agent_core import GISAntigravityAgent
except ImportError:
    GISAntigravityAgent = None

try:
    from .qgis_agent_core import inspect_qgis_active_project, describe_qgis_layer
except ImportError:
    try:
        from qgis_agent_core import inspect_qgis_active_project, describe_qgis_layer
    except ImportError:
        inspect_qgis_active_project = None
        describe_qgis_layer = None


class AgentWorker(QThread):
    """Background thread to run the async Antigravity agent without blocking the QGIS UI."""
    token_received = pyqtSignal(str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, agent, prompt):
        super().__init__()
        self.agent = agent
        self.prompt = prompt

    def run(self):
        try:
            def on_token(token):
                self.token_received.emit(token)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.agent.execute_prompt(self.prompt, token_callback=on_token)
            )
            loop.close()
            self.finished_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))


class AntigravityGISPlugin:
    """Main QGIS Plugin class for AntigravityGIS by Sounny."""

    def __init__(self, iface):
        self.iface = iface
        self.dock_widget = None
        self.action = None
        self.agent = None
        self.worker = None

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
        layout.setContentsMargins(8, 8, 8, 8)

        # Header
        header = QLabel("AntigravityGIS AI Copilot")
        header.setStyleSheet("font-weight: bold; font-size: 14px; color: #0079c1; padding: 4px 0;")
        layout.addWidget(header)

        warning = QLabel(
            "AI & Data Privacy: Prompts are processed by Google Antigravity. "
            "Avoid sharing sensitive or confidential spatial data."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #d97706; font-size: 11px; padding: 4px 0 8px 0;")
        layout.addWidget(warning)

        # Output area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet(
            "background: #0d1117; color: #34d399; font-family: Consolas, monospace; "
            "font-size: 12px; border: 1px solid #30363d; border-radius: 4px; padding: 8px;"
        )
        self.output_text.setPlaceholderText("Agent output will appear here...")
        layout.addWidget(self.output_text)

        # Input row
        input_layout = QHBoxLayout()
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Enter a spatial analysis prompt...")
        self.prompt_input.setStyleSheet(
            "padding: 8px; border: 1px solid #e5e7eb; border-radius: 4px; font-size: 13px;"
        )
        self.prompt_input.returnPressed.connect(self.run_prompt)
        input_layout.addWidget(self.prompt_input)

        self.run_btn = QPushButton("Run")
        self.run_btn.setStyleSheet(
            "background: #0079c1; color: white; font-weight: bold; padding: 8px 16px; "
            "border: none; border-radius: 4px;"
        )
        self.run_btn.clicked.connect(self.run_prompt)
        input_layout.addWidget(self.run_btn)

        layout.addLayout(input_layout)
        container.setLayout(layout)
        self.dock_widget.setWidget(container)

    def run_prompt(self):
        """Execute the user's prompt through the Antigravity Agent."""
        prompt = self.prompt_input.text().strip()
        if not prompt:
            return

        if GISAntigravityAgent is None:
            self.output_text.append(
                "[ERROR] google-antigravity SDK not installed. "
                "Run the AntigravityGIS QGIS installer or pip install google-antigravity."
            )
            return

        # Initialize agent on first use
        if self.agent is None:
            self.agent = GISAntigravityAgent(
                system_instructions=(
                    "You are an AI GIS Assistant running inside QGIS Desktop via Google Antigravity. "
                    "Help the user inspect map layers, analyze spatial features, and automate PyQGIS workflows."
                )
            )
            if inspect_qgis_active_project:
                self.agent.register_tool(inspect_qgis_active_project)
            if describe_qgis_layer:
                self.agent.register_tool(describe_qgis_layer)

        self.output_text.append(f"\n> {prompt}\n")
        self.prompt_input.clear()
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Running...")

        # Run agent in background thread
        self.worker = AgentWorker(self.agent, prompt)
        self.worker.token_received.connect(self._on_token)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.error_signal.connect(self._on_error)
        self.worker.start()

    def _on_token(self, token):
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(token)
        self.output_text.setTextCursor(cursor)
        self.output_text.ensureCursorVisible()

    def _on_finished(self, result):
        self.output_text.append("\n[Task Complete]")
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run")

    def _on_error(self, error_msg):
        self.output_text.append(f"\n[ERROR] {error_msg}")
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run")
