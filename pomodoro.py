"""
Pomodoro Timer — Desktop番茄钟
A clean, minimal Pomodoro timer built with Python tkinter.
"""

import tkinter as tk
from tkinter import ttk
import math
import time
import winsound
from datetime import timedelta

# ── Constants ──────────────────────────────────────────────────────────
WORK_MIN = 25
SHORT_BREAK_MIN = 5
LONG_BREAK_MIN = 15
LONG_BREAK_INTERVAL = 4  # long break every N sessions

COLORS = {
    "bg": "#1E1E2E",
    "fg": "#CDD6F4",
    "accent": "#F38BA8",       # work — soft red / tomato
    "break": "#A6E3A1",        # break — green
    "long_break": "#89B4FA",   # long break — blue
    "button_bg": "#313244",
    "button_hover": "#45475A",
    "progress_bg": "#313244",
    "text_dim": "#6C7086",
    "text_highlight": "#F5C2E7",
}

FONT_DIGITAL = "Segoe UI", 60, "bold"
FONT_LABEL = "Segoe UI", 14
FONT_SMALL = "Segoe UI", 11
FONT_BUTTON = "Segoe UI", 12, "bold"


class CircularTimer(tk.Canvas):
    """Canvas widget that draws a circular countdown."""

    def __init__(self, parent, size=280, **kw):
        super().__init__(parent, width=size, height=size,
                         bg=COLORS["bg"], highlightthickness=0, **kw)
        self.size = size
        self.center = size // 2
        self.radius = size // 2 - 30
        self.line_width = 10
        self.progress = 1.0  # 1.0 = full, 0.0 = empty
        self.color = COLORS["accent"]
        self._arc_id = None
        self._draw_static()
        self._draw_arc()

    def _draw_static(self):
        """Draw the static background track."""
        self.create_oval(
            self.center - self.radius, self.center - self.radius,
            self.center + self.radius, self.center + self.radius,
            outline=COLORS["progress_bg"], width=self.line_width,
        )

    def _draw_arc(self):
        """Draw the progress arc."""
        if self._arc_id:
            self.delete(self._arc_id)
        start_angle = 90  # 12 o'clock
        extent = 360 * self.progress
        self._arc_id = self.create_arc(
            self.center - self.radius, self.center - self.radius,
            self.center + self.radius, self.center + self.radius,
            start=start_angle, extent=-extent,
            outline=self.color, width=self.line_width,
            style="arc",
        )

    def set_progress(self, value: float):
        """Set progress 0.0–1.0."""
        self.progress = max(0.0, min(1.0, value))
        self._draw_arc()

    def set_color(self, color: str):
        self.color = color
        self._draw_arc()


