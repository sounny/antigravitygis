# -*- coding: utf-8 -*-
"""
chat_gui.py - AntigravityGIS Modern AI Copilot Chat Dialog for ArcGIS Pro

A floating, conversational AI Assistant interface designed for seamless GIS workflows.
Runs directly with ArcPy and Google Antigravity SDK with real-time streaming,
quick action chips, and direct map canvas integration.
"""

import asyncio
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

# Ensure parent and current directories are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
for d in [current_dir, parent_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from agent_core import GISAntigravityAgent, __version__

# Premium Dark Titanium Color Palette
BG_DARK = "#0F172A"       # Deep slate navy
BG_PANEL = "#1E293B"      # Dark slate panel
BG_INPUT = "#090D16"      # Deep dark input field
BORDER_COLOR = "#334155"  # Subtle slate border
TEXT_MAIN = "#F8FAFC"     # Crisp white
TEXT_MUTED = "#94A3B8"    # Soft slate gray
ACCENT_BLUE = "#38BDF8"   # Electric sky blue
ACCENT_CYAN = "#06B6D4"   # Vibrant cyan
ACCENT_GREEN = "#10B981"  # Emerald success
USER_BUBBLE = "#0369A1"   # Deep ocean blue
AI_BUBBLE = "#1E293B"     # Elevated dark slate
CHIP_BG = "#1E293B"       # Action chips background
CHIP_HOVER = "#334155"


class AntigravityChatApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"Antigravity AI Copilot (v{__version__}) — ArcGIS Pro")
        self.root.geometry("640x780")
        self.root.minsize(480, 600)
        self.root.configure(bg=BG_DARK)

        # Try setting window icon if available
        try:
            self.root.attributes("-topmost", False)
        except Exception:
            pass

        self.agent = GISAntigravityAgent()
        self.is_processing = False

        self._build_ui()
        self._detect_arcgis_context()

    def _build_ui(self):
        # 1. Header Bar
        header_frame = tk.Frame(self.root, bg=BG_PANEL, height=64, padx=16, pady=12)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        title_label = tk.Label(
            header_frame,
            text="✨ Antigravity AI Copilot",
            font=("Segoe UI", 13, "bold"),
            fg=TEXT_MAIN,
            bg=BG_PANEL,
        )
        title_label.pack(side=tk.LEFT)

        subtitle_label = tk.Label(
            header_frame,
            text=f"v{__version__} by Sounny",
            font=("Segoe UI", 9),
            fg=ACCENT_BLUE,
            bg=BG_PANEL,
        )
        subtitle_label.pack(side=tk.LEFT, padx=(8, 0))

        # Status badge on right
        self.status_badge = tk.Label(
            header_frame,
            text="● Connected",
            font=("Segoe UI", 9, "bold"),
            fg=ACCENT_GREEN,
            bg=BG_PANEL,
        )
        self.status_badge.pack(side=tk.RIGHT)

        # 2. Context Info Bar (Active GDB / Map)
        self.context_bar = tk.Frame(self.root, bg=BG_DARK, padx=16, pady=6)
        self.context_bar.pack(fill=tk.X)

        self.context_label = tk.Label(
            self.context_bar,
            text="📍 Detecting active ArcGIS Pro workspace...",
            font=("Segoe UI", 8),
            fg=TEXT_MUTED,
            bg=BG_DARK,
            anchor="w",
        )
        self.context_label.pack(fill=tk.X)

        # 3. Chat History Display Area
        chat_container = tk.Frame(self.root, bg=BG_DARK, padx=16, pady=4)
        chat_container.pack(fill=tk.BOTH, expand=True)

        self.chat_canvas = tk.Canvas(chat_container, bg=BG_DARK, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(chat_container, orient=tk.VERTICAL, command=self.chat_canvas.yview)
        self.scrollable_frame = tk.Frame(self.chat_canvas, bg=BG_DARK)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all")),
        )

        self.canvas_window = self.chat_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.chat_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.chat_canvas.bind("<Configure>", self._on_canvas_resize)
        self.chat_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Welcome message bubble
        self._add_message(
            "assistant",
            "👋 Welcome to **AntigravityGIS**! I'm your ArcGIS Pro AI Copilot.\n\n"
            "I can interact directly with your map view and project geodatabase. "
            "Ask me to map cities, inspect layers, calculate geometries, or run spatial analysis.",
        )

        # 4. Quick Action Chips Bar
        chips_frame = tk.Frame(self.root, bg=BG_DARK, padx=16, pady=6)
        chips_frame.pack(fill=tk.X)

        chips = [
            ("📍 Add Point (Austin, TX)", "Make a point for Austin Texas and add it to my active map"),
            ("🔍 Inspect Workspace", "Inspect all feature classes and datasets in my project workspace"),
            ("🗺️ Summarize Map", "Describe the layers and spatial reference of the current active map view"),
            ("⚡ Key Setup", "Configure my Google AI Studio API key"),
        ]

        for label, prompt_text in chips:
            btn = tk.Button(
                chips_frame,
                text=label,
                font=("Segoe UI", 8),
                fg=TEXT_MAIN,
                bg=CHIP_BG,
                activebackground=CHIP_HOVER,
                activeforeground=TEXT_MAIN,
                relief=tk.FLAT,
                padx=8,
                pady=4,
                cursor="hand2",
                command=lambda p=prompt_text: self._send_quick_prompt(p),
            )
            btn.pack(side=tk.LEFT, padx=(0, 6))

        # 5. Input Area
        input_container = tk.Frame(self.root, bg=BG_PANEL, padx=14, pady=12)
        input_container.pack(fill=tk.X, side=tk.BOTTOM)

        # Multi-line Prompt Text Box
        self.prompt_text = tk.Text(
            input_container,
            height=3,
            bg=BG_INPUT,
            fg=TEXT_MAIN,
            insertbackground=ACCENT_BLUE,
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            padx=10,
            pady=8,
            wrap=tk.WORD,
        )
        self.prompt_text.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 10))
        self.prompt_text.bind("<Return>", self._on_enter_pressed)
        self.prompt_text.bind("<Shift-Return>", lambda e: None)  # Allows multiline with Shift+Enter

        # Send Button
        self.send_btn = tk.Button(
            input_container,
            text="Send  ➔",
            font=("Segoe UI", 10, "bold"),
            fg="#FFFFFF",
            bg=ACCENT_BLUE,
            activebackground=ACCENT_CYAN,
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=16,
            pady=12,
            cursor="hand2",
            command=self._on_send_clicked,
        )
        self.send_btn.pack(side=tk.RIGHT)

    def _on_canvas_resize(self, event):
        self.chat_canvas.itemconfig(self.canvas_window, width=event.width)

    def _detect_arcgis_context(self):
        """Attempts to detect active ArcGIS Pro project and geodatabase silently."""
        try:
            import arcpy
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            gdb = aprx.defaultGeodatabase or arcpy.env.workspace or "Default GDB"
            map_name = aprx.activeMap.name if aprx.activeMap else "No Active Map"
            self.context_label.config(
                text=f"📂 Project GDB: {os.path.basename(gdb)} | 🗺️ Map: {map_name}"
            )
        except Exception:
            self.context_label.config(text="📂 Standalone ArcGIS Python Mode")

    def _on_enter_pressed(self, event):
        # If Shift is held, let default newline happen
        if event.state & 0x0001:
            return None
        self._on_send_clicked()
        return "break"

    def _send_quick_prompt(self, prompt_text: str):
        if self.is_processing:
            return
        if prompt_text == "Configure my Google AI Studio API key":
            self._open_key_dialog()
            return
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert("1.0", prompt_text)
        self._on_send_clicked()

    def _open_key_dialog(self):
        """Opens a quick popup to enter and save the Google AI Studio API key."""
        win = tk.Toplevel(self.root)
        win.title("Set Google AI Studio API Key")
        win.geometry("480x240")
        win.configure(bg=BG_PANEL)
        win.resizable(False, False)

        tk.Label(
            win,
            text="🔑 Google AI Studio API Key",
            font=("Segoe UI", 11, "bold"),
            fg=TEXT_MAIN,
            bg=BG_PANEL,
        ).pack(anchor="w", padx=20, pady=(16, 4))

        tk.Label(
            win,
            text="Get your free high-speed key at https://aistudio.google.com/apikey",
            font=("Segoe UI", 8),
            fg=ACCENT_BLUE,
            bg=BG_PANEL,
        ).pack(anchor="w", padx=20, pady=(0, 12))

        entry = tk.Entry(win, font=("Segoe UI", 10), bg=BG_INPUT, fg=TEXT_MAIN, show="*")
        entry.pack(fill=tk.X, padx=20, pady=4)
        if os.environ.get("GEMINI_API_KEY"):
            entry.insert(0, os.environ["GEMINI_API_KEY"])

        def save_key():
            val = entry.get().strip()
            if not val:
                messagebox.showerror("Error", "Please enter a valid API key.")
                return
            os.environ["GEMINI_API_KEY"] = val
            os.environ["ANTIGRAVITY_API_KEY"] = val
            # Save to user environment permanently
            import subprocess
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
            padx=12,
            pady=6,
            command=save_key,
        ).pack(pady=16)

    def _add_message(self, sender: str, text: str):
        """Adds a formatted speech bubble to the chat feed."""
        bubble_frame = tk.Frame(self.scrollable_frame, bg=BG_DARK, pady=6)
        bubble_frame.pack(fill=tk.X, padx=8)

        is_user = sender == "user"
        bg_color = USER_BUBBLE if is_user else AI_BUBBLE
        fg_color = TEXT_MAIN
        align = tk.RIGHT if is_user else tk.LEFT
        prefix = "🧑 You" if is_user else "✨ Antigravity Copilot"

        # Container for bubble
        container = tk.Frame(bubble_frame, bg=BG_DARK)
        container.pack(side=align, fill=tk.X, expand=False)

        header_lbl = tk.Label(
            container,
            text=prefix,
            font=("Segoe UI", 8, "bold"),
            fg=ACCENT_BLUE if not is_user else TEXT_MUTED,
            bg=BG_DARK,
        )
        header_lbl.pack(anchor="e" if is_user else "w", padx=4, pady=(0, 2))

        bubble = tk.Label(
            container,
            text=text,
            font=("Segoe UI", 9),
            fg=fg_color,
            bg=bg_color,
            wraplength=480,
            justify=tk.LEFT,
            padx=12,
            pady=8,
            relief=tk.FLAT,
        )
        bubble.pack(anchor="e" if is_user else "w")

        # Scroll to bottom
        self.root.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)
        return bubble

    def _on_send_clicked(self):
        prompt = self.prompt_text.get("1.0", tk.END).strip()
        if not prompt or self.is_processing:
            return

        self.prompt_text.delete("1.0", tk.END)
        self._add_message("user", prompt)

        # Set processing state
        self.is_processing = True
        self.send_btn.config(state=tk.DISABLED, text="Thinking...")
        self.status_badge.config(text="● Processing...", fg=ACCENT_BLUE)

        ai_bubble = self._add_message("assistant", "⏳ Analyzing spatial request...")

        # Run async agent in background thread
        threading.Thread(
            target=self._run_agent_async, args=(prompt, ai_bubble), daemon=True
        ).start()

    def _run_agent_async(self, prompt: str, ai_bubble: tk.Label):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(self.agent.execute_prompt(prompt))
            loop.close()

            # Schedule UI update on main thread
            self.root.after(0, lambda: self._update_ai_response(ai_bubble, response))
        except Exception as err:
            err_msg = f"Execution error: {str(err)}"
            self.root.after(0, lambda: self._update_ai_response(ai_bubble, err_msg))

    def _update_ai_response(self, ai_bubble: tk.Label, response_text: str):
        ai_bubble.config(text=response_text)
        self.is_processing = False
        self.send_btn.config(state=tk.NORMAL, text="Send  ➔")
        self.status_badge.config(text="● Ready", fg=ACCENT_GREEN)
        self._detect_arcgis_context()
        self.root.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)


def main():
    root = tk.Tk()
    app = AntigravityChatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
