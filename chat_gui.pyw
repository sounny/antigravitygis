# -*- coding: utf-8 -*-
"""
chat_gui.py - Antigravity AI Copilot (ArcGIS Pro Native Calcite Theme)

A conversational AI Assistant designed to match the native look and feel of Esri ArcGIS Pro.
Features:
- Native ArcGIS Pro Calcite / Fluent Light Theme (with Dark Mode toggle)
- Multi-turn conversation memory
- Token streaming animation
- Code blocks with 1-click 'Copy' and '▶ Run in ArcPy' execution
- Live project geodatabase & active map layer detection
- Automatic persistent session logging in ArcGIS Pro Geodatabase & Markdown
"""

import asyncio
import datetime
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import subprocess

# Ensure current and parent dirs are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
for d in [current_dir, parent_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from agent_core import (
    GISAntigravityAgent,
    __version__,
    execute_arcpy_code_snippet,
    log_chat_to_geodatabase,
)

# -------------------------------------------------------------
# ArcGIS Pro Native Calcite Theme Palettes
# -------------------------------------------------------------
THEMES = {
    "light": {
        "bg_main": "#F1F5F9",       # Soft light gray map canvas background
        "bg_sidebar": "#F8FAFC",    # ArcGIS Pro Catalog pane gray
        "bg_header": "#FFFFFF",     # Crisp ArcGIS Pro Ribbon white
        "bg_panel": "#FFFFFF",      # Card panels
        "bg_input": "#FFFFFF",      # Clean white input well
        "bg_code": "#1E293B",       # Monospace code slate
        "border": "#E2E8F0",        # Subtle Esri divider border
        "border_dark": "#CBD5E1",   # Medium border
        "text_main": "#0F172A",     # Deep dark slate text
        "text_muted": "#64748B",    # Muted label gray
        "text_header": "#1E293B",   # Header bold text
        "esri_blue": "#0079C1",     # Official Esri Calcite Blue
        "esri_blue_hover": "#005E95",
        "esri_blue_light": "#E0F2FE",
        "esri_green": "#059669",    # Success emerald
        "esri_cyan": "#0284C7",
        "user_bubble": "#E0F2FE",   # Esri Light Blue user bubble
        "user_border": "#BAE6FD",
        "ai_bubble": "#FFFFFF",     # Crisp white AI bubble
        "ai_border": "#E2E8F0",
        "chip_bg": "#FFFFFF",
        "chip_hover": "#F1F5F9",
    },
    "dark": {
        "bg_main": "#090D16",
        "bg_sidebar": "#0F172A",
        "bg_header": "#1E293B",
        "bg_panel": "#1E293B",
        "bg_input": "#0B1120",
        "bg_code": "#030712",
        "border": "#334155",
        "border_dark": "#475569",
        "text_main": "#F8FAFC",
        "text_muted": "#94A3B8",
        "text_header": "#F8FAFC",
        "esri_blue": "#38BDF8",
        "esri_blue_hover": "#0284C7",
        "esri_blue_light": "#0369A1",
        "esri_green": "#10B981",
        "esri_cyan": "#06B6D4",
        "user_bubble": "#0369A1",
        "user_border": "#0284C7",
        "ai_bubble": "#1E293B",
        "ai_border": "#334155",
        "chip_bg": "#1E293B",
        "chip_hover": "#334155",
    }
}


class AntigravityArcGISProChatApp:
    def __init__(
        self,
        root: tk.Tk,
        initial_prompt: Optional[str] = None,
        model: Optional[str] = None,
        theme: Optional[str] = None,
        workspace: Optional[str] = None,
    ):
        self.root = root
        self.root.title(f"Antigravity AI Copilot (v{__version__}) — ArcGIS Pro")
        self.root.geometry("980x760")
        self.root.minsize(740, 560)

        self.current_theme = theme if theme in THEMES else "light"
        self.t = THEMES[self.current_theme]
        self.root.configure(bg=self.t["bg_main"])

        model_name = model or "gemini-2.5-flash"
        self.selected_model = tk.StringVar(value=model_name)
        self.agent = GISAntigravityAgent(model=model_name)
        self.is_processing = False
        self.stop_requested = False
        self.active_gdb = workspace or ""
        self.active_map_name = ""

        self._build_ui()
        self._refresh_arcgis_context()

        # Update combobox to match initial model
        for i, val in enumerate(self.model_combo["values"]):
            if model_name in val:
                self.model_combo.current(i)
                break

        # If an initial prompt was provided from the Geoprocessing pane, run it automatically
        if initial_prompt and initial_prompt.strip():
            self.root.after(300, lambda p=initial_prompt.strip(): self._auto_execute_prompt(p))

    def _auto_execute_prompt(self, prompt: str):
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", prompt)
        self._on_send()

    def _build_ui(self):
        t = self.t

        # Master Container
        self.main_container = tk.Frame(self.root, bg=t["bg_main"])
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # ----------------------------------------------------
        # 1. LEFT SIDEBAR (ArcGIS Pro Catalog Pane Style)
        # ----------------------------------------------------
        self.sidebar = tk.Frame(
            self.main_container,
            bg=t["bg_sidebar"],
            width=290,
            padx=14,
            pady=14,
            highlightbackground=t["border"],
            highlightthickness=1,
        )
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Brand Header with Esri Diamond Icon
        brand_frame = tk.Frame(self.sidebar, bg=t["bg_sidebar"])
        brand_frame.pack(fill=tk.X, pady=(0, 14))

        tk.Label(
            brand_frame,
            text="🔷 AntigravityGIS",
            font=("Segoe UI", 12, "bold"),
            fg=t["text_header"],
            bg=t["bg_sidebar"],
        ).pack(anchor="w")

        tk.Label(
            brand_frame,
            text=f"ArcGIS Pro AI Copilot v{__version__}",
            font=("Segoe UI", 8),
            fg=t["esri_blue"],
            bg=t["bg_sidebar"],
        ).pack(anchor="w")

        # Model Selector Dropdown
        tk.Label(
            self.sidebar,
            text="AI MODEL ENGINE",
            font=("Segoe UI", 7, "bold"),
            fg=t["text_muted"],
            bg=t["bg_sidebar"],
        ).pack(anchor="w", pady=(6, 4))

        models = [
            ("⚡ Gemini 2.5 Flash (Fast Spatial)", "gemini-2.5-flash"),
            ("🧠 Gemini 2.5 Pro (Deep Reasoning)", "gemini-2.5-pro"),
            ("🚀 Gemini 2.0 Flash", "gemini-2.0-flash"),
        ]

        self.model_combo = ttk.Combobox(
            self.sidebar,
            values=[m[0] for m in models],
            state="readonly",
            font=("Segoe UI", 9),
        )
        self.model_combo.current(0)
        self.model_combo.pack(fill=tk.X, pady=(0, 12))
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_changed)

        # Active Project Context Card
        tk.Label(
            self.sidebar,
            text="PROJECT CONTEXT",
            font=("Segoe UI", 7, "bold"),
            fg=t["text_muted"],
            bg=t["bg_sidebar"],
        ).pack(anchor="w", pady=(4, 4))

        self.context_card = tk.Frame(
            self.sidebar,
            bg=t["bg_panel"],
            padx=10,
            pady=10,
            highlightbackground=t["border"],
            highlightthickness=1,
        )
        self.context_card.pack(fill=tk.X, pady=(0, 14))

        self.lbl_gdb = tk.Label(
            self.context_card,
            text="📂 GDB: Detecting...",
            font=("Segoe UI", 8),
            fg=t["text_main"],
            bg=t["bg_panel"],
            anchor="w",
            wraplength=240,
            justify=tk.LEFT,
        )
        self.lbl_gdb.pack(fill=tk.X)

        self.lbl_map = tk.Label(
            self.context_card,
            text="🗺️ Map: Detecting...",
            font=("Segoe UI", 8, "bold"),
            fg=t["esri_blue"],
            bg=t["bg_panel"],
            anchor="w",
        )
        self.lbl_map.pack(fill=tk.X, pady=(4, 0))

        # Quick Actions Header
        tk.Label(
            self.sidebar,
            text="GEOPROCESSING ACTIONS",
            font=("Segoe UI", 7, "bold"),
            fg=t["text_muted"],
            bg=t["bg_sidebar"],
        ).pack(anchor="w", pady=(4, 4))

        presets = [
            ("📍 Pin Austin, TX", "Make a point for Austin Texas and add it to my active map"),
            ("⭕ 10km Buffer Layer", "Buffer the active point layer by 10 Kilometers and add the result to map"),
            ("📊 Inspect GDB Datasets", "Inspect all feature classes and tables in the default project geodatabase"),
            ("🗺️ Summarize Map Layers", "Describe all layers, field schemas, and spatial reference of the current map"),
            ("📜 Open Chat History (.md)", "__OPEN_HISTORY__"),
            ("🔑 Configure API Key", "__CONFIG_KEY__"),
            ("🧹 Clear Conversation", "__CLEAR_CHAT__"),
        ]

        for label, cmd in presets:
            btn = tk.Button(
                self.sidebar,
                text=label,
                font=("Segoe UI", 8),
                fg=t["text_main"],
                bg=t["chip_bg"],
                activebackground=t["chip_hover"],
                activeforeground=t["text_main"],
                relief=tk.SOLID,
                borderwidth=1,
                highlightbackground=t["border"],
                anchor="w",
                padx=8,
                pady=5,
                cursor="hand2",
                command=lambda c=cmd: self._handle_sidebar_action(c),
            )
            btn.pack(fill=tk.X, pady=2)

        # ----------------------------------------------------
        # 2. RIGHT CHAT AREA
        # ----------------------------------------------------
        self.chat_area = tk.Frame(self.main_container, bg=t["bg_main"])
        self.chat_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Ribbon Header Bar
        self.top_header = tk.Frame(
            self.chat_area,
            bg=t["bg_header"],
            height=50,
            padx=16,
            pady=10,
            highlightbackground=t["border"],
            highlightthickness=1,
        )
        self.top_header.pack(fill=tk.X, side=tk.TOP)

        self.status_title = tk.Label(
            self.top_header,
            text="ArcGIS Pro AI Copilot",
            font=("Segoe UI", 11, "bold"),
            fg=t["text_header"],
            bg=t["bg_header"],
        )
        self.status_title.pack(side=tk.LEFT)

        # Right Controls: Theme Toggle + Status Indicator
        self.theme_btn = tk.Button(
            self.top_header,
            text="🌙 Dark Mode" if self.current_theme == "light" else "☀️ Light Mode",
            font=("Segoe UI", 8),
            fg=t["text_main"],
            bg=t["bg_sidebar"],
            activebackground=t["border"],
            relief=tk.SOLID,
            borderwidth=1,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._toggle_theme,
        )
        self.theme_btn.pack(side=tk.RIGHT, padx=(10, 0))

        self.status_dot = tk.Label(
            self.top_header,
            text="● Ready (Gemini 2.5 Flash)",
            font=("Segoe UI", 9, "bold"),
            fg=t["esri_green"],
            bg=t["bg_header"],
        )
        self.status_dot.pack(side=tk.RIGHT)

        # Scrollable Chat Stream Canvas
        self.chat_container = tk.Frame(self.chat_area, bg=t["bg_main"], padx=16, pady=8)
        self.chat_container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.chat_container, bg=t["bg_main"], highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.chat_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.feed_frame = tk.Frame(self.canvas, bg=t["bg_main"])

        self.feed_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.feed_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Welcome Speech Bubble
        self._add_ai_bubble(
            "👋 Welcome to **AntigravityGIS AI Copilot**!\n\n"
            "I have direct access to your active **ArcGIS Pro** map canvas, project geodatabase, and ArcPy tools.\n\n"
            "• Ask me to pin coordinates or cities (`make a point for Austin Texas`)\n"
            "• Ask me to run spatial analysis (`buffer Point_Austin by 10 km`)\n"
            "• Ask me to inspect your geodatabase schema and count records\n"
            "• All conversations and actions are automatically logged to your project geodatabase!"
        )

        # ----------------------------------------------------
        # 3. BOTTOM INPUT PANEL (ArcGIS Pro Fluent Input Well)
        # ----------------------------------------------------
        self.input_panel = tk.Frame(
            self.chat_area,
            bg=t["bg_header"],
            padx=16,
            pady=12,
            highlightbackground=t["border"],
            highlightthickness=1,
        )
        self.input_panel.pack(fill=tk.X, side=tk.BOTTOM)

        # Multi-line Text Box
        self.input_text = tk.Text(
            self.input_panel,
            height=3,
            bg=t["bg_input"],
            fg=t["text_main"],
            insertbackground=t["esri_blue"],
            font=("Segoe UI", 10),
            relief=tk.SOLID,
            borderwidth=1,
            highlightbackground=t["border_dark"],
            padx=12,
            pady=10,
            wrap=tk.WORD,
        )
        self.input_text.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 10))
        self.input_text.bind("<Return>", self._on_enter_pressed)

        # Action Buttons
        btn_box = tk.Frame(self.input_panel, bg=t["bg_header"])
        btn_box.pack(side=tk.RIGHT)

        self.send_btn = tk.Button(
            btn_box,
            text="Send  ➔",
            font=("Segoe UI", 10, "bold"),
            fg="#FFFFFF",
            bg=t["esri_blue"],
            activebackground=t["esri_blue_hover"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=18,
            pady=10,
            cursor="hand2",
            command=self._on_send,
        )
        self.send_btn.pack(fill=tk.X, pady=(0, 4))

        self.stop_btn = tk.Button(
            btn_box,
            text="⏹ Stop",
            font=("Segoe UI", 8),
            fg=t["text_muted"],
            bg=t["bg_sidebar"],
            activebackground=t["border"],
            relief=tk.SOLID,
            borderwidth=1,
            state=tk.DISABLED,
            command=self._on_stop,
        )
        self.stop_btn.pack(fill=tk.X)

    def _toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.t = THEMES[self.current_theme]
        t = self.t

        self.root.configure(bg=t["bg_main"])
        self.main_container.configure(bg=t["bg_main"])
        self.sidebar.configure(bg=t["bg_sidebar"], highlightbackground=t["border"])
        self.chat_area.configure(bg=t["bg_main"])
        self.top_header.configure(bg=t["bg_header"], highlightbackground=t["border"])
        self.status_title.configure(fg=t["text_header"], bg=t["bg_header"])
        self.status_dot.configure(bg=t["bg_header"])
        self.theme_btn.configure(
            text="🌙 Dark Mode" if self.current_theme == "light" else "☀️ Light Mode",
            fg=t["text_main"],
            bg=t["bg_sidebar"],
        )
        self.chat_container.configure(bg=t["bg_main"])
        self.canvas.configure(bg=t["bg_main"])
        self.feed_frame.configure(bg=t["bg_main"])
        self.input_panel.configure(bg=t["bg_header"], highlightbackground=t["border"])
        self.input_text.configure(
            bg=t["bg_input"],
            fg=t["text_main"],
            insertbackground=t["esri_blue"],
            highlightbackground=t["border_dark"],
        )
        self.context_card.configure(bg=t["bg_panel"], highlightbackground=t["border"])
        self.lbl_gdb.configure(fg=t["text_main"], bg=t["bg_panel"])
        self.lbl_map.configure(fg=t["esri_blue"], bg=t["bg_panel"])
        self.send_btn.configure(bg=t["esri_blue"], activebackground=t["esri_blue_hover"])
        self.stop_btn.configure(bg=t["bg_sidebar"], fg=t["text_muted"])

    def _refresh_arcgis_context(self):
        try:
            import arcpy
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            gdb = aprx.defaultGeodatabase or arcpy.env.workspace or "Default.gdb"
            active_map = aprx.activeMap.name if aprx.activeMap else "None"
            self.active_gdb = gdb
            self.active_map_name = active_map
            self.lbl_gdb.config(text=f"📂 GDB: {os.path.basename(gdb)}")
            self.lbl_map.config(text=f"🗺️ Map: {active_map}")
        except Exception:
            self.lbl_gdb.config(text="📂 Standalone / Python Mode")
            self.lbl_map.config(text="🗺️ Map: Ready")

    def _on_model_changed(self, event=None):
        raw_val = self.model_combo.get()
        model_id = "gemini-2.5-flash"
        if "Pro" in raw_val:
            model_id = "gemini-2.5-pro"
        elif "2.0" in raw_val:
            model_id = "gemini-2.0-flash"
        self.selected_model.set(model_id)
        self.agent = GISAntigravityAgent(model=model_id)
        self.status_dot.config(text=f"● Ready ({model_id})", fg=self.t["esri_green"])

    def _handle_sidebar_action(self, cmd: str):
        if cmd == "__OPEN_HISTORY__":
            self._open_history_file()
        elif cmd == "__CONFIG_KEY__":
            self._open_key_dialog()
        elif cmd == "__CLEAR_CHAT__":
            self._clear_chat()
        else:
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", cmd)
            self._on_send()

    def _open_history_file(self):
        candidate_paths = [
            os.path.join(os.path.dirname(self.active_gdb), "Antigravity_Chat_History.md") if self.active_gdb else None,
            os.path.expanduser(r"~\Documents\ArcGIS\Projects\AntigravityGIS\Antigravity_Chat_History.md"),
            os.path.join(os.getcwd(), "Antigravity_Chat_History.md"),
        ]
        found = False
        for p in candidate_paths:
            if p and os.path.exists(p):
                try:
                    os.startfile(p)
                except Exception:
                    pass
                found = True
                break
        if not found:
            messagebox.showinfo("History Log", "Chat history will be created upon your first prompt execution.")

    def _open_key_dialog(self):
        t = self.t
        win = tk.Toplevel(self.root)
        win.title("Configure Google AI Studio Key")
        win.geometry("480x240")
        win.configure(bg=t["bg_panel"])
        win.resizable(False, False)

        tk.Label(
            win,
            text="🔑 Google AI Studio API Key",
            font=("Segoe UI", 11, "bold"),
            fg=t["text_header"],
            bg=t["bg_panel"],
        ).pack(anchor="w", padx=20, pady=(16, 4))

        tk.Label(
            win,
            text="Get your free high-speed key at https://aistudio.google.com/apikey",
            font=("Segoe UI", 8),
            fg=t["esri_blue"],
            bg=t["bg_panel"],
        ).pack(anchor="w", padx=20, pady=(0, 12))

        entry = tk.Entry(win, font=("Segoe UI", 10), bg=t["bg_input"], fg=t["text_main"], show="*")
        entry.pack(fill=tk.X, padx=20, pady=4)
        if os.environ.get("GEMINI_API_KEY"):
            entry.insert(0, os.environ["GEMINI_API_KEY"])

        def save():
            val = entry.get().strip()
            if not val:
                messagebox.showerror("Error", "Please enter an API Key.")
                return
            os.environ["GEMINI_API_KEY"] = val
            os.environ["ANTIGRAVITY_API_KEY"] = val
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "GEMINI_API_KEY", 0, winreg.REG_EXPAND_SZ, val)
                winreg.SetValueEx(key, "ANTIGRAVITY_API_KEY", 0, winreg.REG_EXPAND_SZ, val)
                winreg.CloseKey(key)
            except Exception:
                pass
            messagebox.showinfo("Saved", "Google AI Studio API Key saved permanently!")
            win.destroy()

        tk.Button(
            win,
            text="Save Key Permanently",
            font=("Segoe UI", 9, "bold"),
            fg="#FFFFFF",
            bg=t["esri_blue"],
            activebackground=t["esri_blue_hover"],
            relief=tk.FLAT,
            padx=14,
            pady=8,
            command=save,
        ).pack(pady=16)

    def _clear_chat(self):
        self.agent.conversation_history.clear()
        for child in self.feed_frame.winfo_children():
            child.destroy()
        self._add_ai_bubble("🧹 Conversation cleared. Ready for your next spatial instruction!")

    def _on_enter_pressed(self, event):
        if event.state & 0x0001:  # Shift held
            return None
        self._on_send()
        return "break"

    def _on_stop(self):
        self.stop_requested = True
        self.status_dot.config(text="● Aborting...", fg=self.t["text_muted"])

    def _add_user_bubble(self, text: str):
        t = self.t
        row = tk.Frame(self.feed_frame, bg=t["bg_main"], pady=6)
        row.pack(fill=tk.X, padx=8)

        container = tk.Frame(row, bg=t["bg_main"])
        container.pack(side=tk.RIGHT, fill=tk.X)

        tk.Label(
            container,
            text="🧑 You",
            font=("Segoe UI", 8, "bold"),
            fg=t["esri_blue"],
            bg=t["bg_main"],
        ).pack(anchor="e", padx=4, pady=(0, 2))

        bubble = tk.Label(
            container,
            text=text,
            font=("Segoe UI", 9),
            fg=t["text_main"],
            bg=t["user_bubble"],
            wraplength=520,
            justify=tk.LEFT,
            padx=14,
            pady=10,
            relief=tk.SOLID,
            borderwidth=1,
            highlightbackground=t["user_border"],
        )
        bubble.pack(anchor="e")
        self._scroll_bottom()

    def _add_ai_bubble(self, initial_text: str = ""):
        t = self.t
        row = tk.Frame(self.feed_frame, bg=t["bg_main"], pady=6)
        row.pack(fill=tk.X, padx=8)

        container = tk.Frame(row, bg=t["bg_main"])
        container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            container,
            text=f"✨ Antigravity Copilot ({self.selected_model.get()})",
            font=("Segoe UI", 8, "bold"),
            fg=t["esri_cyan"],
            bg=t["bg_main"],
        ).pack(anchor="w", padx=4, pady=(0, 2))

        bubble = tk.Label(
            container,
            text=initial_text,
            font=("Segoe UI", 9),
            fg=t["text_main"],
            bg=t["ai_bubble"],
            wraplength=560,
            justify=tk.LEFT,
            padx=14,
            pady=10,
            relief=tk.SOLID,
            borderwidth=1,
            highlightbackground=t["ai_border"],
        )
        bubble.pack(anchor="w")

        btn_holder = tk.Frame(container, bg=t["bg_main"])
        btn_holder.pack(anchor="w", pady=(4, 0))

        self._scroll_bottom()
        return bubble, btn_holder

    def _scroll_bottom(self):
        self.root.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def _on_send(self):
        prompt = self.input_text.get("1.0", tk.END).strip()
        if not prompt or self.is_processing:
            return

        self.input_text.delete("1.0", tk.END)
        self._add_user_bubble(prompt)

        self.is_processing = True
        self.stop_requested = False
        self.send_btn.config(state=tk.DISABLED, text="Thinking...")
        self.stop_btn.config(state=tk.NORMAL)
        self.status_dot.config(text="● Streaming...", fg=self.t["esri_blue"])

        bubble, btn_holder = self._add_ai_bubble("⏳ Processing spatial request...")

        threading.Thread(
            target=self._run_async_agent,
            args=(prompt, bubble, btn_holder),
            daemon=True,
        ).start()

    def _run_async_agent(self, prompt: str, bubble: tk.Label, btn_holder: tk.Frame):
        streamed_tokens = []

        def on_token(token: str):
            if self.stop_requested:
                return
            streamed_tokens.append(token)
            full_so_far = "".join(streamed_tokens)
            self.root.after(0, lambda t=full_so_far: bubble.config(text=t))
            self.root.after(0, self._scroll_bottom)

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            final_text = loop.run_until_complete(
                self.agent.execute_prompt(
                    prompt,
                    token_callback=on_token,
                    model=self.selected_model.get(),
                    workspace=self.active_gdb,
                )
            )
            loop.close()

            self.root.after(0, lambda: self._finalize_ai_turn(bubble, btn_holder, final_text))
        except Exception as err:
            err_msg = f"Execution Error: {str(err)}"
            self.root.after(0, lambda: self._finalize_ai_turn(bubble, btn_holder, err_msg))

    def _finalize_ai_turn(self, bubble: tk.Label, btn_holder: tk.Frame, final_text: str):
        bubble.config(text=final_text)
        self.is_processing = False
        self.send_btn.config(state=tk.NORMAL, text="Send  ➔")
        self.stop_btn.config(state=tk.DISABLED)
        self.status_dot.config(text=f"● Ready ({self.selected_model.get()})", fg=self.t["esri_green"])
        self._refresh_arcgis_context()

        if "```python" in final_text or "```py" in final_text or "arcpy." in final_text:
            self._render_code_actions(btn_holder, final_text)

        self._scroll_bottom()

    def _render_code_actions(self, holder: tk.Frame, text: str):
        t = self.t
        code = text
        if "```python" in text:
            code = text.split("```python")[1].split("```")[0].strip()
        elif "```py" in text:
            code = text.split("```py")[1].split("```")[0].strip()
        elif "```" in text:
            code = text.split("```")[1].split("```")[0].strip()

        def copy_code():
            self.root.clipboard_clear()
            self.root.clipboard_append(code)
            messagebox.showinfo("Copied", "Python code copied to clipboard!")

        def run_arcpy():
            res = execute_arcpy_code_snippet(code)
            if res.get("status") == "Success":
                out = res.get("stdout") or "ArcPy snippet executed successfully."
                messagebox.showinfo("ArcPy Result", f"✅ {out}")
            else:
                err = res.get("error") or "Unknown execution error."
                messagebox.showerror("ArcPy Error", f"❌ {err}")
            self._refresh_arcgis_context()

        tk.Button(
            holder,
            text="📋 Copy Code",
            font=("Segoe UI", 8),
            fg=t["text_main"],
            bg=t["bg_panel"],
            activebackground=t["border"],
            relief=tk.SOLID,
            borderwidth=1,
            padx=8,
            pady=4,
            command=copy_code,
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            holder,
            text="▶ Run in ArcPy",
            font=("Segoe UI", 8, "bold"),
            fg="#FFFFFF",
            bg=t["esri_green"],
            activebackground=t["esri_cyan"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            command=run_arcpy,
        ).pack(side=tk.LEFT)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AntigravityGIS AI Copilot")
    parser.add_argument("--prompt", type=str, default=None, help="Initial prompt to run")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", help="AI Model Engine")
    parser.add_argument("--theme", type=str, default="light", help="UI Theme (light/dark)")
    parser.add_argument("--workspace", type=str, default=None, help="Target geodatabase workspace")
    parser.add_argument("--key", type=str, default=None, help="API Key")
    args, _ = parser.parse_known_args()

    if args.key:
        os.environ["GEMINI_API_KEY"] = args.key
        os.environ["ANTIGRAVITY_API_KEY"] = args.key

    root = tk.Tk()
    app = AntigravityArcGISProChatApp(
        root,
        initial_prompt=args.prompt,
        model=args.model,
        theme=args.theme,
        workspace=args.workspace,
    )
    root.mainloop()


if __name__ == "__main__":
    main()