class PomodoroApp:
    """Main Pomodoro timer application."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Pomodoro Timer")
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(False, False)

        # Centre window
        win_w, win_h = 420, 540
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - win_w) // 2
        y = (sh - win_h) // 2
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        # ── State ──────────────────────────────────────────────────────
        self.state = "idle"        # idle | work | short_break | long_break
        self.remaining = 0         # seconds remaining
        self.total = 0             # total seconds for current phase
        self.session_count = 0     # completed work sessions
        self.running = False
        self.timer_id = None

        # ── UI ─────────────────────────────────────────────────────────
        self._build_ui()

        # ── Keyboard shortcuts ─────────────────────────────────────────
        self.root.bind("<space>", lambda e: self.toggle())
        self.root.bind("<Escape>", lambda e: self.reset())
        self.root.bind("<r>", lambda e: self.reset())

        # ── Show idle ──────────────────────────────────────────────────
        self._update_display()

    # ── UI Build ───────────────────────────────────────────────────────

    def _build_ui(self):
        main = tk.Frame(self.root, bg=COLORS["bg"])
        main.pack(expand=True, fill="both", padx=30, pady=(30, 20))

        # Title
        self.title_label = tk.Label(
            main, text="🍅  Pomodoro",
            font=("Segoe UI", 18, "bold"),
            bg=COLORS["bg"], fg=COLORS["fg"],
        )
        self.title_label.pack(pady=(0, 10))

        # Phase label
        self.phase_label = tk.Label(
            main, text="Ready",
            font=FONT_LABEL,
            bg=COLORS["bg"], fg=COLORS["text_dim"],
        )
        self.phase_label.pack(pady=(0, 15))

        # Circular timer
        self.canvas = CircularTimer(main, size=280)
        self.canvas.pack(pady=(0, 5))

        # Time text on canvas
        self.time_text = self.canvas.create_text(
            self.canvas.center, self.canvas.center - 12,
            text="25:00", fill=COLORS["fg"],
            font=FONT_DIGITAL, anchor="center",
        )
        self.status_text = self.canvas.create_text(
            self.canvas.center, self.canvas.center + 35,
            text="", fill=COLORS["text_dim"],
            font=FONT_SMALL, anchor="center",
        )

        # Session counter
        self.session_label = tk.Label(
            main, text="Completed: 0  pomodoro",
            font=FONT_SMALL,
            bg=COLORS["bg"], fg=COLORS["text_dim"],
        )
        self.session_label.pack(pady=(5, 15))

        # ── Buttons ────────────────────────────────────────────────────
        btn_frame = tk.Frame(main, bg=COLORS["bg"])
        btn_frame.pack()

        self.start_btn = self._make_button(
            btn_frame, "▶  Start", 0, 0, self.toggle,
            COLORS["accent"],
        )
        self.reset_btn = self._make_button(
            btn_frame, "⟳  Reset", 0, 1, self.reset,
            COLORS["text_dim"],
        )

        # ── Mode quick-switch ──────────────────────────────────────────
        mode_frame = tk.Frame(main, bg=COLORS["bg"])
        mode_frame.pack(pady=(15, 0))

        self.mode_btns = {}
        for i, (key, label, color) in enumerate([
            ("work", "Work 25m", COLORS["accent"]),
            ("short", "Break 5m", COLORS["break"]),
            ("long", "Long 15m", COLORS["long_break"]),
        ]):
            btn = self._make_button(
                mode_frame, label, 0, i, lambda k=key: self._quick_switch(k),
                color, small=True,
            )
            self.mode_btns[key] = btn

        # ── Key hint ───────────────────────────────────────────────────
        hint = tk.Label(
            main,
            text="Space = Start/Pause   ·   Esc / R = Reset",
            font=("Segoe UI", 9),
            bg=COLORS["bg"], fg=COLORS["text_dim"],
        )
        hint.pack(pady=(12, 0))

    def _make_button(self, parent, text, row, col, cmd, color,
                     small=False):
        """Create a styled Button."""
        padx, pady = (18, 8) if small else (24, 10)
        font = FONT_SMALL if small else FONT_BUTTON
        btn = tk.Button(
            parent, text=text, command=cmd,
            font=font,
            bg=COLORS["button_bg"], fg=color,
            activebackground=COLORS["button_hover"],
            activeforeground=color,
            relief="flat", bd=0,
            padx=padx, pady=pady,
            cursor="hand2",
        )
        btn.grid(row=row, column=col, padx=4)
        return btn

    # ── Core Logic ─────────────────────────────────────────────────────

    def _get_default_seconds(self, state):
        if state == "work":
            return WORK_MIN * 60
        elif state == "short_break":
            return SHORT_BREAK_MIN * 60
        elif state == "long_break":
            return LONG_BREAK_MIN * 60
        return WORK_MIN * 60

    def _get_phase_color(self, state):
        return {
            "work": COLORS["accent"],
            "short_break": COLORS["break"],
            "long_break": COLORS["long_break"],
        }.get(state, COLORS["accent"])

    def _get_phase_label(self, state):
        labels = {
            "idle": "Ready",
            "work": "Focus Time",
            "short_break": "Short Break",
            "long_break": "Long Break",
        }
        return labels.get(state, "")

    def _format_time(self, seconds):
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    def _update_display(self):
        """Refresh time text, canvas progress, labels."""
        self.canvas.itemconfig(self.time_text,
                               text=self._format_time(self.remaining))

        if self.total > 0:
            self.canvas.set_progress(self.remaining / self.total)
        else:
            self.canvas.set_progress(1.0)

        color = self._get_phase_color(self.state)
        self.canvas.set_color(color)
        self.phase_label.config(text=self._get_phase_label(self.state),
                                fg=color)

        self.session_label.config(
            text=f"Completed: {self.session_count}  pomodoro"
            + ("s" if self.session_count != 1 else "")
        )

        # Status icon
        icon = "▶" if self.running else "⏸"
        self.canvas.itemconfig(self.status_text,
                               text=f"{icon}  {self._get_phase_label(self.state)}")

        # Start button text
        if self.state == "idle":
            self.start_btn.config(text="▶  Start")
        elif self.running:
            self.start_btn.config(text="⏸  Pause")
        else:
            self.start_btn.config(text="▶  Resume")

    def _tick(self):
        """Called every second when running."""
        if not self.running:
            return

        self.remaining -= 1
        self._update_display()

        if self.remaining <= 0:
            self._on_finish()
            return

        self.timer_id = self.root.after(1000, self._tick)

    def _on_finish(self):
        """Timer reached zero."""
        self.running = False

        # Beep
        try:
            winsound.Beep(800, 300)
            winsound.Beep(1000, 300)
        except Exception:
            pass

        if self.state == "work":
            self.session_count += 1
            if self.session_count % LONG_BREAK_INTERVAL == 0:
                self._start_phase("long_break")
            else:
                self._start_phase("short_break")
        else:
            self._start_phase("work")

    def _start_phase(self, state):
        """Start a phase (work/break) without auto-countdown."""
        self.state = state
        self.total = self._get_default_seconds(state)
        self.remaining = self.total
        self.running = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self.canvas.set_color(self._get_phase_color(state))
        self._update_display()

    def toggle(self):
        """Start / pause."""
        if self.state == "idle":
            self._start_phase("work")
            self.running = True
            self._tick()
        elif self.running:
            self.running = False
            self._update_display()
        else:
            self.running = True
            self._tick()

    def reset(self):
        """Reset current phase to its full duration."""
        was_running = self.running
        self.running = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

        if self.state == "idle":
            self.total = self._get_default_seconds("work")
            self.remaining = self.total
        else:
            self.total = self._get_default_seconds(self.state)
            self.remaining = self.total

        self._update_display()

        if was_running:
            self.toggle()

    def _quick_switch(self, key):
        """Switch mode instantly (reset current)."""
        state_map = {"work": "work", "short": "short_break", "long": "long_break"}
        state = state_map[key]
        self.running = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self._start_phase(state)

    # ── Run ────────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PomodoroApp()
    app.run()
