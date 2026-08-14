# -*- coding: utf-8 -*-
"""
chat_gui.py - Next-Gen Antigravity AI Copilot Interactive Chat Dialog for ArcGIS Pro

A desktop AI Copilot featuring:
- Multi-turn conversation memory
- Token-by-token streaming animation
- Code blocks with 1-click 'Copy' and '▶ Run in ArcPy' execution
- Dynamic Model Selector (Gemini 2.5 Flash, Gemini 2.5 Pro)
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

# Dark Titanium Glassmorphic Palette
BG_DARK = "#090D16"        # Deep void slate
BG_SIDEBAR = "#0F172A"     # Sleek slate sidebar
BG_PANEL = "#1E293B"       # Elevated container slate
BG_INPUT = "#0B1120"       # Deep input well
BG_CODE = "#030712"        # Monospace code background
BORDER_COLOR = "#334155"   # Slate border
TEXT_MAIN = "#F8FAFC"      # Crisp bright white
TEXT_MUTED = "#94A3B8"     # Soft slate gray
ACCENT_BLUE = "#38BDF8"    # Electric sky blue
ACCENT_CYAN = "#06B6D4"    # Vibrant cyan
ACCENT_GREEN = "#10B981"   # Emerald success
ACCENT_PURPLE = "#818CF8"  # Soft indigo
USER_BUBBLE = "#0369A1"    # Deep ocean blue
AI_BUBBLE = "#1E293B"      # Deep slate panel


class AntigravityModernChatApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"Antigravity AI Copilot (v{__version__}) — ArcGIS Pro")
        self.root.geometry("980x760")
        self.root.minsize(720, 560)
        self.root.configure(bg=BG_DARK)

        self.selected_model = tk.StringVar(value="gemini-2.5-flash")
        self.agent = GISAntigravityAgent(model=self.selected_model.get())
        self.is_processing = False
        self.stop_requested = False
        self.active_gdb = ""
        self.active_map_name = ""

        self._build_ui()
        self._refresh_arcgis_context()

    def _build_ui(self):
        # Master Horizontal Split: Sidebar (Left) + Chat View (Right)
        self.main_container = tk.Frame(self.root, bg=BG_DARK)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # ----------------------------------------------------
        # 1. LEFT SIDEBAR
        # ----------------------------------------------------
        sidebar = tk.Frame(self.main_container, bg=BG_SIDEBAR, width=280, padx=14, pady=14)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        # App Brand Title
        brand_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
        brand_frame.pack(fill=tk.X, pady=(0, 14))

        tk.Label(
            brand_frame,
            text="✨ AntigravityGIS",
            font=("Segoe UI", 13, "bold"),
            fg=TEXT_MAIN,
            bg=BG_SIDEBAR,
        ).pack(anchor="w")

        tk.Label(
            brand_frame,
            text=f"AI Spatial Copilot v{__version__}",
            font=("Segoe UI", 8),
            fg=ACCENT_BLUE,
            bg=BG_SIDEBAR,
        ).pack(anchor="w")

        # Model Selector Dropdown
        tk.Label(
            sidebar,
            text="MODEL ENGINE",
            font=("Segoe UI", 7, "bold"),
            fg=TEXT_MUTED,
            bg=BG_SIDEBAR,
        ).pack(anchor="w", pady=(8, 4))

        models = [
            ("⚡ Gemini 2.5 Flash (Fast)", "gemini-2.5-flash"),
            ("🧠 Gemini 2.5 Pro (Reasoning)", "gemini-2.5-pro"),
            ("🚀 Gemini 2.0 Flash", "gemini-2.0-flash"),
        ]

        self.model_combo = ttk.Combobox(
            sidebar,
            values=[m[0] for m in models],
            state="readonly",
            font=("Segoe UI", 9),
        )
        self.model_combo.current(0)
        self.model_combo.pack(fill=tk.X, pady=(0, 12))
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_changed)

        # Active Context Panel
        tk.Label(
            sidebar,
            text="PROJECT CONTEXT",
            font=("Segoe UI", 7, "bold"),
            fg=TEXT_MUTED,
            bg=BG_SIDEBAR,
        ).pack(anchor="w", pady=(8, 4))

        self.context_card = tk.Frame(sidebar, bg=BG_PANEL, padx=10, pady=10)
        self.context_card.pack(fill=tk.X, pady=(0, 14))

        self.lbl_gdb = tk.Label(
            self.context_card,
            text="📂 GDB: Detecting...",
            font=("Segoe UI", 8),
            fg=TEXT_MAIN,
            bg=BG_PANEL,
            anchor="w",
            wraplength=230,
            justify=tk.LEFT,
        )
        self.lbl_gdb.pack(fill=tk.X)

        self.lbl_map = tk.Label(
            self.context_card,
            text="🗺️ Map: Detecting...",
            font=("Segoe UI", 8),
            fg=ACCENT_CYAN,
            bg=BG_PANEL,
            anchor="w",
        )
        self.lbl_map.pack(fill=tk.X, pady=(4, 0))

        # Quick Actions Header
        tk.Label(
            sidebar,
            text="QUICK SPATIAL ACTIONS",
            font=("Segoe UI", 7, "bold"),
            fg=TEXT_MUTED,
            bg=BG_SIDEBAR,
        ).pack(anchor="w", pady=(8, 4))

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
                sidebar,
                text=label,
                font=("Segoe UI", 8),
                fg=TEXT_MAIN,
                bg=BG_PANEL,
                activebackground=BORDER_COLOR,
                activeforeground=TEXT_MAIN,
                relief=tk.FLAT,
                anchor="w",
                padx=8,
                pady=6,
                cursor="hand2",
                command=lambda c=cmd: self._handle_sidebar_action(c),
            )
            btn.pack(fill=tk.X, pady=2)

        # ----------------------------------------------------
        # 2. RIGHT CHAT AREA
        # ----------------------------------------------------
        chat_area = tk.Frame(self.main_container, bg=BG_DARK)
        chat_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Header Bar
        top_header = tk.Frame(chat_area, bg=BG_PANEL, height=50, padx=16, pady=10)
        top_header.pack(fill=tk.X, side=tk.TOP)

        self.status_title = tk.Label(
            top_header,
            text="ArcGIS Pro AI Copilot",
            font=("Segoe UI", 11, "bold"),
            fg=TEXT_MAIN,
            bg=BG_PANEL,
        )
        self.status_title.pack(side=tk.LEFT)

        self.status_dot = tk.Label(
            top_header,
            text="● Ready (Gemini 2.5 Flash)",
            font=("Segoe UI", 9, "bold"),
            fg=ACCENT_GREEN,
            bg=BG_PANEL,
        )
        self.status_dot.pack(side=tk.RIGHT)

        # Chat Stream Area (Scrollable Canvas)
        chat_container = tk.Frame(chat_area, bg=BG_DARK, padx=16, pady=8)
        chat_container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(chat_container, bg=BG_DARK, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(chat_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.feed_frame = tk.Frame(self.canvas, bg=BG_DARK)

        self.feed_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.feed_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Welcome message
        self._add_ai_bubble(
            "👋 Welcome to **AntigravityGIS AI Copilot**!\n\n"
            "I have direct access to your active **ArcGIS Pro** map canvas, project geodatabase, and ArcPy tools.\n\n"
            "• Ask me to pin coordinates or cities (`make a point for Austin Texas`)\n"
            "• Ask me to run spatial analysis (`buffer Point_Austin by 10 km`)\n"
            "• Ask me to inspect your geodatabase schema and count records\n"
            "• All conversations and actions are automatically logged to your project geodatabase!"
        )

        # ----------------------------------------------------
        # 3. BOTTOM INPUT PANEL
        # ----------------------------------------------------
        input_panel = tk.Frame(chat_area, bg=BG_PANEL, padx=16, pady=12)
        input_panel.pack(fill=tk.X, side=tk.BOTTOM)

        # Expanding Multi-line Text Box
        self.input_text = tk.Text(
            input_panel,
            height=3,
            bg=BG_INPUT,
            fg=TEXT_MAIN,
            insertbackground=ACCENT_BLUE,
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            padx=12,
            pady=10,
            wrap=tk.WORD,
        )
        self.input_text.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 10))
        self.input_text.bind("<Return>", self._on_enter_pressed)

        # Action Buttons Container
        btn_box = tk.Frame(input_panel, bg=BG_PANEL)
        btn_box.pack(side=tk.RIGHT)

        self.send_btn = tk.Button(
            btn_box,
            text="Send  ➔",
            font=("Segoe UI", 10, "bold"),
            fg="#FFFFFF",
            bg=ACCENT_BLUE,
            activebackground=ACCENT_CYAN,
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
            fg=TEXT_MUTED,
            bg=BG_DARK,
            activebackground=BORDER_COLOR,
            relief=tk.FLAT,
            state=tk.DISABLED,
            command=self._on_stop,
        )
        self.stop_btn.pack(fill=tk.X)

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
        self.status_dot.config(text=f"● Ready ({model_id})", fg=ACCENT_GREEN)

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
        # Look for Antigravity_Chat_History.md in project or default locations
        candidate_paths = [
            os.path.join(os.path.dirname(self.active_gdb), "Antigravity_Chat_History.md") if self.active_gdb else None,
            os.path.expanduser(r"~\Documents\ArcGIS\Projects\AntigravityGIS\Antigravity_Chat_History.md"),
            os.path.join(os.getcwd(), "Antigravity_Chat_History.md"),
        ]
        found = False
        for p in candidate_paths:
            if p and os.path.exists(p):
                os.system(f'start "" "{p}"')
                found = True
                break
        if not found:
            messagebox.showinfo("History Log", "Chat history will be created upon your first prompt execution.")

    def _open_key_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("Configure Google AI Studio Key")
        win.geometry("480x240")
        win.configure(bg=BG_SIDEBAR)
        win.resizable(False, False)

        tk.Label(
            win,
            text="🔑 Google AI Studio API Key",
            font=("Segoe UI", 11, "bold"),
            fg=TEXT_MAIN,
            bg=BG_SIDEBAR,
        ).pack(anchor="w", padx=20, pady=(16, 4))

        tk.Label(
            win,
            text="Get your free high-speed key at https://aistudio.google.com/apikey",
            font=("Segoe UI", 8),
            fg=ACCENT_BLUE,
            bg=BG_SIDEBAR,
        ).pack(anchor="w", padx=20, pady=(0, 12))

        entry = tk.Entry(win, font=("Segoe UI", 10), bg=BG_INPUT, fg=TEXT_MAIN, show="*")
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
            cmd = f"[System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', '{val}', 'User'); [System.Environment]::SetEnvironmentVariable('ANTIGRAVITY_API_KEY', '{val}', 'User')"
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, creationflags=0x08000000)
            messagebox.showinfo("Saved", "Google AI Studio API Key saved permanently!")
            win.destroy()

        tk.Button(
            win,
            text="Save Key Permanently",
            font=("Segoe UI", 9, "bold"),
            fg="#FFFFFF",
            bg=ACCENT_BLUE,
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
        self.status_dot.config(text="● Aborting...", fg=TEXT_MUTED)

    def _add_user_bubble(self, text: str):
        row = tk.Frame(self.feed_frame, bg=BG_DARK, pady=6)
        row.pack(fill=tk.X, padx=8)

        container = tk.Frame(row, bg=BG_DARK)
        container.pack(side=tk.RIGHT, fill=tk.X)

        tk.Label(
            container,
            text="🧑 You",
            font=("Segoe UI", 8, "bold"),
            fg=ACCENT_BLUE,
            bg=BG_DARK,
        ).pack(anchor="e", padx=4, pady=(0, 2))

        bubble = tk.Label(
            container,
            text=text,
            font=("Segoe UI", 9),
            fg=TEXT_MAIN,
            bg=USER_BUBBLE,
            wraplength=520,
            justify=tk.LEFT,
            padx=14,
            pady=10,
            relief=tk.FLAT,
        )
        bubble.pack(anchor="e")
        self._scroll_bottom()

    def _add_ai_bubble(self, initial_text: str = ""):
        row = tk.Frame(self.feed_frame, bg=BG_DARK, pady=6)
        row.pack(fill=tk.X, padx=8)

        container = tk.Frame(row, bg=BG_DARK)
        container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            container,
            text=f"✨ Antigravity Copilot ({self.selected_model.get()})",
            font=("Segoe UI", 8, "bold"),
            fg=ACCENT_CYAN,
            bg=BG_DARK,
        ).pack(anchor="w", padx=4, pady=(0, 2))

        bubble = tk.Label(
            container,
            text=initial_text,
            font=("Segoe UI", 9),
            fg=TEXT_MAIN,
            bg=AI_BUBBLE,
            wraplength=560,
            justify=tk.LEFT,
            padx=14,
            pady=10,
            relief=tk.FLAT,
        )
        bubble.pack(anchor="w")

        # Container for code execution buttons if code is detected
        btn_holder = tk.Frame(container, bg=BG_DARK)
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
        self.status_dot.config(text="● Streaming...", fg=ACCENT_BLUE)

        bubble, btn_holder = self._add_ai_bubble("⏳ Processing spatial request...")

        # Background thread execution with token streaming callback
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
        self.status_dot.config(text=f"● Ready ({self.selected_model.get()})", fg=ACCENT_GREEN)
        self._refresh_arcgis_context()

        # Check if Python / ArcPy code block exists in response
        if "```python" in final_text or "```py" in final_text or "arcpy." in final_text:
            self._render_code_actions(btn_holder, final_text)

        self._scroll_bottom()

    def _render_code_actions(self, holder: tk.Frame, text: str):
        # Extract code inside backticks if present
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
            fg=TEXT_MAIN,
            bg=BG_PANEL,
            activebackground=BORDER_COLOR,
            relief=tk.FLAT,
            padx=8,
            pady=4,
            command=copy_code,
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            holder,
            text="▶ Run in ArcPy",
            font=("Segoe UI", 8, "bold"),
            fg="#FFFFFF",
            bg=ACCENT_GREEN,
            activebackground=ACCENT_CYAN,
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            command=run_arcpy,
        ).pack(side=tk.LEFT)


def main():
    root = tk.Tk()
    app = AntigravityModernChatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
