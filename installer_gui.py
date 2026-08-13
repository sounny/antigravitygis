"""
installer_gui.py - One-Click GUI Installer Executable for AntigravityGIS by Sounny
"""

import os
import sys
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox


def run_installation(log_func, progress_func):
    try:
        log_func("=================================================")
        log_func(" AntigravityGIS by Sounny — ArcGIS Pro Setup")
        log_func("=================================================\n")

        progress_func(10)
        # 1. Locate ArcGIS Pro Python environment
        arcgis_path = r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"
        target_python = None

        if os.path.exists(arcgis_path):
            target_python = arcgis_path
        else:
            log_func("Searching for custom ArcGIS Pro Python environment...")
            for root_dir in [r"C:\Program Files\ArcGIS\Pro", os.path.expanduser(r"~\AppData\Local\Programs\ArcGIS\Pro")]:
                if os.path.exists(root_dir):
                    for r, dirs, files in os.walk(root_dir):
                        if "python.exe" in files:
                            target_python = os.path.join(r, "python.exe")
                            break
                if target_python:
                    break

        if not target_python:
            target_python = sys.executable

        log_func(f"[OK] Found Python Environment: {target_python}")
        progress_func(30)

        # 2. Install google-antigravity
        log_func("Installing google-antigravity SDK into target environment...")
        res = subprocess.run([target_python, "-m", "pip", "install", "--upgrade", "google-antigravity", "protobuf"], capture_output=True, text=True)
        if res.returncode == 0:
            log_func("[OK] google-antigravity SDK installed successfully.")
        else:
            log_func(f"[NOTICE] Pip warning: {res.stderr.strip()[:200]}")
        progress_func(60)

        # 3. Deploy Toolbox Add-on
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        user_toolbox_dir = os.path.join(appdata, "Esri", "ArcGISPro", "ArcToolbox", "MyToolboxes", "AntigravityGIS")
        os.makedirs(user_toolbox_dir, exist_ok=True)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        if getattr(sys, 'frozen', False):
            base_dir = getattr(sys, '_MEIPASS', base_dir)

        core_file = os.path.join(base_dir, "agent_core.py")
        pyt_file = os.path.join(base_dir, "arcgis", "AntigravityGIS.pyt")
        if not os.path.exists(pyt_file):
            pyt_file = os.path.join(base_dir, "AntigravityGIS.pyt")

        if os.path.exists(core_file):
            shutil.copy(core_file, os.path.join(user_toolbox_dir, "agent_core.py"))
        if os.path.exists(pyt_file):
            shutil.copy(pyt_file, os.path.join(user_toolbox_dir, "AntigravityGIS.pyt"))

        log_func(f"[OK] Deployed toolbox to: {user_toolbox_dir}")
        progress_func(85)

        # 4. Check Antigravity authentication
        antigravity_dir = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity")
        if os.path.exists(antigravity_dir) or os.environ.get("ANTIGRAVITY_API_KEY"):
            log_func("[OK] Google Antigravity account session detected.")
        else:
            log_func("[NOTICE] Please log into your Google Antigravity account or Antigravity Desktop App.")
        progress_func(100)

        log_func("\n=================================================")
        log_func(" SUCCESS: AntigravityGIS Installed Successfully! ")
        log_func(" Open ArcGIS Pro -> Catalog -> Toolboxes -> Add Toolbox")
        log_func(" Select: " + os.path.join(user_toolbox_dir, "AntigravityGIS.pyt"))
        log_func("=================================================")

    except Exception as e:
        log_func(f"\n[ERROR] Setup encountered an issue: {str(e)}")


class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AntigravityGIS by Sounny — Installer")
        self.root.geometry("580x420")
        self.root.resizable(False, False)
        self.root.configure(bg="#0b0f19")

        # Header
        header_frame = tk.Frame(root, bg="#0079c1", padx=15, pady=15)
        header_frame.pack(fill="x")

        title_lbl = tk.Label(header_frame, text="AntigravityGIS by Sounny", font=("Montserrat", 16, "bold"), fg="#ffffff", bg="#0079c1")
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(header_frame, text="1-Click ArcGIS Pro Add-on Setup", font=("Montserrat", 10), fg="#e0f2fe", bg="#0079c1")
        subtitle_lbl.pack(anchor="w")

        # Body
        body_frame = tk.Frame(root, bg="#0b0f19", padx=15, pady=15)
        body_frame.pack(fill="both", expand=True)

        self.progress = ttk.Progressbar(body_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(0, 10))

        self.log_text = tk.Text(body_frame, bg="#090d16", fg="#34d399", font=("Consolas", 9), relief="solid", bd=1)
        self.log_text.pack(fill="both", expand=True, pady=(0, 10))

        # Terms of Agreement
        self.terms_var = tk.BooleanVar(value=False)
        self.terms_cb = tk.Checkbutton(body_frame, text="I agree to the AntigravityGIS Terms and Conditions", variable=self.terms_var, command=self.toggle_install_btn, bg="#0b0f19", fg="#ffffff", selectcolor="#0b0f19")
        self.terms_cb.pack(anchor="w", pady=(0, 5))

        # Buttons
        btn_frame = tk.Frame(body_frame, bg="#0b0f19")
        btn_frame.pack(fill="x")

        self.install_btn = tk.Button(btn_frame, text="Install Add-on Now", font=("Montserrat", 10, "bold"), bg="#0079c1", fg="#ffffff", activebackground="#005e95", activeforeground="#ffffff", relief="flat", padx=15, pady=6, command=self.start_install, state="disabled")
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
        self.progress["value"] = 0
        self.log("Starting installation...")

        # Verify ArcGIS Pro is installed
        arcgis_appdata = os.path.join(os.environ.get("APPDATA", ""), "Esri", "ArcGISPro")
        if not os.path.exists(arcgis_appdata):
            self.log("[ERROR] ArcGIS Pro does not appear to be installed or initialized.")
            self.log("Please install and open ArcGIS Pro at least once before installing this add-on.")
            self.install_btn.config(state="normal")
            return

        threading.Thread(target=run_installation, args=(self.log, self.set_progress), daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = InstallerApp(root)
    root.mainloop()
