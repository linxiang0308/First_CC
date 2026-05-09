# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Desktop Pomodoro Timer built with Python tkinter. Single-file application with a dark theme and circular countdown visualization.

## Architecture

- **`pomodoro.py`** — Main application file (~385 lines)
  - `CircularTimer(tk.Canvas)` — Custom canvas widget drawing a circular progress arc
  - `PomodoroApp` — Main application controller: UI layout, state machine, timer loop
- **`Pomodoro.bat`** — Windows launcher (runs `pythonw pomodoro.py` in background)

### State Machine

`PomodoroApp.state` transitions: `idle` → `work` ↔ `short_break` / `long_break`

- Every 4th work session triggers a `long_break` instead of `short_break`
- Timer uses `root.after(1000, tick)` for 1-second resolution
- `winsound.Beep()` for notification on timer completion

### Configuration Constants

`WORK_MIN`, `SHORT_BREAK_MIN`, `LONG_BREAK_MIN`, `LONG_BREAK_INTERVAL` defined at module top. `COLORS` dict controls the Catppuccin-inspired dark theme — override any value to customize appearance.

## Commands

```bash
# Run the app
python pomodoro.py

# Or double-click Pomodoro.bat (runs via pythonw, no terminal)
```
