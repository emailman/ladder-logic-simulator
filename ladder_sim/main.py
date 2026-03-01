import sys
import tkinter as tk
from tkinter import ttk

from loader import load
from engine import PLCEngine
from renderer import LadderRenderer

SCAN_MS = 100  # scan cycle in milliseconds


class LadderApp(tk.Tk):
    def __init__(self, json_path: str):
        super().__init__()
        program = load(json_path)
        self.title(f"Ladder Logic Simulator - {program['title']}")
        self.resizable(True, True)

        self.engine = PLCEngine(program)

        # ── Toolbar ────────────────────────────────────────────────────
        toolbar = tk.Frame(self, bd=1, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        tk.Button(toolbar, text="Reset", command=self.on_reset).pack(
            side=tk.LEFT, padx=4, pady=2)

        # ── Scrollable canvas ──────────────────────────────────────────
        frame = tk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(frame, bg="white", width=960, height=600,
                                scrollregion=(0, 0, 960, 2000))

        v_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL,
                                  command=self.canvas.yview)
        h_scroll = ttk.Scrollbar(frame, orient=tk.HORIZONTAL,
                                  command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scroll.set,
                              xscrollcommand=h_scroll.set)

        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ── Status bar ─────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Click an input contact to toggle it.")
        status_bar = tk.Label(self, textvariable=self.status_var,
                              bd=1, relief=tk.SUNKEN, anchor=tk.W,
                              font=("Helvetica", 9))
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # ── Renderer ───────────────────────────────────────────────────
        self.renderer = LadderRenderer(self.canvas, self.engine)

        self._held_momentary: str | None = None  # bit currently held by mouse

        # ── Mouse bindings ─────────────────────────────────────────────
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)   # Windows/macOS
        self.canvas.bind("<Button-4>", self._on_mousewheel)     # Linux scroll up
        self.canvas.bind("<Button-5>", self._on_mousewheel)     # Linux scroll down

        # ── Start scan loop ────────────────────────────────────────────
        self.after(SCAN_MS, self.scan_loop)

    def scan_loop(self):
        self.engine.scan()
        self.renderer.draw()
        self._update_scroll_region()
        self.after(SCAN_MS, self.scan_loop)

    def on_click(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        bit = self.renderer.hit_test(int(cx), int(cy))
        if bit:
            meta = self.engine.bit_meta.get(bit, {})
            label = meta.get("label", bit)
            if meta.get("momentary"):
                self._held_momentary = bit
                self.engine.set_input(bit, True)
                self.status_var.set(f"Holding {bit} ({label}) - ON while pressed")
            else:
                self.engine.toggle_input(bit)
                state = "ON" if self.engine.bits.get(bit, False) else "OFF"
                self.status_var.set(f"Toggled {bit} ({label}) -> {state}")
        else:
            self.status_var.set("Click an input contact to toggle it.")

    def on_release(self, event):
        if self._held_momentary:
            bit = self._held_momentary
            self._held_momentary = None
            self.engine.set_input(bit, False)
            meta = self.engine.bit_meta.get(bit, {})
            label = meta.get("label", bit)
            self.status_var.set(f"Released {bit} ({label}) -> OFF")

    def on_reset(self):
        self.engine.reset_timers_and_counters()
        self.status_var.set("Timers and counter reset.")

    def _update_scroll_region(self):
        self.canvas.configure(scrollregion=self.canvas.bbox("all") or (0, 0, 960, 600))

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(-1 * (event.delta // 120), "units")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "example.json"
    LadderApp(path).mainloop()
