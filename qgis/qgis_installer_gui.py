"""
qgis_installer_gui.py - One-Click GUI Installer Executable for AntigravityGIS QGIS Plugin
Created by Sounny (sounny.com)
"""

import os
import sys
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox


def run_qgis_installation(log_func, progress_func):
    try:
        log_func("=================================================")
        log_func(" AntigravityGIS by Sounny — QGIS Plugin Setup")
        log_func("=================================================\n")

        progress_func(10)
        # 1. Locate QGIS Python environment
        qgis_paths = [
            r"C:\Program Files\QGIS 3.34\apps\Python312\python.exe",
            r"C:\Program Files\QGIS 3.28\apps\Python39\python.exe",
            r"C:\OSGeo4W\apps\Python39\python.exe",
            r"C:\OSGeo4W64\apps\Python39\python.exe"
        ]
        target_python = None
        for p in qgis_paths:
            if os.path.exists(p):
                target_python = p
                break

        if not target_python:
            target_python = sys.executable

        log_func(f"[OK] Target QGIS Python Environment: {target_python}")
        progress_func(30)

        # 2. Install google-antigravity SDK
        log_func("Installing google-antigravity SDK into QGIS Python environment...")
        res = subprocess.run([target_python, "-m", "pip", "install", "--upgrade", "google-antigravity", "protobuf"], capture_output=True, text=True)
        if res.returncode == 0:
            log_func("[OK] google-antigravity SDK installed successfully.")
        else:
            log_func(f"[NOTICE] Pip info: {res.stderr.strip()[:180]}")
        progress_func(65)

        # 3. Deploy QGIS Plugin
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        qgis_plugin_dir = os.path.join(appdata, "QGIS", "QGIS3", "profiles", "default", "python", "plugins", "AntigravityGIS")
        os.makedirs(qgis_plugin_dir, exist_ok=True)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.abspath(os.path.join(base_dir, ".."))
        if getattr(sys, 'frozen', False):
            base_dir = getattr(sys, '_MEIPASS', base_dir)
            parent_dir = base_dir

        core_file = os.path.join(parent_dir, "agent_core.py")
        if not os.path.exists(core_file):
            core_file = os.path.join(base_dir, "agent_core.py")

        version_file = os.path.join(parent_dir, "version.json")
        if not os.path.exists(version_file):
            version_file = os.path.join(base_dir, "version.json")

        deploy_files = [
            (core_file, "agent_core.py"),
            (version_file, "version.json"),
            (qgis_core_file, "qgis_agent_core.py"),
            (init_file, "__init__.py"),
            (metadata_file, "metadata.txt"),
            (plugin_file, "antigravitygis_plugin.py"),
        ]

        for src, dest_name in deploy_files:
            if os.path.exists(src):
                shutil.copy(src, os.path.join(qgis_plugin_dir, dest_name))
                log_func(f"  + Deployed {dest_name}")
            else:
                log_func(f"  - Warning: {dest_name} not found at {src}")

        log_func(f"[OK] Deployed QGIS Plugin to: {qgis_plugin_dir}")
        progress_func(100)

        log_func("\n=================================================")
        log_func(" SUCCESS: AntigravityGIS QGIS Plugin Installed!  ")
        log_func(" Open QGIS -> Plugins -> Manage Plugins -> Enable AntigravityGIS")
        log_func("=================================================")

    except Exception as e:
        log_func(f"\n[ERROR] QGIS Setup encountered an issue: {str(e)}")


class QGISInstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AntigravityGIS for QGIS — Setup")
        self.root.geometry("580x420")
        self.root.resizable(False, False)
        self.root.configure(bg="#0b0f19")

        header_frame = tk.Frame(root, bg="#0079c1", padx=15, pady=15)
        header_frame.pack(fill="x")

        title_lbl = tk.Label(header_frame, text="AntigravityGIS for QGIS", font=("Montserrat", 16, "bold"), fg="#ffffff", bg="#0079c1")
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(header_frame, text="1-Click PyQGIS Plugin & SDK Installer by Sounny", font=("Montserrat", 10), fg="#e0f2fe", bg="#0079c1")
        subtitle_lbl.pack(anchor="w")

        body_frame = tk.Frame(root, bg="#0b0f19", padx=15, pady=15)
        body_frame.pack(fill="both", expand=True)

        self.progress = ttk.Progressbar(body_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(0, 10))

        self.log_text = tk.Text(body_frame, bg="#090d16", fg="#34d399", font=("Consolas", 9), relief="solid", bd=1)
        self.log_text.pack(fill="both", expand=True, pady=(0, 10))

        self.terms_var = tk.BooleanVar(value=False)
        self.terms_cb = tk.Checkbutton(
            body_frame,
            text="I agree to the AntigravityGIS Terms and Conditions",
            variable=self.terms_var,
            command=self.toggle_install_btn,
            bg="#0b0f19",
            fg="#ffffff",
            selectcolor="#0b0f19"
        )
        self.terms_cb.pack(anchor="w", pady=(0, 5))

        btn_frame = tk.Frame(body_frame, bg="#0b0f19")
        btn_frame.pack(fill="x")

        self.install_btn = tk.Button(
            btn_frame, 
            text="Install Plugin Now", 
            font=("Montserrat", 10, "bold"), 
            bg="#0079c1", 
            fg="#ffffff", 
            activebackground="#005e95", 
            activeforeground="#ffffff", 
            relief="flat", 
            padx=15, 
            pady=6, 
            command=self.start_install,
            state="disabled"
        )
        self.install_btn.pack(side="right")

    def toggle_install_btn(self):
        if self.terms_var.get():
            self.install_btn.config(state="normal")
        else:
            self.install_btn.config(state="disabled")

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def set_progress(self, val):
        self.progress["value"] = val

    def start_install(self):
        self.install_btn.config(state="disabled")
        threading.Thread(target=run_qgis_installation, args=(self.log, self.set_progress), daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = QGISInstallerApp(root)
    root.mainloop()
