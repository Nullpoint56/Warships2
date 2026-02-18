from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import (
    BOTH,
    END,
    LEFT,
    RIGHT,
    VERTICAL,
    BooleanVar,
    StringVar,
    Tk,
    X,
    Y,
    filedialog,
    messagebox,
    ttk,
)
from tkinter.scrolledtext import ScrolledText

_RE_UI_DIAG_FRAME = re.compile(r"ui_diag frame=(\d+) anomalies=(\d+)")
_RE_UI_DIAG_DUMP = re.compile(r"ui_diag_anomaly_dumped .* anomalies=(\[.*\])")


@dataclass(frozen=True)
class RunRecord:
    ts: datetime
    logger: str
    msg: str
    raw: dict[str, object]


@dataclass(frozen=True)
class WarningRecord:
    ts: datetime
    frame_seq: int | None
    anomalies: list[str]
    msg: str


@dataclass(frozen=True)
class UiFrame:
    ts: datetime | None
    frame_seq: int
    resize_seq: int | None
    viewport_revision: int | None
    reasons: list[str]
    anomalies: list[str]
    raw: dict[str, object]


def _parse_ts(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _safe_json_line(line: str) -> dict[str, object] | None:
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _load_run_records(path: Path) -> tuple[list[RunRecord], list[WarningRecord]]:
    records: list[RunRecord] = []
    warnings: list[WarningRecord] = []
    last_frame_seq: int | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        obj = _safe_json_line(line)
        if obj is None:
            continue
        ts = _parse_ts(obj.get("ts"))
        if ts is None:
            continue
        msg = str(obj.get("msg", ""))
        logger = str(obj.get("logger", ""))
        rec = RunRecord(ts=ts, logger=logger, msg=msg, raw=obj)
        records.append(rec)

        frame_match = _RE_UI_DIAG_FRAME.search(msg)
        if frame_match:
            last_frame_seq = int(frame_match.group(1))
            continue
        dump_match = _RE_UI_DIAG_DUMP.search(msg)
        if dump_match:
            anomalies_raw = dump_match.group(1)
            anomalies: list[str] = []
            try:
                parsed = ast.literal_eval(anomalies_raw)
                if isinstance(parsed, list):
                    anomalies = [str(item) for item in parsed]
            except SyntaxError, ValueError:
                anomalies = [anomalies_raw]
            warnings.append(
                WarningRecord(
                    ts=ts,
                    frame_seq=last_frame_seq,
                    anomalies=anomalies,
                    msg=msg,
                )
            )
    records.sort(key=lambda r: r.ts)
    warnings.sort(key=lambda w: w.ts)
    return records, warnings


def _load_ui_frames(path: Path) -> tuple[list[UiFrame], dict[int, UiFrame], int]:
    frames: list[UiFrame] = []
    by_seq: dict[int, UiFrame] = {}
    duplicates = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        obj = _safe_json_line(line)
        if obj is None:
            continue
        frame_seq = obj.get("frame_seq")
        if not isinstance(frame_seq, int):
            continue
        resize_seq = None
        resize_obj = obj.get("resize")
        if isinstance(resize_obj, dict):
            rv = resize_obj.get("resize_seq")
            if isinstance(rv, int):
                resize_seq = rv
        viewport_revision = None
        viewport_obj = obj.get("viewport")
        if isinstance(viewport_obj, dict):
            vv = viewport_obj.get("revision")
            if isinstance(vv, int):
                viewport_revision = vv
        reasons = obj.get("reasons")
        anomalies = obj.get("anomalies")
        frame = UiFrame(
            ts=_parse_ts(obj.get("ts_utc")),
            frame_seq=frame_seq,
            resize_seq=resize_seq,
            viewport_revision=viewport_revision,
            reasons=[str(item) for item in reasons] if isinstance(reasons, list) else [],
            anomalies=[str(item) for item in anomalies] if isinstance(anomalies, list) else [],
            raw=obj,
        )
        frames.append(frame)
        if frame_seq in by_seq:
            duplicates += 1
        by_seq[frame_seq] = frame
    frames.sort(key=lambda f: f.frame_seq)
    return frames, by_seq, duplicates


def _is_non_decreasing(values: list[int]) -> bool:
    return all(values[i] <= values[i + 1] for i in range(len(values) - 1))


class UiDiagViewer:
    def __init__(self, root: Tk, run_log: Path | None, ui_log: Path | None, window_ms: int) -> None:
        self.root = root
        self.root.title("UI Diagnostics Viewer")
        self.window_ms = window_ms
        self.run_log_path = run_log
        self.ui_log_path = ui_log

        self.run_records: list[RunRecord] = []
        self.warning_records: list[WarningRecord] = []
        self.ui_frames: list[UiFrame] = []
        self.ui_frames_by_seq: dict[int, UiFrame] = {}
        self.ui_duplicate_count = 0
        self.run_index_by_ui_frame_seq: dict[int, int] = {}
        self.resize_event_timestamps: list[float] = []
        self.revision_changed_frames: set[int] = set()
        self.geometry_changed_frames: set[int] = set()
        self.suspicious_frames: set[int] = set()
        self.suspicious_reasons: dict[int, list[str]] = {}
        self.frame_spreads: dict[int, tuple[float, float, float]] = {}
        self.scale_spread_frames: set[int] = set()

        self._build_ui()
        if self.run_log_path and self.ui_log_path:
            self._load_and_render()

    def _build_ui(self) -> None:
        controls = ttk.Frame(self.root)
        controls.pack(fill=X, padx=8, pady=6)

        ttk.Label(controls, text="Run log").pack(side=LEFT)
        self.run_log_var = ttk.Entry(controls, width=60)
        self.run_log_var.pack(side=LEFT, padx=4)
        ttk.Button(controls, text="Browse", command=self._browse_run).pack(side=LEFT, padx=2)

        ttk.Label(controls, text="UI diag").pack(side=LEFT, padx=(10, 0))
        self.ui_log_var = ttk.Entry(controls, width=60)
        self.ui_log_var.pack(side=LEFT, padx=4)
        ttk.Button(controls, text="Browse", command=self._browse_ui).pack(side=LEFT, padx=2)
        ttk.Button(controls, text="Load", command=self._load_and_render).pack(
            side=LEFT, padx=(10, 0)
        )

        filters = ttk.Frame(self.root)
        filters.pack(fill=X, padx=8, pady=(0, 6))
        self.only_around_resize_var = BooleanVar(value=False)
        self.revision_changes_only_var = BooleanVar(value=False)
        self.geometry_changed_only_var = BooleanVar(value=False)
        self.suspicious_only_var = BooleanVar(value=False)
        self.spread_only_var = BooleanVar(value=False)
        self.input_after_resize_only_var = BooleanVar(value=False)
        self.resize_mode_var = StringVar(value="both")
        self.window_ms_var = StringVar(value=str(self.window_ms))
        self.primitive_key_prefix_var = StringVar(value="")
        self.spread_threshold_var = StringVar(value="0.001")

        ttk.Checkbutton(
            filters,
            text="Only Around Resize",
            variable=self.only_around_resize_var,
            command=self._apply_filters,
        ).pack(side=LEFT, padx=(0, 8))
        ttk.Label(filters, text="Mode").pack(side=LEFT)
        resize_mode = ttk.Combobox(
            filters,
            width=7,
            textvariable=self.resize_mode_var,
            state="readonly",
            values=("both", "before", "after"),
        )
        resize_mode.pack(side=LEFT, padx=(3, 8))
        resize_mode.bind("<<ComboboxSelected>>", lambda _e: self._apply_filters())
        ttk.Label(filters, text="Window ms").pack(side=LEFT)
        window_entry = ttk.Entry(filters, width=6, textvariable=self.window_ms_var)
        window_entry.pack(side=LEFT, padx=(3, 8))
        window_entry.bind("<Return>", lambda _e: self._apply_filters())
        ttk.Checkbutton(
            filters,
            text="Revision Changes Only",
            variable=self.revision_changes_only_var,
            command=self._apply_filters,
        ).pack(side=LEFT, padx=(0, 8))
        ttk.Checkbutton(
            filters,
            text="Geometry Changed Only",
            variable=self.geometry_changed_only_var,
            command=self._apply_filters,
        ).pack(side=LEFT, padx=(0, 8))
        ttk.Checkbutton(
            filters,
            text="Suspicious Only",
            variable=self.suspicious_only_var,
            command=self._apply_filters,
        ).pack(side=LEFT, padx=(0, 8))
        ttk.Checkbutton(
            filters,
            text="Scale Spread Only",
            variable=self.spread_only_var,
            command=self._apply_filters,
        ).pack(side=LEFT, padx=(0, 8))
        ttk.Checkbutton(
            filters,
            text="Input After Resize",
            variable=self.input_after_resize_only_var,
            command=self._apply_filters,
        ).pack(side=LEFT, padx=(0, 8))
        ttk.Label(filters, text="Spread eps").pack(side=LEFT)
        spread_entry = ttk.Entry(filters, width=7, textvariable=self.spread_threshold_var)
        spread_entry.pack(side=LEFT, padx=(3, 8))
        spread_entry.bind("<Return>", lambda _e: self._apply_filters())
        ttk.Label(filters, text="Primitive Prefix").pack(side=LEFT)
        prefix_entry = ttk.Entry(filters, width=18, textvariable=self.primitive_key_prefix_var)
        prefix_entry.pack(side=LEFT, padx=(3, 8))
        prefix_entry.bind("<Return>", lambda _e: self._on_frame_select(None))
        ttk.Button(filters, text="Apply", command=self._apply_filters).pack(side=LEFT, padx=(0, 6))
        ttk.Button(filters, text="Reset", command=self._reset_filters).pack(side=LEFT, padx=(0, 6))
        ttk.Button(filters, text="Find Suspicious", command=self._find_suspicious).pack(
            side=LEFT, padx=(0, 6)
        )
        ttk.Button(filters, text="Jump Nearest Resize", command=self._jump_nearest_resize).pack(
            side=LEFT
        )

        if self.run_log_path:
            self.run_log_var.insert(0, str(self.run_log_path))
        if self.ui_log_path:
            self.ui_log_var.insert(0, str(self.ui_log_path))

        main = ttk.Panedwindow(self.root, orient="horizontal")
        main.pack(fill=BOTH, expand=True, padx=8, pady=(0, 8))

        left = ttk.Frame(main)
        right = ttk.Frame(main)
        main.add(left, weight=1)
        main.add(right, weight=3)

        ttk.Label(left, text="Warnings").pack(anchor="w")
        self.warning_tree = ttk.Treeview(
            left, columns=("ts", "frame", "anomalies"), show="headings", height=20
        )
        self.warning_tree.heading("ts", text="Timestamp")
        self.warning_tree.heading("frame", text="Frame")
        self.warning_tree.heading("anomalies", text="Anomalies")
        self.warning_tree.column("ts", width=210)
        self.warning_tree.column("frame", width=70, anchor="center")
        self.warning_tree.column("anomalies", width=240)
        y_scroll = ttk.Scrollbar(left, orient=VERTICAL, command=self.warning_tree.yview)
        self.warning_tree.configure(yscrollcommand=y_scroll.set)
        self.warning_tree.pack(side=LEFT, fill=BOTH, expand=True)
        y_scroll.pack(side=RIGHT, fill=Y)
        self.warning_tree.bind("<<TreeviewSelect>>", self._on_warning_select)

        frame_panel = ttk.Frame(self.root)
        frame_panel.pack(fill=BOTH, expand=False, padx=8, pady=(0, 8))
        ttk.Label(frame_panel, text="Frames").pack(anchor="w")
        self.frame_tree = ttk.Treeview(
            frame_panel,
            columns=("frame", "rev", "resize", "sx", "sy", "txtr", "reasons"),
            show="headings",
            height=8,
        )
        self.frame_tree.heading("frame", text="Frame")
        self.frame_tree.heading("rev", text="Viewport Rev")
        self.frame_tree.heading("resize", text="Resize Seq")
        self.frame_tree.heading("sx", text="Spread X")
        self.frame_tree.heading("sy", text="Spread Y")
        self.frame_tree.heading("txtr", text="Spread Text")
        self.frame_tree.heading("reasons", text="Reasons")
        self.frame_tree.column("frame", width=90, anchor="center")
        self.frame_tree.column("rev", width=120, anchor="center")
        self.frame_tree.column("resize", width=100, anchor="center")
        self.frame_tree.column("sx", width=90, anchor="center")
        self.frame_tree.column("sy", width=90, anchor="center")
        self.frame_tree.column("txtr", width=100, anchor="center")
        self.frame_tree.column("reasons", width=500)
        self.frame_tree.pack(fill=X, expand=False)
        self.frame_tree.bind("<<TreeviewSelect>>", self._on_frame_select)

        ttk.Label(right, text="Validation + Event Window").pack(anchor="w")
        self.output = ScrolledText(right, wrap="none")
        self.output.pack(fill=BOTH, expand=True)

    def _browse_run(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("JSONL files", "*.jsonl"), ("All files", "*.*")]
        )
        if path:
            self.run_log_var.delete(0, END)
            self.run_log_var.insert(0, path)

    def _browse_ui(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("JSONL files", "*.jsonl"), ("All files", "*.*")]
        )
        if path:
            self.ui_log_var.delete(0, END)
            self.ui_log_var.insert(0, path)

    def _load_and_render(self) -> None:
        run_path = Path(self.run_log_var.get().strip())
        ui_path = Path(self.ui_log_var.get().strip())
        if not run_path.exists() or not ui_path.exists():
            messagebox.showerror("Missing file", "Both run log and UI diagnostics log must exist.")
            return
        self.run_log_path = run_path
        self.ui_log_path = ui_path

        try:
            self.run_records, self.warning_records = _load_run_records(run_path)
            self.ui_frames, self.ui_frames_by_seq, self.ui_duplicate_count = _load_ui_frames(
                ui_path
            )
            self.run_index_by_ui_frame_seq = self._build_run_index_by_ui_frame_seq()
            self._compute_frame_change_sets()
            self._compute_scale_spread_sets()
            self._compute_suspicious_sets()
            self.resize_event_timestamps = [
                rec.ts.timestamp() for rec in self.run_records if "resize_event " in rec.msg
            ]
        except OSError as exc:
            messagebox.showerror("Load failed", str(exc))
            return

        self.warning_tree.delete(*self.warning_tree.get_children())
        self.frame_tree.delete(*self.frame_tree.get_children())
        for idx, warning in enumerate(self.warning_records):
            frame_text = "" if warning.frame_seq is None else str(warning.frame_seq)
            self.warning_tree.insert(
                "",
                END,
                iid=str(idx),
                values=(
                    warning.ts.isoformat(timespec="milliseconds"),
                    frame_text,
                    ", ".join(warning.anomalies),
                ),
            )
        self._apply_filters()

        self._render_summary()

    def _render_summary(self) -> None:
        frame_seqs = [f.frame_seq for f in self.ui_frames]
        unique_frame_count = len(self.ui_frames_by_seq)
        ui_monotonic = _is_non_decreasing(frame_seqs) if frame_seqs else True

        projection_revisions: list[int] = []
        for rec in self.run_records:
            if "ui_projection revision=" in rec.msg:
                part = rec.msg.split("ui_projection revision=", 1)[1].split(" ", 1)[0]
                try:
                    projection_revisions.append(int(part))
                except ValueError:
                    pass
        projection_monotonic = (
            _is_non_decreasing(projection_revisions) if projection_revisions else True
        )

        unresolved_warnings = 0
        for w in self.warning_records:
            if w.frame_seq is not None and w.frame_seq not in self.ui_frames_by_seq:
                unresolved_warnings += 1

        resize_event_count = sum(1 for rec in self.run_records if "resize_event " in rec.msg)
        projection_event_count = sum(
            1 for rec in self.run_records if "ui_projection revision=" in rec.msg
        )
        input_event_count = sum(
            1
            for rec in self.run_records
            if rec.logger.startswith("engine.input") and "input_event " in rec.msg
        )

        lines = [
            "== Summary ==",
            f"Run log: {self.run_log_path}",
            f"UI log:  {self.ui_log_path}",
            "",
            f"Run records: {len(self.run_records)}",
            f"Warnings (ui_diag_anomaly_dumped): {len(self.warning_records)}",
            f"UI frame rows: {len(self.ui_frames)}",
            f"UI unique frame_seq: {unique_frame_count}",
            f"UI duplicate frame rows: {self.ui_duplicate_count}",
            f"UI frame_seq monotonic: {ui_monotonic}",
            f"Run ui_projection monotonic: {projection_monotonic}",
            f"Warnings with unresolved frame link: {unresolved_warnings}",
            f"Run resize_event count: {resize_event_count}",
            f"Run ui_projection count: {projection_event_count}",
            f"Run input_event count: {input_event_count}",
            "",
            "Select a warning row or frame row to inspect details.",
        ]
        self.output.delete("1.0", END)
        self.output.insert("1.0", "\n".join(lines))

    def _apply_filters(self) -> None:
        try:
            self.window_ms = max(25, int(self.window_ms_var.get()))
        except ValueError:
            self.window_ms = 250
            self.window_ms_var.set("250")
        self._compute_scale_spread_sets()
        self._compute_suspicious_sets()
        self._refresh_frame_tree()

    def _reset_filters(self) -> None:
        self.only_around_resize_var.set(False)
        self.revision_changes_only_var.set(False)
        self.geometry_changed_only_var.set(False)
        self.suspicious_only_var.set(False)
        self.spread_only_var.set(False)
        self.input_after_resize_only_var.set(False)
        self.resize_mode_var.set("both")
        self.window_ms_var.set(str(self.window_ms))
        self.primitive_key_prefix_var.set("")
        self._apply_filters()

    def _refresh_frame_tree(self) -> None:
        self.frame_tree.delete(*self.frame_tree.get_children())
        for frame in self._filtered_frames():
            self.frame_tree.insert(
                "",
                END,
                iid=f"f{frame.frame_seq}",
                values=(
                    frame.frame_seq,
                    "" if frame.viewport_revision is None else frame.viewport_revision,
                    "" if frame.resize_seq is None else frame.resize_seq,
                    f"{self.frame_spreads.get(frame.frame_seq, (0.0, 0.0, 0.0))[0]:.4f}",
                    f"{self.frame_spreads.get(frame.frame_seq, (0.0, 0.0, 0.0))[1]:.4f}",
                    f"{self.frame_spreads.get(frame.frame_seq, (0.0, 0.0, 0.0))[2]:.4f}",
                    ",".join(frame.reasons),
                ),
            )

    def _filtered_frames(self) -> list[UiFrame]:
        frames = self.ui_frames
        if self.revision_changes_only_var.get():
            frames = [f for f in frames if f.frame_seq in self.revision_changed_frames]
        if self.geometry_changed_only_var.get():
            frames = [f for f in frames if f.frame_seq in self.geometry_changed_frames]
        if self.suspicious_only_var.get():
            frames = [f for f in frames if f.frame_seq in self.suspicious_frames]
        if self.spread_only_var.get():
            frames = [f for f in frames if f.frame_seq in self.scale_spread_frames]
        if self.only_around_resize_var.get() and self.resize_event_timestamps:
            mode = self.resize_mode_var.get().strip().lower()
            window_s = self.window_ms / 1000.0
            kept: list[UiFrame] = []
            for frame in frames:
                if frame.ts is None:
                    continue
                ft = frame.ts.timestamp()
                matched = False
                for rt in self.resize_event_timestamps:
                    if mode == "before":
                        if rt - window_s <= ft <= rt:
                            matched = True
                            break
                    elif mode == "after":
                        if rt <= ft <= rt + window_s:
                            matched = True
                            break
                    else:
                        if abs(ft - rt) <= window_s:
                            matched = True
                            break
                if matched:
                    kept.append(frame)
            frames = kept
        return frames

    def _on_warning_select(self, _event: object) -> None:
        selection = self.warning_tree.selection()
        if not selection:
            return
        idx = int(selection[0])
        warning = self.warning_records[idx]
        window_start = warning.ts.timestamp() - (self.window_ms / 1000.0)
        window_end = warning.ts.timestamp() + (self.window_ms / 1000.0)
        nearby = [
            rec
            for rec in self.run_records
            if window_start <= rec.ts.timestamp() <= window_end
            and (
                "ui_diag " in rec.msg
                or "ui_projection " in rec.msg
                or "ui_button_geometry " in rec.msg
                or "resize_event " in rec.msg
                or rec.logger.startswith("engine.input")
            )
        ]

        lines = [
            "== Warning ==",
            f"ts: {warning.ts.isoformat(timespec='milliseconds')}",
            f"frame_seq (from run log): {warning.frame_seq}",
            f"anomalies: {warning.anomalies}",
            "",
            f"== Nearby events (+/- {self.window_ms} ms) ==",
        ]
        for rec in nearby[:200]:
            lines.append(f"{rec.ts.isoformat(timespec='milliseconds')} | {rec.logger} | {rec.msg}")

        if warning.frame_seq is not None:
            lines.extend(["", "== Linked UI frame =="])
            linked = self.ui_frames_by_seq.get(warning.frame_seq)
            if linked is None:
                lines.append("No matching frame_seq found in UI log.")
            else:
                lines.extend(self._format_ui_frame(linked))
                prev_frame = self.ui_frames_by_seq.get(warning.frame_seq - 1)
                next_frame = self.ui_frames_by_seq.get(warning.frame_seq + 1)
                if prev_frame is not None:
                    lines.extend(["", "-- Prev frame --"])
                    lines.extend(self._format_ui_frame(prev_frame))
                if next_frame is not None:
                    lines.extend(["", "-- Next frame --"])
                    lines.extend(self._format_ui_frame(next_frame))

        self.output.delete("1.0", END)
        self.output.insert("1.0", "\n".join(lines))

    def _on_frame_select(self, _event: object) -> None:
        selection = self.frame_tree.selection()
        if not selection:
            return
        frame_id = selection[0]
        if not frame_id.startswith("f"):
            return
        frame_seq = int(frame_id[1:])
        linked = self.ui_frames_by_seq.get(frame_seq)
        if linked is None:
            return
        lines = ["== Selected Frame =="]
        lines.extend(self._format_ui_frame(linked))
        lines.extend(["", "== Button Scale Consistency =="])
        lines.extend(self._format_button_scales(linked))
        reasons = self.suspicious_reasons.get(frame_seq)
        if reasons:
            lines.extend(["", "== Suspicious Signals =="])
            for item in reasons:
                lines.append(f"- {item}")
        lines.extend(["", "== Nearby Run Events =="])
        nearby = self._nearby_run_events_for_frame(frame_seq)
        if not nearby:
            lines.append("No nearby run events found for this frame.")
        else:
            for rec in nearby:
                lines.append(
                    f"{rec.ts.isoformat(timespec='milliseconds')} | {rec.logger} | {rec.msg}"
                )
        lines.extend(["", "== Filtered Primitives =="])
        lines.extend(self._format_primitives(linked))
        lines.extend(["", "== Retained Ops =="])
        lines.extend(self._format_retained_ops(linked))
        lines.extend(["", "== Frame State =="])
        lines.extend(self._format_frame_state(linked))
        prev_frame = self.ui_frames_by_seq.get(frame_seq - 1)
        next_frame = self.ui_frames_by_seq.get(frame_seq + 1)
        if prev_frame is not None:
            lines.extend(["", "-- Prev frame --"])
            lines.extend(self._format_ui_frame(prev_frame))
        if next_frame is not None:
            lines.extend(["", "-- Next frame --"])
            lines.extend(self._format_ui_frame(next_frame))
        self.output.delete("1.0", END)
        self.output.insert("1.0", "\n".join(lines))

    def _build_run_index_by_ui_frame_seq(self) -> dict[int, int]:
        mapping: dict[int, int] = {}
        for idx, rec in enumerate(self.run_records):
            m = _RE_UI_DIAG_FRAME.search(rec.msg)
            if not m:
                continue
            frame_seq = int(m.group(1))
            mapping[frame_seq] = idx
        return mapping

    def _nearby_run_events_for_frame(self, frame_seq: int) -> list[RunRecord]:
        center_idx = self.run_index_by_ui_frame_seq.get(frame_seq)
        if center_idx is not None:
            center_ts = self.run_records[center_idx].ts.timestamp()
            return self._nearby_by_timestamp(center_ts)

        frame = self.ui_frames_by_seq.get(frame_seq)
        if frame is not None and frame.ts is not None:
            return self._nearby_by_timestamp(frame.ts.timestamp())

        return self._nearby_by_shape(frame_seq)

    def _nearby_by_timestamp(self, center_ts: float) -> list[RunRecord]:
        window_start = center_ts - (self.window_ms / 1000.0)
        window_end = center_ts + (self.window_ms / 1000.0)
        rows = [
            rec
            for rec in self.run_records
            if window_start <= rec.ts.timestamp() <= window_end
            and self._is_interesting_run_record(rec)
        ]
        if self.input_after_resize_only_var.get():
            last_resize_ts = max(
                (rec.ts.timestamp() for rec in rows if "resize_event " in rec.msg),
                default=None,
            )
            if last_resize_ts is not None:
                rows = [
                    rec
                    for rec in rows
                    if rec.ts.timestamp() >= last_resize_ts
                    and (rec.logger.startswith("engine.input") or "resize_event " in rec.msg)
                ]
        return rows[:250]

    def _nearby_by_shape(self, frame_seq: int) -> list[RunRecord]:
        frame = self.ui_frames_by_seq.get(frame_seq)
        if frame is None:
            return []
        width = None
        height = None
        if isinstance(frame.raw.get("viewport"), dict):
            width = frame.raw["viewport"].get("width")
            height = frame.raw["viewport"].get("height")
        revision = frame.viewport_revision

        candidates: list[RunRecord] = []
        for rec in self.run_records:
            if not self._is_interesting_run_record(rec):
                continue
            msg = rec.msg
            if revision is not None and f"ui_projection revision={revision}" in msg:
                candidates.append(rec)
                continue
            if (
                width is not None
                and height is not None
                and f"applied_size=({width},{height})" in msg
            ):
                candidates.append(rec)
                continue
        if self.input_after_resize_only_var.get():
            last_resize_ts = max(
                (rec.ts.timestamp() for rec in candidates if "resize_event " in rec.msg),
                default=None,
            )
            if last_resize_ts is not None:
                candidates = [
                    rec
                    for rec in candidates
                    if rec.ts.timestamp() >= last_resize_ts
                    and (rec.logger.startswith("engine.input") or "resize_event " in rec.msg)
                ]
        return candidates[-120:]

    @staticmethod
    def _is_interesting_run_record(rec: RunRecord) -> bool:
        return (
            "ui_diag " in rec.msg
            or "ui_projection " in rec.msg
            or "ui_button_geometry " in rec.msg
            or "resize_event " in rec.msg
            or rec.logger.startswith("engine.input")
        )

    @staticmethod
    def _format_ui_frame(frame: UiFrame) -> list[str]:
        viewport_obj = frame.raw.get("viewport")
        resize_obj = frame.raw.get("resize")
        viewport_text = str(viewport_obj) if isinstance(viewport_obj, dict) else "-"
        resize_text = str(resize_obj) if isinstance(resize_obj, dict) else "-"
        ts_text = frame.ts.isoformat(timespec="milliseconds") if frame.ts is not None else "-"
        return [
            f"ts_utc={ts_text}",
            f"frame_seq={frame.frame_seq}",
            f"reasons={frame.reasons}",
            f"anomalies={frame.anomalies}",
            f"viewport={viewport_text}",
            f"resize={resize_text}",
        ]

    def _compute_frame_change_sets(self) -> None:
        self.revision_changed_frames.clear()
        self.geometry_changed_frames.clear()
        prev_revision: int | None = None
        prev_sig: tuple[tuple[str, tuple[float, float, float, float]], ...] | None = None
        for frame in self.ui_frames:
            rev = frame.viewport_revision
            if prev_revision is not None and rev is not None and rev != prev_revision:
                self.revision_changed_frames.add(frame.frame_seq)
            prev_revision = rev
            sig = self._button_signature(frame)
            if prev_sig is not None and sig != prev_sig:
                self.geometry_changed_frames.add(frame.frame_seq)
            prev_sig = sig

    def _compute_scale_spread_sets(self) -> None:
        self.frame_spreads.clear()
        self.scale_spread_frames.clear()
        try:
            threshold = max(0.0, float(self.spread_threshold_var.get()))
        except ValueError:
            threshold = 0.001
            self.spread_threshold_var.set("0.001")
        for frame in self.ui_frames:
            sx_spread, sy_spread, tr_spread, _ = self._button_scale_metrics(frame)
            self.frame_spreads[frame.frame_seq] = (sx_spread, sy_spread, tr_spread)
            if sx_spread > threshold or sy_spread > threshold or tr_spread > threshold:
                self.scale_spread_frames.add(frame.frame_seq)

    def _find_suspicious(self) -> None:
        self._compute_suspicious_sets()
        count = len(self.suspicious_frames)
        lines = ["== Suspicious Scan =="]
        lines.append(f"Suspicious frames: {count}")
        if count == 0:
            lines.append("No suspicious frames found with current heuristics.")
        else:
            sample = sorted(self.suspicious_frames)[:20]
            lines.append(f"Sample frame_seq: {sample}")
        self.output.delete("1.0", END)
        self.output.insert("1.0", "\n".join(lines))
        self.suspicious_only_var.set(True)
        self._apply_filters()
        if count > 0:
            first = min(self.suspicious_frames)
            iid = f"f{first}"
            if self.frame_tree.exists(iid):
                self.frame_tree.selection_set(iid)
                self.frame_tree.focus(iid)
                self.frame_tree.see(iid)
                self._on_frame_select(None)

    def _compute_suspicious_sets(self) -> None:
        self.suspicious_frames.clear()
        self.suspicious_reasons.clear()
        for frame_seq, reason in self._count_button_rect_changes():
            self._mark_suspicious(frame_seq, reason)
        for frame_seq in self.scale_spread_frames:
            sx, sy, tr = self.frame_spreads.get(frame_seq, (0.0, 0.0, 0.0))
            self._mark_suspicious(
                frame_seq,
                f"button_scale_spread sx={sx:.4f} sy={sy:.4f} text_ratio={tr:.4f}",
            )
        for frame_seq, reason in self._count_ratio_jumps():
            self._mark_suspicious(frame_seq, reason)

    def _mark_suspicious(self, frame_seq: int, reason: str) -> None:
        self.suspicious_frames.add(frame_seq)
        self.suspicious_reasons.setdefault(frame_seq, []).append(reason)

    def _count_button_rect_changes(self) -> list[tuple[int, str]]:
        hits: list[tuple[int, str]] = []
        prev: UiFrame | None = None
        for frame in self.ui_frames:
            if prev is None:
                prev = frame
                continue
            same_rev = (
                frame.viewport_revision is not None
                and frame.viewport_revision == prev.viewport_revision
            )
            same_resize = frame.resize_seq is not None and frame.resize_seq == prev.resize_seq
            if same_rev and same_resize:
                prev_map = self._button_rect_map(prev)
                curr_map = self._button_rect_map(frame)
                if prev_map and curr_map and prev_map != curr_map:
                    hits.append(
                        (
                            frame.frame_seq,
                            "button_rect_changed_without_resize_or_revision_change",
                        )
                    )
            prev = frame
        return hits

    def _count_ratio_jumps(self) -> list[tuple[int, str]]:
        hits: list[tuple[int, str]] = []
        prev: UiFrame | None = None
        jump_threshold = 0.02
        for frame in self.ui_frames:
            if prev is None:
                prev = frame
                continue
            same_rev = (
                frame.viewport_revision is not None
                and frame.viewport_revision == prev.viewport_revision
            )
            same_resize = frame.resize_seq is not None and frame.resize_seq == prev.resize_seq
            if same_rev and same_resize:
                prev_map = self._button_ratio_map(prev)
                curr_map = self._button_ratio_map(frame)
                for key, curr_ratio in curr_map.items():
                    prev_ratio = prev_map.get(key)
                    if prev_ratio is None:
                        continue
                    if abs(curr_ratio - prev_ratio) > jump_threshold:
                        hits.append((frame.frame_seq, f"button_ratio_jump key={key}"))
                        break
            prev = frame
        return hits

    @staticmethod
    def _button_rect_map(frame: UiFrame) -> dict[str, tuple[float, float, float, float]]:
        out: dict[str, tuple[float, float, float, float]] = {}
        for item in (
            frame.raw.get("primitives", []) if isinstance(frame.raw.get("primitives"), list) else []
        ):
            if not isinstance(item, dict):
                continue
            typ = item.get("type")
            key = item.get("key")
            transformed = item.get("transformed")
            if typ != "rect" or not isinstance(key, str) or not key.startswith("button:bg:"):
                continue
            if not isinstance(transformed, dict):
                continue
            x = transformed.get("x")
            y = transformed.get("y")
            w = transformed.get("w")
            h = transformed.get("h")
            if all(isinstance(v, (int, float)) for v in (x, y, w, h)):
                out[key] = (float(x), float(y), float(w), float(h))
        return out

    @staticmethod
    def _button_ratio_map(frame: UiFrame) -> dict[str, float]:
        rect_map: dict[str, tuple[float, float, float, float]] = {}
        text_map: dict[str, tuple[float, float, float, float]] = {}
        for item in (
            frame.raw.get("primitives", []) if isinstance(frame.raw.get("primitives"), list) else []
        ):
            if not isinstance(item, dict):
                continue
            typ = item.get("type")
            key = item.get("key")
            transformed = item.get("transformed")
            if not isinstance(key, str) or not isinstance(transformed, dict):
                continue
            x = transformed.get("x")
            y = transformed.get("y")
            w = transformed.get("w")
            h = transformed.get("h")
            if not all(isinstance(v, (int, float)) for v in (x, y, w, h)):
                continue
            vals = (float(x), float(y), float(w), float(h))
            if typ == "rect" and key.startswith("button:bg:"):
                rect_map[key.removeprefix("button:bg:")] = vals
            if typ == "text" and key.startswith("button:text:"):
                text_map[key.removeprefix("button:text:")] = vals

        out: dict[str, float] = {}
        for name, rect in rect_map.items():
            text = text_map.get(name)
            if text is None:
                continue
            rect_h = rect[3]
            text_h = text[3]
            if rect_h > 0:
                out[name] = text_h / rect_h
        return out

    @staticmethod
    def _button_scale_metrics(
        frame: UiFrame,
    ) -> tuple[float, float, float, dict[str, tuple[float, float, float]]]:
        buttons = frame.raw.get("buttons")
        if not isinstance(buttons, dict):
            return 0.0, 0.0, 0.0, {}

        metrics: dict[str, tuple[float, float, float]] = {}
        sx_values: list[float] = []
        sy_values: list[float] = []
        tr_values: list[float] = []
        for key, value in buttons.items():
            if not isinstance(value, dict):
                continue
            src = value.get("source_rect")
            rect = value.get("rect")
            text_size = value.get("text_size")
            if not isinstance(src, dict) or not isinstance(rect, dict):
                continue
            sw = src.get("w")
            sh = src.get("h")
            rw = rect.get("w")
            rh = rect.get("h")
            if not all(isinstance(v, (int, float)) for v in (sw, sh, rw, rh)):
                continue
            if float(sw) <= 0.0 or float(sh) <= 0.0 or float(rh) <= 0.0:
                continue
            sx = float(rw) / float(sw)
            sy = float(rh) / float(sh)
            text_ratio = (
                float(text_size) / float(rh) if isinstance(text_size, (int, float)) else 0.0
            )
            metrics[str(key)] = (sx, sy, text_ratio)
            sx_values.append(sx)
            sy_values.append(sy)
            tr_values.append(text_ratio)

        if not metrics:
            return 0.0, 0.0, 0.0, {}

        sx_spread = max(sx_values) - min(sx_values)
        sy_spread = max(sy_values) - min(sy_values)
        tr_spread = max(tr_values) - min(tr_values)
        return sx_spread, sy_spread, tr_spread, metrics

    def _format_button_scales(self, frame: UiFrame) -> list[str]:
        sx_spread, sy_spread, tr_spread, metrics = self._button_scale_metrics(frame)
        lines = [
            f"spread_sx={sx_spread:.6f}",
            f"spread_sy={sy_spread:.6f}",
            f"spread_text_ratio={tr_spread:.6f}",
        ]
        if not metrics:
            lines.append("No button metrics available.")
            return lines
        for key in sorted(metrics.keys()):
            sx, sy, tr = metrics[key]
            lines.append(f"{key}: scale_x={sx:.6f} scale_y={sy:.6f} text_ratio={tr:.6f}")
        return lines

    @staticmethod
    def _button_signature(
        frame: UiFrame,
    ) -> tuple[tuple[str, tuple[float, float, float, float]], ...]:
        buttons = frame.raw.get("buttons")
        out: list[tuple[str, tuple[float, float, float, float]]] = []
        if not isinstance(buttons, dict):
            return tuple()
        for key, value in buttons.items():
            if not isinstance(value, dict):
                continue
            rect = value.get("rect")
            if not isinstance(rect, dict):
                continue
            x = rect.get("x")
            y = rect.get("y")
            w = rect.get("w")
            h = rect.get("h")
            if all(isinstance(v, (float, int)) for v in (x, y, w, h)):
                out.append((str(key), (float(x), float(y), float(w), float(h))))
        out.sort(key=lambda i: i[0])
        return tuple(out)

    def _format_primitives(self, frame: UiFrame) -> list[str]:
        primitives = frame.raw.get("primitives")
        if not isinstance(primitives, list) or not primitives:
            return ["No primitives in frame."]
        prefix = self.primitive_key_prefix_var.get().strip()
        rows: list[str] = []
        count = 0
        for item in primitives:
            if not isinstance(item, dict):
                continue
            key = item.get("key")
            if prefix and (not isinstance(key, str) or not key.startswith(prefix)):
                continue
            rows.append(
                "seq={seq} type={typ} key={key} rev={rev} src={src} tx={tx}".format(
                    seq=item.get("seq"),
                    typ=item.get("type"),
                    key=key,
                    rev=item.get("viewport_revision"),
                    src=item.get("source"),
                    tx=item.get("transformed"),
                )
            )
            count += 1
            if count >= 40:
                rows.append("... truncated ...")
                break
        return rows if rows else [f"No primitives matched prefix '{prefix}'."]

    @staticmethod
    def _format_retained_ops(frame: UiFrame) -> list[str]:
        ops = frame.raw.get("retained_ops")
        if not isinstance(ops, list) or not ops:
            return ["No retained ops in frame."]
        rows: list[str] = []
        for item in ops[:80]:
            if not isinstance(item, dict):
                continue
            rows.append(
                "type={typ} key={key} action={act} rev={rev} before={before} after={after}".format(
                    typ=item.get("type"),
                    key=item.get("key"),
                    act=item.get("action"),
                    rev=item.get("viewport_revision"),
                    before=item.get("before"),
                    after=item.get("after"),
                )
            )
        if len(ops) > 80:
            rows.append("... truncated ...")
        return rows

    @staticmethod
    def _format_frame_state(frame: UiFrame) -> list[str]:
        states = frame.raw.get("frame_state")
        if not isinstance(states, list) or not states:
            return ["No frame state snapshots in frame."]
        rows: list[str] = []
        for item in states:
            if isinstance(item, dict):
                rows.append(str(item))
        return rows if rows else ["No frame state snapshots in frame."]

    def _jump_nearest_resize(self) -> None:
        selected = self.frame_tree.selection()
        if not selected:
            return
        frame_id = selected[0]
        if not frame_id.startswith("f"):
            return
        current_seq = int(frame_id[1:])
        current = self.ui_frames_by_seq.get(current_seq)
        if current is None or current.ts is None or not self.resize_event_timestamps:
            return
        ct = current.ts.timestamp()
        nearest_resize = min(self.resize_event_timestamps, key=lambda t: abs(t - ct))
        candidates = [f for f in self.ui_frames if f.ts is not None]
        if not candidates:
            return
        target = min(candidates, key=lambda f: abs(f.ts.timestamp() - nearest_resize))
        target_id = f"f{target.frame_seq}"
        if self.frame_tree.exists(target_id):
            self.frame_tree.selection_set(target_id)
            self.frame_tree.focus(target_id)
            self.frame_tree.see(target_id)
            self._on_frame_select(None)


