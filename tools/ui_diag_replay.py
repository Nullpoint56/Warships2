from __future__ import annotations

import argparse
import json
import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Any


def _safe_json_line(line: str) -> dict[str, Any] | None:
    line = line.strip()
    if not line:
        return None
    try:
        value = json.loads(line)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _load_frames(path: Path) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        obj = _safe_json_line(line)
        if obj is None:
            continue
        if isinstance(obj.get("frame_seq"), int):
            frames.append(obj)
    frames.sort(key=lambda f: int(f.get("frame_seq", 0)))
    return frames


class ReplayApp:
    def __init__(self, root: tk.Tk, log_path: Path | None) -> None:
        self.root = root
        self.root.title("UI Diag Replay")
        self.root.geometry("1600x950")

        self.log_path = log_path
        self.frames: list[dict[str, Any]] = []
        self.index = 0
        self.playing = False
        self.play_ms = 70
        self.key_prefix = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="No log loaded.")
        self._seeking = False

        self._build_ui()
        if self.log_path is not None and self.log_path.exists():
            self._load_log(self.log_path)

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root)
        top.pack(fill=tk.X, padx=8, pady=6)

        self.path_entry = ttk.Entry(top, width=90)
        self.path_entry.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(top, text="Browse", command=self._browse).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(top, text="Load", command=self._load_from_entry).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Button(top, text="<<", command=self._prev).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(top, text="Play/Pause", command=self._toggle_play).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(top, text=">>", command=self._next).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(top, text="Key Prefix").pack(side=tk.LEFT)
        prefix = ttk.Entry(top, width=20, textvariable=self.key_prefix)
        prefix.pack(side=tk.LEFT, padx=(4, 8))
        prefix.bind("<Return>", lambda _e: self._render())

        ttk.Label(top, text="Playback ms").pack(side=tk.LEFT)
        self.ms_spin = ttk.Spinbox(top, width=6, from_=16, to=1000, increment=5)
        self.ms_spin.set(str(self.play_ms))
        self.ms_spin.pack(side=tk.LEFT, padx=(4, 0))

        mid = ttk.Frame(self.root)
        mid.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

        self.canvas = tk.Canvas(mid, bg="#101114", highlightthickness=1, highlightbackground="#333")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.scale = ttk.Scale(self.root, from_=0, to=0, orient=tk.HORIZONTAL, command=self._on_seek)
        self.scale.pack(fill=tk.X, padx=8, pady=(0, 6))

        bottom = ttk.Frame(self.root)
        bottom.pack(fill=tk.BOTH, expand=False, padx=8, pady=(0, 8))
        ttk.Label(bottom, textvariable=self.status_var).pack(anchor="w")

        self.info = tk.Text(bottom, height=10, wrap="none")
        self.info.pack(fill=tk.BOTH, expand=True)

    def _browse(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSONL files", "*.jsonl"), ("All files", "*.*")])
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)

    def _load_from_entry(self) -> None:
        value = self.path_entry.get().strip()
        if not value:
            return
        self._load_log(Path(value))

    def _load_log(self, path: Path) -> None:
        self.frames = _load_frames(path)
        self.log_path = path
        self.path_entry.delete(0, tk.END)
        self.path_entry.insert(0, str(path))
        self.index = 0
        max_idx = max(0, len(self.frames) - 1)
        self.scale.configure(to=max_idx)
        self.scale.set(0)
        self.status_var.set(f"Loaded {len(self.frames)} frames from {path}")
        self._render()

    def _frame(self) -> dict[str, Any] | None:
        if not self.frames:
            return None
        self.index = max(0, min(self.index, len(self.frames) - 1))
        return self.frames[self.index]

    def _render(self, *, update_slider: bool = True) -> None:
        self.canvas.delete("all")
        frame = self._frame()
        if frame is None:
            self.info.delete("1.0", tk.END)
            self.info.insert("1.0", "No frames loaded.")
            return

        viewport = frame.get("viewport") if isinstance(frame.get("viewport"), dict) else {}
        width = int(float(viewport.get("width", 1280)))
        height = int(float(viewport.get("height", 720)))
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        sx = cw / max(1, width)
        sy = ch / max(1, height)

        prefix = self.key_prefix.get().strip()
        drawn = 0
        packet = frame.get("render_packet")
        keyed = packet.get("keyed_transforms") if isinstance(packet, dict) else None
        if isinstance(keyed, dict) and keyed:
            for key, item in keyed.items():
                if not isinstance(key, str) or not isinstance(item, dict):
                    continue
                if prefix and not key.startswith(prefix):
                    continue
                typ = str(item.get("type", ""))
                x = float(item.get("x", 0.0)) * sx
                y = float(item.get("y", 0.0)) * sy
                w = float(item.get("w", 0.0)) * sx
                h = float(item.get("h", 0.0)) * sy
                if not self._draw_item(typ=typ, key=key, x=x, y=y, w=w, h=h):
                    continue
                drawn += 1
        else:
            primitives = frame.get("primitives")
            if isinstance(primitives, list):
                for p in primitives:
                    if not isinstance(p, dict):
                        continue
                    key = p.get("key")
                    if prefix and (not isinstance(key, str) or not key.startswith(prefix)):
                        continue
                    t = p.get("transformed")
                    if not isinstance(t, dict):
                        continue
                    typ = str(p.get("type", ""))
                    x = float(t.get("x", 0.0)) * sx
                    y = float(t.get("y", 0.0)) * sy
                    w = float(t.get("w", 0.0)) * sx
                    h = float(t.get("h", 0.0)) * sy
                    if not self._draw_item(typ=typ, key=key if isinstance(key, str) else "", x=x, y=y, w=w, h=h):
                        continue
                    drawn += 1

        seq = frame.get("frame_seq")
        reasons = frame.get("reasons")
        resize = frame.get("resize")
        self.status_var.set(
            f"frame={seq} index={self.index+1}/{len(self.frames)} drawn={drawn} reasons={reasons} resize={resize}"
        )

        self.info.delete("1.0", tk.END)
        self.info.insert("1.0", json.dumps(frame, indent=2))
        if update_slider and not self._seeking:
            self.scale.set(self.index)

    def _draw_item(self, *, typ: str, key: str, x: float, y: float, w: float, h: float) -> bool:
        vals = (x, y, w, h)
        if not all(math.isfinite(v) for v in vals):
            return False
        x2 = x + max(0.0, w)
        y2 = y + max(0.0, h)
        # Clip huge values to keep Tk canvas stable.
        limit = 1_000_000.0
        if any(abs(v) > limit for v in (x, y, x2, y2)):
            return False
        if typ in ("window_rect", "rect"):
            color = "#102040" if typ == "window_rect" else "#2a72ff"
            self.canvas.create_rectangle(x, y, x2, y2, outline="", fill=color)
            return True
        if typ == "grid":
            self.canvas.create_rectangle(x, y, x2, y2, outline="#5a5a5a")
            return True
        if typ == "text":
            self.canvas.create_text(x, y, text=key or "text", anchor="nw", fill="#f0f0f0")
            return True
        return False

    def _prev(self) -> None:
        if not self.frames:
            return
        self.index = max(0, self.index - 1)
        self._render()

    def _next(self) -> None:
        if not self.frames:
            return
        self.index = min(len(self.frames) - 1, self.index + 1)
        self._render()

    def _on_seek(self, value: str) -> None:
        if not self.frames:
            return
        try:
            idx = int(float(value))
        except ValueError:
            return
        self._seeking = True
        try:
            self.index = max(0, min(idx, len(self.frames) - 1))
            self._render(update_slider=False)
        finally:
            self._seeking = False

    def _toggle_play(self) -> None:
        self.playing = not self.playing
        if self.playing:
            try:
                self.play_ms = max(16, int(self.ms_spin.get()))
            except ValueError:
                self.play_ms = 70
                self.ms_spin.set(str(self.play_ms))
            self._tick_play()

    def _tick_play(self) -> None:
        if not self.playing:
            return
        if self.frames:
            self.index = (self.index + 1) % len(self.frames)
            self._render()
        self.root.after(self.play_ms, self._tick_play)


def _default_ui_log() -> Path | None:
    base = Path("warships") / "appdata" / "logs"
    if not base.exists():
        return None
    candidates = sorted(base.glob("ui_diag_run_*.jsonl"))
    return candidates[-1] if candidates else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay UI diagnostic frames from ui_diag_run_*.jsonl")
    parser.add_argument("--ui-log", type=Path, default=None, help="Path to ui_diag_run_*.jsonl")
    args = parser.parse_args()
    ui_log = args.ui_log or _default_ui_log()
    root = tk.Tk()
    ReplayApp(root, ui_log)
    root.mainloop()


if __name__ == "__main__":
    main()