def _default_logs() -> tuple[Path | None, Path | None]:
    base = Path("warships") / "appdata" / "logs"
    if not base.exists():
        return None, None
    run_candidates = sorted(base.glob("warships_run_*.jsonl"))
    ui_candidates = sorted(base.glob("ui_diag_run_*.jsonl"))
    run_path = run_candidates[-1] if run_candidates else None
    ui_path = ui_candidates[-1] if ui_candidates else None
    return run_path, ui_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Visualize and validate Warships UI diagnostics logs."
    )
    parser.add_argument("--run-log", type=Path, default=None, help="Path to warships_run_*.jsonl")
    parser.add_argument("--ui-log", type=Path, default=None, help="Path to ui_diag_run_*.jsonl")
    parser.add_argument(
        "--window-ms", type=int, default=250, help="Event window around warning timestamp"
    )
    args = parser.parse_args()

    run_log = args.run_log
    ui_log = args.ui_log
    if run_log is None or ui_log is None:
        default_run, default_ui = _default_logs()
        run_log = run_log or default_run
        ui_log = ui_log or default_ui

    root = Tk()
    root.geometry("1450x860")
    UiDiagViewer(root, run_log=run_log, ui_log=ui_log, window_ms=max(25, args.window_ms))
    root.mainloop()


if __name__ == "__main__":
    main()
