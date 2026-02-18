from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import (
    BOTH,
    END,
    LEFT,
    RIGHT,
    VERTICAL,
    BooleanVar,
    Canvas,
    StringVar,
    Tk,
    X,
    Y,
    filedialog,
    ttk,
)
from tkinter.scrolledtext import ScrolledText
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.api.debug import (  # noqa: E402
    DebugLoadedSession,
    DebugSessionBundle,
    discover_debug_sessions,
    load_debug_session,
)

RE_FRAME_METRICS = re.compile(
    r"frame_metrics frame=(?P<frame>\d+) "
    r"dt_ms=(?P<dt>[0-9]+(?:\.[0-9]+)?) "
    r"fps=(?P<fps>[0-9]+(?:\.[0-9]+)?)"
)
RE_TOP_LIST = re.compile(r"top=(?P<top>\[.*\])$")
RE_MEMORY_KV = re.compile(
    r"(?P<key>rss_mb|memory_mb|ram_mb|vram_mb)=(?P<value>[0-9]+(?:\.[0-9]+)?)"
)


@dataclass(frozen=True)
class UiEvent:
    ts: datetime | None
    source: str
    family: str
    severity: str
    msg: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class ProfileSample:
    frame_index: int
    dt_ms: float
    fps_rolling: float
    scheduler_queue_size: int
    top_system_name: str
    top_system_ms: float
    top_event_name: str
    top_event_count: int
    publish_count: int
    bottlenecks: tuple[str, ...]
    systems_timings_ms: dict[str, float]
    events_by_topic: dict[str, int]
    memory: dict[str, float]
    ts: str
    raw: dict[str, Any]


def _parse_ts(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _default_logs_dir() -> Path:
    preferred = ROOT / "tools" / "data" / "logs"
    if preferred.exists():
        return preferred
    fallback = Path.cwd() / "warships" / "appdata" / "logs"
    if fallback.exists():
        return fallback
    return preferred


class App:
    def __init__(self, root: Tk, logs_dir: Path) -> None:
        self.root = root
        self.logs_dir = logs_dir
        self.root.title("Engine Observability")
        self.root.geometry("1680x980")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.bundles: list[DebugSessionBundle] = discover_debug_sessions(logs_dir, recursive=True)
        self.loaded: DebugLoadedSession | None = None
        self.frame_rows: list[dict[str, Any]] = []
        self.frame_idx_by_seq: dict[int, int] = {}
        self.events: list[UiEvent] = []
        self.samples: list[tuple[int, float, float, float | None, float | None, str]] = []
        self.profile_samples: list[ProfileSample] = []
        self.sample_top_by_frame: dict[int, dict[str, float]] = {}
        self.memory_samples: dict[str, list[float]] = {}
        self.hitches: list[dict[str, Any]] = []
        self.session_map: dict[str, int] = {}
        self.loaded_profile_export: dict[str, Any] | None = None
        self.loaded_replay_export: dict[str, Any] | None = None
        self.loaded_crash_bundle: dict[str, Any] | None = None

        self.session_var = StringVar()
        self.logs_dir_var = StringVar(value=str(self.logs_dir))
        self.profile_export_var = StringVar(value="")
        self.replay_export_var = StringVar(value="")
        self.crash_bundle_var = StringVar(value="")
        self.status_var = StringVar(value="No session loaded.")
        self.replay_var = StringVar(value="frame_index=0")
        self.replay_fps = StringVar(value="60")
        self.replay_realtime = BooleanVar(value=True)
        self.replay_mode_var = StringVar(value="stopped")
        self.events_search = StringVar(value="")
        self.events_severity = StringVar(value="all")
        self.events_family = StringVar(value="all")
        self.events_range = StringVar(value="all")
        self.events_count_var = StringVar(value="0 / 0")
        self.runs_search = StringVar(value="")
        self.runs_count_var = StringVar(value="0")
        self.hitch_thresh = StringVar(value="25")
        self.perf_count_var = StringVar(value="hitches=0 samples=0")

        self.frame_scale: ttk.Scale | None = None
        self.replay_after_id: str | None = None
        self.canvas: Canvas | None = None
        self.replay_text: ScrolledText | None = None
        self.events_tree: ttk.Treeview | None = None
        self.events_detail: ScrolledText | None = None
        self.runs_tree: ttk.Treeview | None = None
        self.runs_text: ScrolledText | None = None
        self.crash_text: ScrolledText | None = None
        self.perf_text: ScrolledText | None = None
        self.hitch_tree: ttk.Treeview | None = None
        self.sample_tree: ttk.Treeview | None = None
        self.system_tree: ttk.Treeview | None = None
        self.perf_canvas: Canvas | None = None
        self.perf_system_canvas: Canvas | None = None
        self.perf_event_canvas: Canvas | None = None
        self.perf_memory_canvas: Canvas | None = None

        self._build()
        self._refresh_sessions()

    def _build(self) -> None:
        top = ttk.Frame(self.root)
        top.pack(fill=X, padx=8, pady=6)

        ttk.Label(top, text="Logs Dir").pack(side=LEFT)
        logs_entry = ttk.Entry(top, width=62, textvariable=self.logs_dir_var)
        logs_entry.pack(side=LEFT, padx=4)
        ttk.Button(top, text="Pick Logs Dir", command=self._pick_logs_dir).pack(
            side=LEFT,
            padx=4,
        )
        ttk.Button(top, text="Open Run/UI Files", command=self._open_run_ui_files).pack(
            side=LEFT,
            padx=4,
        )
        ttk.Button(top, text="Open Profiling JSON", command=self._open_profiling_json).pack(
            side=LEFT,
            padx=4,
        )
        ttk.Button(top, text="Open Replay JSON", command=self._open_replay_json).pack(
            side=LEFT,
            padx=4,
        )
        ttk.Button(top, text="Open Crash Bundle", command=self._open_crash_bundle_json).pack(
            side=LEFT,
            padx=4,
        )
        ttk.Button(top, text="Save Crash Bundle", command=self._save_crash_bundle_json).pack(
            side=LEFT,
            padx=4,
        )
        ttk.Button(top, text="Refresh", command=self._refresh_sessions).pack(
            side=LEFT,
            padx=6,
        )
        logs_entry.bind("<Return>", lambda _e: self._refresh_sessions())

        sessions_row = ttk.Frame(self.root)
        sessions_row.pack(fill=X, padx=8)
        ttk.Label(sessions_row, text="Session").pack(side=LEFT)
        self.session_combo = ttk.Combobox(
            sessions_row,
            width=90,
            textvariable=self.session_var,
            state="readonly",
        )
        self.session_combo.pack(side=LEFT, padx=4)
        self.session_combo.bind("<<ComboboxSelected>>", lambda _e: self._load_selected())

        ttk.Label(self.root, textvariable=self.status_var).pack(anchor="w", padx=8)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=BOTH, expand=True, padx=8, pady=8)

        replay_tab = ttk.Frame(notebook)
        events_tab = ttk.Frame(notebook)
        runs_tab = ttk.Frame(notebook)
        perf_tab = ttk.Frame(notebook)

        notebook.add(replay_tab, text="Replay")
        notebook.add(events_tab, text="Events")
        notebook.add(runs_tab, text="Runs/Crashes")
        notebook.add(perf_tab, text="Profiling")

        self._build_replay(replay_tab)
        self._build_events(events_tab)
        self._build_runs(runs_tab)
        self._build_perf(perf_tab)

    def _build_replay(self, tab: ttk.Frame) -> None:
        controls = ttk.LabelFrame(tab, text="Replay Controls")
        controls.pack(fill=X, pady=6)

        ttk.Button(controls, text="Prev", command=lambda: self._step(-1)).pack(
            side=LEFT,
            padx=4,
            pady=4,
        )
        ttk.Button(controls, text="Next", command=lambda: self._step(1)).pack(
            side=LEFT,
            padx=4,
            pady=4,
        )
        ttk.Button(controls, text="Next Hitch", command=self._jump_hitch).pack(
            side=LEFT,
            padx=4,
            pady=4,
        )
        ttk.Button(controls, text="Next Resize", command=self._jump_resize).pack(
            side=LEFT,
            padx=4,
            pady=4,
        )
        ttk.Button(controls, text="Next Anomaly", command=self._jump_anomaly).pack(
            side=LEFT,
            padx=4,
            pady=4,
        )
        ttk.Button(controls, text="Play", command=self._play_start).pack(
            side=LEFT,
            padx=4,
            pady=4,
        )
        ttk.Button(controls, text="Pause", command=self._play_stop).pack(
            side=LEFT,
            padx=4,
            pady=4,
        )
        ttk.Label(controls, text="FPS").pack(side=LEFT, padx=4)
        fps_combo = ttk.Combobox(
            controls,
            width=5,
            state="readonly",
            textvariable=self.replay_fps,
            values=("15", "30", "60", "120"),
        )
        fps_combo.pack(side=LEFT)
        ttk.Checkbutton(
            controls,
            text="Real-time timing",
            variable=self.replay_realtime,
        ).pack(side=LEFT, padx=6)
        ttk.Label(controls, textvariable=self.replay_mode_var).pack(side=LEFT, padx=8)
        ttk.Label(controls, textvariable=self.replay_var).pack(side=LEFT, padx=8)

        split = ttk.Panedwindow(tab, orient="horizontal")
        split.pack(fill=BOTH, expand=True)
        visual = ttk.LabelFrame(split, text="Visual")
        details = ttk.LabelFrame(split, text="Details")
        split.add(visual, weight=3)
        split.add(details, weight=2)

        self.canvas = Canvas(visual, bg="#11141a")
        self.canvas.pack(fill=BOTH, expand=True)
        self.replay_text = ScrolledText(details, wrap="none")
        self.replay_text.pack(fill=BOTH, expand=True)

        self.frame_scale = ttk.Scale(
            tab,
            from_=0,
            to=0,
            orient="horizontal",
            command=self._seek,
        )
        self.frame_scale.pack(fill=X, pady=6)

    def _build_events(self, tab: ttk.Frame) -> None:
        controls = ttk.LabelFrame(tab, text="Event Filters")
        controls.pack(fill=X, pady=6)

        ttk.Label(controls, text="Range").pack(side=LEFT, padx=4)
        range_combo = ttk.Combobox(
            controls,
            width=10,
            state="readonly",
            textvariable=self.events_range,
            values=("all", "last_5s", "last_30s", "last_120s"),
        )
        range_combo.pack(side=LEFT)

        ttk.Label(controls, text="Severity").pack(side=LEFT, padx=4)
        sev_combo = ttk.Combobox(
            controls,
            width=10,
            state="readonly",
            textvariable=self.events_severity,
            values=("all", "warnings+", "errors+"),
        )
        sev_combo.pack(side=LEFT)

        ttk.Label(controls, text="Family").pack(side=LEFT, padx=4)
        fam_combo = ttk.Combobox(
            controls,
            width=10,
            state="readonly",
            textvariable=self.events_family,
            values=("all", "input", "resize", "state", "render"),
        )
        fam_combo.pack(side=LEFT)

        ttk.Label(controls, text="Search").pack(side=LEFT, padx=4)
        query_entry = ttk.Entry(controls, width=30, textvariable=self.events_search)
        query_entry.pack(side=LEFT)
        ttk.Label(controls, text="Shown/Total").pack(side=LEFT, padx=8)
        ttk.Label(controls, textvariable=self.events_count_var).pack(side=LEFT)

        for widget in (range_combo, sev_combo, fam_combo):
            widget.bind("<<ComboboxSelected>>", lambda _e: self._refresh_events())
        query_entry.bind("<Return>", lambda _e: self._refresh_events())

        split = ttk.Panedwindow(tab, orient="horizontal")
        split.pack(fill=BOTH, expand=True)

        events_frame = ttk.LabelFrame(split, text="Events")
        payload_frame = ttk.LabelFrame(split, text="Payload")
        split.add(events_frame, weight=3)
        split.add(payload_frame, weight=2)

        columns = ("ts", "source", "family", "severity", "msg")
        tree = ttk.Treeview(events_frame, columns=columns, show="headings")
        sizes = (("ts", 190), ("source", 240), ("family", 90), ("severity", 90), ("msg", 700))
        for col, width in sizes:
            tree.heading(col, text=col.upper())
            tree.column(col, width=width, anchor="w")

        bar = ttk.Scrollbar(events_frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=bar.set)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        bar.pack(side=RIGHT, fill=Y)
        tree.bind("<<TreeviewSelect>>", self._event_select)
        self.events_tree = tree

        self.events_detail = ScrolledText(payload_frame, wrap="none")
        self.events_detail.pack(fill=BOTH, expand=True)

    def _build_runs(self, tab: ttk.Frame) -> None:
        controls = ttk.LabelFrame(tab, text="Run Log Filters")
        controls.pack(fill=X, pady=6)
        ttk.Label(controls, text="Search").pack(side=LEFT, padx=4)
        search_entry = ttk.Entry(controls, width=40, textvariable=self.runs_search)
        search_entry.pack(side=LEFT)
        search_entry.bind("<Return>", lambda _e: self._refresh_runs())
        ttk.Label(controls, text="Rows").pack(side=LEFT, padx=8)
        ttk.Label(controls, textvariable=self.runs_count_var).pack(side=LEFT)

        split = ttk.Panedwindow(tab, orient="vertical")
        split.pack(fill=BOTH, expand=True)
        summary_frame = ttk.LabelFrame(split, text="Summary")
        crash_frame = ttk.LabelFrame(split, text="Crash Focus")
        logs_frame = ttk.LabelFrame(split, text="Warnings/Errors")
        split.add(summary_frame, weight=1)
        split.add(crash_frame, weight=1)
        split.add(logs_frame, weight=3)

        self.runs_text = ScrolledText(summary_frame, wrap="none", height=8)
        self.runs_text.pack(fill=BOTH, expand=True)
        self.crash_text = ScrolledText(crash_frame, wrap="none", height=8)
        self.crash_text.pack(fill=BOTH, expand=True)

        columns = ("ts", "logger", "level", "msg")
        tree = ttk.Treeview(logs_frame, columns=columns, show="headings")
        sizes = (("ts", 190), ("logger", 260), ("level", 90), ("msg", 900))
        for col, width in sizes:
            tree.heading(col, text=col.upper())
            tree.column(col, width=width, anchor="w")

        bar = ttk.Scrollbar(logs_frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=bar.set)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        bar.pack(side=RIGHT, fill=Y)
        self.runs_tree = tree

    def _build_perf(self, tab: ttk.Frame) -> None:
        controls = ttk.LabelFrame(tab, text="Performance Filters")
        controls.pack(fill=X, pady=6)
        ttk.Label(controls, text="Hitch >= ms").pack(side=LEFT, padx=4)
        hitch_combo = ttk.Combobox(
            controls,
            width=6,
            state="readonly",
            textvariable=self.hitch_thresh,
            values=("16", "25", "33", "50"),
        )
        hitch_combo.pack(side=LEFT)
        hitch_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_perf())
        ttk.Label(controls, text="Counts").pack(side=LEFT, padx=8)
        ttk.Label(controls, textvariable=self.perf_count_var).pack(side=LEFT)

        split = ttk.Panedwindow(tab, orient="vertical")
        split.pack(fill=BOTH, expand=True)
        metrics_frame = ttk.LabelFrame(split, text="Metrics")
        chart_frame = ttk.LabelFrame(split, text="Visuals")
        hitches_frame = ttk.LabelFrame(split, text="Blocking Frames")
        samples_frame = ttk.LabelFrame(split, text="Runtime Samples")
        systems_frame = ttk.LabelFrame(split, text="Systems / Memory")
        split.add(metrics_frame, weight=1)
        split.add(chart_frame, weight=1)
        split.add(hitches_frame, weight=2)
        split.add(samples_frame, weight=2)
        split.add(systems_frame, weight=2)

        self.perf_text = ScrolledText(metrics_frame, wrap="none", height=7)
        self.perf_text.pack(fill=BOTH, expand=True)
        chart_notebook = ttk.Notebook(chart_frame)
        chart_notebook.pack(fill=BOTH, expand=True)

        frame_tab = ttk.Frame(chart_notebook)
        system_tab = ttk.Frame(chart_notebook)
        event_tab = ttk.Frame(chart_notebook)
        memory_tab = ttk.Frame(chart_notebook)
        chart_notebook.add(frame_tab, text="Frame")
        chart_notebook.add(system_tab, text="Systems")
        chart_notebook.add(event_tab, text="Events/Bottlenecks")
        chart_notebook.add(memory_tab, text="Memory")

        self.perf_canvas = Canvas(frame_tab, bg="#0e1218", height=180)
        self.perf_canvas.pack(fill=BOTH, expand=True)
        self.perf_system_canvas = Canvas(system_tab, bg="#0e1218", height=180)
        self.perf_system_canvas.pack(fill=BOTH, expand=True)
        self.perf_event_canvas = Canvas(event_tab, bg="#0e1218", height=180)
        self.perf_event_canvas.pack(fill=BOTH, expand=True)
        self.perf_memory_canvas = Canvas(memory_tab, bg="#0e1218", height=180)
        self.perf_memory_canvas.pack(fill=BOTH, expand=True)

        hitch_tree = ttk.Treeview(
            hitches_frame,
            columns=("frame", "dt_ms", "bottleneck", "top_system", "top_event", "queue", "ts"),
            show="headings",
        )
        for col, width in (
            ("frame", 90),
            ("dt_ms", 90),
            ("bottleneck", 180),
            ("top_system", 160),
            ("top_event", 160),
            ("queue", 80),
            ("ts", 220),
        ):
            hitch_tree.heading(col, text=col.upper())
            hitch_tree.column(col, width=width, anchor="w")
        hitch_bar = ttk.Scrollbar(hitches_frame, orient=VERTICAL, command=hitch_tree.yview)
        hitch_tree.configure(yscrollcommand=hitch_bar.set)
        hitch_tree.pack(side=LEFT, fill=BOTH, expand=True)
        hitch_bar.pack(side=RIGHT, fill=Y)
        hitch_tree.bind("<Double-1>", self._hitch_select)
        self.hitch_tree = hitch_tree

        sample_tree = ttk.Treeview(
            samples_frame,
            columns=("frame", "dt", "render", "non_render", "fps", "top_system", "top_event", "ts"),
            show="headings",
        )
        sizes = (
            ("frame", 90),
            ("dt", 100),
            ("render", 110),
            ("non_render", 130),
            ("fps", 90),
            ("top_system", 180),
            ("top_event", 180),
            ("ts", 250),
        )
        for col, width in sizes:
            sample_tree.heading(col, text=col.upper())
            sample_tree.column(col, width=width, anchor="w")
        sample_bar = ttk.Scrollbar(
            samples_frame,
            orient=VERTICAL,
            command=sample_tree.yview,
        )
        sample_tree.configure(yscrollcommand=sample_bar.set)
        sample_tree.pack(side=LEFT, fill=BOTH, expand=True)
        sample_bar.pack(side=RIGHT, fill=Y)
        self.sample_tree = sample_tree

        system_tree = ttk.Treeview(
            systems_frame,
            columns=("system", "mean_ms", "max_ms", "share_pct"),
            show="headings",
        )
        for col, width in (
            ("system", 260),
            ("mean_ms", 100),
            ("max_ms", 100),
            ("share_pct", 100),
        ):
            system_tree.heading(col, text=col.upper())
            system_tree.column(col, width=width, anchor="w")
        system_bar = ttk.Scrollbar(
            systems_frame,
            orient=VERTICAL,
            command=system_tree.yview,
        )
        system_tree.configure(yscrollcommand=system_bar.set)
        system_tree.pack(side=LEFT, fill=BOTH, expand=True)
        system_bar.pack(side=RIGHT, fill=Y)
        self.system_tree = system_tree

    def _refresh_sessions(self) -> None:
        self._play_stop()
        self.logs_dir = Path(self.logs_dir_var.get().strip() or self.logs_dir)
        self.logs_dir_var.set(str(self.logs_dir))
        self.bundles = discover_debug_sessions(self.logs_dir, recursive=True)
        self.session_map.clear()
        labels: list[str] = []
        for idx, bundle in enumerate(self.bundles):
            run_name = bundle.run_log.name if bundle.run_log else "n/a"
            ui_name = bundle.ui_log.name if bundle.ui_log else "n/a"
            label = f"[{idx}] run={run_name} | ui={ui_name}"
            labels.append(label)
            self.session_map[label] = idx

        self.session_combo["values"] = labels
        if not labels:
            self.status_var.set("No sessions discovered.")
            return

        self.session_var.set(labels[0])
        self._load_selected()

    def _load_selected(self) -> None:
        index = self.session_map.get(self.session_var.get().strip())
        if index is None:
            return

        loaded = load_debug_session(self.bundles[index])
        self._apply_loaded_session(loaded, label=f"session {index}")

    def _apply_loaded_session(self, loaded: DebugLoadedSession, *, label: str) -> None:
        self._play_stop()
        self.loaded = loaded
        self.frame_rows = self.loaded.ui_frames
        self.frame_idx_by_seq = {
            int(frame["frame_seq"]): idx for idx, frame in enumerate(self.frame_rows)
        }
        self.events = self._make_events()
        self.samples = self._make_samples()
        self.profile_samples = self._make_profile_samples()

        self.status_var.set(
            "Loaded "
            f"{label}: frames={len(self.frame_rows)} "
            f"run_records={len(self.loaded.run_records)}"
        )

        if self.frame_scale is not None:
            self.frame_scale.configure(to=max(0, len(self.frame_rows) - 1))
            self.frame_scale.set(0)
        self._render_frame(0)
        self._refresh_events()
        self._refresh_runs()
        self._refresh_perf()

    def _pick_logs_dir(self) -> None:
        selected = filedialog.askdirectory(
            title="Select logs directory",
            initialdir=self.logs_dir_var.get() or str(_default_logs_dir()),
        )
        if not selected:
            return
        self.logs_dir_var.set(selected)
        self._refresh_sessions()

    def _open_run_ui_files(self) -> None:
        initial_dir = self.logs_dir_var.get() or str(_default_logs_dir())
        run_path_raw = filedialog.askopenfilename(
            title="Select run log",
            initialdir=initial_dir,
            filetypes=[("Run Logs", "warships_run_*.jsonl"), ("JSONL", "*.jsonl")],
        )
        if not run_path_raw:
            return
        ui_path_raw = filedialog.askopenfilename(
            title="Select UI log (optional)",
            initialdir=initial_dir,
            filetypes=[("UI Logs", "ui_diag_run_*.jsonl"), ("JSONL", "*.jsonl")],
        )

        run_path = Path(run_path_raw)
        ui_path = Path(ui_path_raw) if ui_path_raw else None
        bundle = DebugSessionBundle(
            run_log=run_path,
            ui_log=ui_path,
            run_stamp=None,
            ui_stamp=None,
        )
        loaded = load_debug_session(bundle)
        self._apply_loaded_session(loaded, label=run_path.name)

    def _open_profiling_json(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select profiling export JSON",
            initialdir=str(ROOT / "tools" / "data" / "profiles"),
            filetypes=[("JSON", "*.json"), ("All Files", "*.*")],
        )
        if not selected:
            return
        path = Path(selected)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.status_var.set(f"Failed to load profiling JSON: {exc}")
            return
        if not isinstance(payload, dict):
            self.status_var.set("Profiling JSON payload must be an object.")
            return
        self.loaded_profile_export = payload
        self.profile_export_var.set(str(path))
        if self.loaded is not None:
            self.profile_samples = self._make_profile_samples()
            self._refresh_perf()
        self.status_var.set(f"Loaded profiling export: {path.name}")

    def _open_replay_json(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select replay export JSON",
            initialdir=str(ROOT / "tools" / "data" / "replay"),
            filetypes=[("JSON", "*.json"), ("All Files", "*.*")],
        )
        if not selected:
            return
        path = Path(selected)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.status_var.set(f"Failed to load replay JSON: {exc}")
            return
        if not isinstance(payload, dict):
            self.status_var.set("Replay JSON payload must be an object.")
            return
        self.loaded_replay_export = payload
        self.replay_export_var.set(str(path))
        if self.frame_scale is not None:
            self._render_frame(int(float(self.frame_scale.get())))
        self.status_var.set(f"Loaded replay export: {path.name}")

    def _open_crash_bundle_json(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select crash bundle JSON",
            initialdir=str(ROOT / "tools" / "data" / "crash"),
            filetypes=[("JSON", "*.json"), ("All Files", "*.*")],
        )
        if not selected:
            return
        path = Path(selected)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.status_var.set(f"Failed to load crash bundle JSON: {exc}")
            return
        if not isinstance(payload, dict):
            self.status_var.set("Crash bundle JSON payload must be an object.")
            return
        self.loaded_crash_bundle = payload
        self.crash_bundle_var.set(str(path))
        if self.loaded is not None:
            self._refresh_crash_focus()
        self.status_var.set(f"Loaded crash bundle: {path.name}")

    def _save_crash_bundle_json(self) -> None:
        payload = self._build_crash_bundle_payload_for_save()
        if payload is None:
            self.status_var.set(
                "No crash bundle or session loaded; open a crash bundle or load a run first."
            )
            return
        default_dir = ROOT / "tools" / "data" / "crash"
        default_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        selected = filedialog.asksaveasfilename(
            title="Save crash bundle JSON",
            initialdir=str(default_dir),
            initialfile=f"engine_crash_bundle_{stamp}.json",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All Files", "*.*")],
        )
        if not selected:
            return
        path = Path(selected)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.status_var.set(f"Failed to save crash bundle JSON: {exc}")
            return
        self.loaded_crash_bundle = payload
        self.crash_bundle_var.set(str(path))
        if self.loaded is not None:
            self._refresh_crash_focus()
        self.status_var.set(f"Saved crash bundle: {path.name}")

    def _build_crash_bundle_payload_for_save(self) -> dict[str, Any] | None:
        if isinstance(self.loaded_crash_bundle, dict):
            return dict(self.loaded_crash_bundle)
        if self.loaded is None:
            return None

        crash_records: list[dict[str, Any]] = []
        for record in self.loaded.run_records:
            level = str(record.get("level", "")).upper()
            msg = str(record.get("msg", ""))
            if level in {"ERROR", "CRITICAL"} or "exception" in msg.lower():
                crash_records.append(record)

        recent_events = crash_records[-200:]
        selected_tick = 0
        if self.frame_scale is not None:
            selected_tick = int(float(self.frame_scale.get()))
        if self.frame_rows:
            selected_tick = int(
                self.frame_rows[min(selected_tick, len(self.frame_rows) - 1)].get(
                    "frame_seq", selected_tick
                )
            )

        head_msg = str(crash_records[0].get("msg", "")) if crash_records else ""
        exception_payload: dict[str, Any] | None
        if head_msg:
            exception_payload = {
                "type": "RuntimeError",
                "message": head_msg,
                "traceback": [],
            }
        else:
            exception_payload = None

        return {
            "schema_version": "engine.crash_bundle.v1",
            "captured_at_utc": datetime.now().isoformat(timespec="milliseconds"),
            "tick": int(selected_tick),
            "reason": "manual_export_from_observability_tool",
            "exception": exception_payload,
            "runtime": {
                "source": "tools.engine_observability",
                "run_records": len(self.loaded.run_records),
                "ui_frames": len(self.loaded.ui_frames),
            },
            "recent_events": recent_events,
            "profiling": {},
            "replay": {},
        }

    def _make_events(self) -> list[UiEvent]:
        if self.loaded is None:
            return []

        result: list[UiEvent] = []
        for record in self.loaded.run_records:
            msg = str(record.get("msg", ""))
            source = str(record.get("logger", ""))

            if "input" in source.lower() or "pointer" in msg.lower():
                family = "input"
            elif "resize" in msg.lower():
                family = "resize"
            elif "state" in msg.lower():
                family = "state"
            elif "render" in source.lower() or "ui_diag" in msg.lower():
                family = "render"
            else:
                family = "other"

            level = str(record.get("level", "")).upper()
            if level in {"ERROR", "CRITICAL"} or "exception" in msg.lower():
                severity = "error"
            elif level in {"WARNING", "WARN"}:
                severity = "warning"
            else:
                severity = "info"

            result.append(
                UiEvent(
                    ts=_parse_ts(record.get("ts")),
                    source=source,
                    family=family,
                    severity=severity,
                    msg=msg,
                    raw=record,
                )
            )

        for frame in self.frame_rows:
            result.append(
                UiEvent(
                    ts=_parse_ts(frame.get("ts_utc")),
                    source="engine.rendering.ui_diag",
                    family="render",
                    severity="warning" if frame.get("anomalies") else "info",
                    msg=f"frame={frame.get('frame_seq')} reasons={frame.get('reasons')}",
                    raw=frame,
                )
            )

        result.sort(key=lambda item: item.ts or datetime.min)
        return result

    def _make_samples(self) -> list[tuple[int, float, float, float | None, float | None, str]]:
        if self.loaded is None:
            return []

        self.sample_top_by_frame = {}
        self.memory_samples = {}
        render_by_frame: dict[int, float] = {}
        for record in self.loaded.run_records:
            if str(record.get("logger", "")) != "engine.runtime":
                continue
            message = str(record.get("msg", ""))
            metrics = RE_FRAME_METRICS.search(message)
            if metrics is None:
                continue
            frame = int(metrics.group("frame"))
            top_match = RE_TOP_LIST.search(message)
            if top_match is None:
                continue
            try:
                parsed = ast.literal_eval(top_match.group("top"))
            except SyntaxError, ValueError:
                continue
            if not isinstance(parsed, list):
                continue
            frame_costs: dict[str, float] = {}
            for item in parsed:
                if isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], (int, float)):
                    key = str(item[0])
                    value = float(item[1])
                    frame_costs[key] = value
                    if key == "view_render":
                        render_by_frame[frame] = value
            if frame_costs:
                self.sample_top_by_frame[frame] = frame_costs

        for record in self.loaded.run_records:
            message = str(record.get("msg", ""))
            for match in RE_MEMORY_KV.finditer(message):
                key = str(match.group("key"))
                value = float(match.group("value"))
                self.memory_samples.setdefault(key, []).append(value)

        result: list[tuple[int, float, float, float | None, float | None, str]] = []
        for record in self.loaded.run_records:
            if str(record.get("logger", "")) != "engine.runtime":
                continue
            message = str(record.get("msg", ""))
            metrics = RE_FRAME_METRICS.search(message)
            if metrics is None:
                continue
            frame = int(metrics.group("frame"))
            dt_ms = float(metrics.group("dt"))
            fps = float(metrics.group("fps"))
            render = render_by_frame.get(frame)
            non_render = None if render is None else max(0.0, dt_ms - render)
            result.append((frame, dt_ms, fps, render, non_render, str(record.get("ts", "n/a"))))

        return result

    def _make_profile_samples(self) -> list[ProfileSample]:
        if self.loaded is None:
            return []
        profile_export = self.loaded_profile_export
        if (
            isinstance(profile_export, dict)
            and str(profile_export.get("schema_version", "")) == "diag.profiling.v1"
        ):
            from_export = self._profile_samples_from_export(profile_export)
            if from_export:
                return from_export

        out: list[ProfileSample] = []
        for record in self.loaded.run_records:
            fields = record.get("fields")
            if not isinstance(fields, dict):
                continue
            profile = fields.get("profile")
            if not isinstance(profile, dict):
                continue
            if str(profile.get("schema", "")) != "frame_profile_v1":
                continue

            scheduler = profile.get("scheduler")
            systems = profile.get("systems")
            events = profile.get("events")
            memory = profile.get("memory")

            scheduler_dict = scheduler if isinstance(scheduler, dict) else {}
            systems_dict = systems if isinstance(systems, dict) else {}
            events_dict = events if isinstance(events, dict) else {}
            memory_dict = memory if isinstance(memory, dict) else {}
            top_system = systems_dict.get("top_system")
            top_event = events_dict.get("top_topic")
            top_system_dict = top_system if isinstance(top_system, dict) else {}
            top_event_dict = top_event if isinstance(top_event, dict) else {}
            systems_timings = systems_dict.get("timings_ms")
            systems_timings_dict = systems_timings if isinstance(systems_timings, dict) else {}
            events_topics = events_dict.get("publish_by_topic")
            events_topics_dict = events_topics if isinstance(events_topics, dict) else {}

            sample = ProfileSample(
                frame_index=int(profile.get("frame_index", -1)),
                dt_ms=float(profile.get("dt_ms", 0.0)),
                fps_rolling=float(profile.get("fps_rolling", 0.0)),
                scheduler_queue_size=int(scheduler_dict.get("queue_size", 0)),
                top_system_name=str(top_system_dict.get("name", "")),
                top_system_ms=float(top_system_dict.get("ms", 0.0)),
                top_event_name=str(top_event_dict.get("name", "")),
                top_event_count=int(top_event_dict.get("count", 0)),
                publish_count=int(events_dict.get("publish_count", 0)),
                bottlenecks=tuple(
                    str(v) for v in profile.get("bottlenecks", ()) if isinstance(v, str)
                ),
                systems_timings_ms={
                    str(k): float(v)
                    for k, v in systems_timings_dict.items()
                    if isinstance(v, (int, float))
                },
                events_by_topic={
                    str(k): int(v) for k, v in events_topics_dict.items() if isinstance(v, int)
                },
                memory={
                    str(k): float(v) for k, v in memory_dict.items() if isinstance(v, (int, float))
                },
                ts=str(record.get("ts", "n/a")),
                raw=profile,
            )
            if sample.frame_index >= 0:
                out.append(sample)

        out.sort(key=lambda sample: sample.frame_index)
        return out

    def _profile_samples_from_export(self, payload: dict[str, Any]) -> list[ProfileSample]:
        spans = payload.get("spans")
        if not isinstance(spans, list):
            return []
        by_tick: dict[int, list[dict[str, Any]]] = {}
        for span in spans:
            if not isinstance(span, dict):
                continue
            tick = int(span.get("tick", 0))
            by_tick.setdefault(tick, []).append(span)

        out: list[ProfileSample] = []
        for tick in sorted(by_tick.keys()):
            entries = by_tick[tick]
            systems: dict[str, float] = {}
            frame_ms = 0.0
            for entry in entries:
                category = str(entry.get("category", ""))
                name = str(entry.get("name", ""))
                duration_ms = float(entry.get("duration_ms", 0.0))
                key = f"{category}:{name}" if category else name
                systems[key] = systems.get(key, 0.0) + duration_ms
                if category == "host" and name == "frame":
                    frame_ms = max(frame_ms, duration_ms)
            if frame_ms <= 0.0:
                frame_ms = sum(systems.values())
            fps = (1000.0 / frame_ms) if frame_ms > 0.0 else 0.0
            top_system = max(systems.items(), key=lambda kv: kv[1], default=("", 0.0))
            out.append(
                ProfileSample(
                    frame_index=tick,
                    dt_ms=frame_ms,
                    fps_rolling=fps,
                    scheduler_queue_size=0,
                    top_system_name=top_system[0],
                    top_system_ms=float(top_system[1]),
                    top_event_name="n/a",
                    top_event_count=0,
                    publish_count=0,
                    bottlenecks=((top_system[0],) if top_system[0] else ()),
                    systems_timings_ms=systems,
                    events_by_topic={},
                    memory={},
                    ts="n/a",
                    raw={"schema": "diag.profiling.v1", "tick": tick},
                )
            )
        return out

    def _seek(self, value: str) -> None:
        self._render_frame(int(float(value)))

    def _step(self, delta: int) -> None:
        if self.frame_scale is None:
            return
        current = int(float(self.frame_scale.get()))
        index = max(0, min(len(self.frame_rows) - 1, current + delta))
        self.frame_scale.set(index)
        self._render_frame(index)

    def _play_start(self) -> None:
        if not self.frame_rows or self.frame_scale is None:
            return
        if self.replay_after_id is not None:
            return
        self.replay_mode_var.set("playing")
        self._play_tick()

    def _play_stop(self) -> None:
        if self.replay_after_id is not None:
            self.root.after_cancel(self.replay_after_id)
            self.replay_after_id = None
        self.replay_mode_var.set("stopped")

    def _play_tick(self) -> None:
        if self.frame_scale is None or not self.frame_rows:
            self._play_stop()
            return

        current = int(float(self.frame_scale.get()))
        if current >= len(self.frame_rows) - 1:
            self._play_stop()
            return

        next_idx = current + 1
        self.frame_scale.set(next_idx)
        self._render_frame(next_idx)
        delay_ms = self._next_delay_ms(next_idx)
        self.replay_after_id = self.root.after(delay_ms, self._play_tick)

    def _next_delay_ms(self, index: int) -> int:
        fps = max(1, int(self.replay_fps.get() or "60"))
        fixed = max(1, int(round(1000.0 / fps)))
        if not self.replay_realtime.get():
            return fixed
        if index <= 0 or index >= len(self.frame_rows):
            return fixed
        curr_ts = _parse_ts(self.frame_rows[index].get("ts_utc"))
        prev_ts = _parse_ts(self.frame_rows[index - 1].get("ts_utc"))
        if curr_ts is None or prev_ts is None:
            return fixed
        delta = int(round((curr_ts - prev_ts).total_seconds() * 1000.0))
        return max(5, min(200, delta))

    def _render_frame(self, idx: int) -> None:
        if not self.frame_rows or self.replay_text is None or self.canvas is None:
            return
        index = max(0, min(idx, len(self.frame_rows) - 1))
        frame = self.frame_rows[index]
        self.replay_var.set(f"frame_index={index} frame_seq={frame.get('frame_seq')}")
        self._draw_frame(frame)
        self.replay_text.delete("1.0", END)
        self.replay_text.insert(END, self._format_replay_details(frame))

    def _format_replay_details(self, frame: dict[str, Any]) -> str:
        lines: list[str] = []
        lines.append("Selected Frame")
        lines.append(f"frame_seq={frame.get('frame_seq')}")
        lines.append(f"ts_utc={frame.get('ts_utc')}")
        lines.append(f"reasons={frame.get('reasons')}")
        lines.append(f"anomalies={frame.get('anomalies')}")

        viewport = frame.get("viewport")
        if isinstance(viewport, dict):
            lines.append(
                "viewport="
                f"{viewport.get('width')}x{viewport.get('height')} "
                f"sx={viewport.get('sx')} sy={viewport.get('sy')} "
                f"ox={viewport.get('ox')} oy={viewport.get('oy')}"
            )

        retained = frame.get("retained_ops")
        if isinstance(retained, list):
            counts: dict[str, int] = {}
            for op in retained:
                if not isinstance(op, dict):
                    continue
                action = str(op.get("action", "unknown"))
                counts[action] = counts.get(action, 0) + 1
            if counts:
                counts_text = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
                lines.append(f"retained_ops_summary: {counts_text}")

        lines.append("")
        lines.append("Nearby Run Events")
        nearby = self._nearby_run_events(frame)
        if not nearby:
            lines.append("n/a")
        else:
            for record in nearby:
                lines.append(
                    f"- [{record.get('ts', 'n/a')}] "
                    f"{record.get('logger', 'n/a')} "
                    f"{record.get('level', 'n/a')}: "
                    f"{record.get('msg', '')}"
                )
        replay_nearby = self._nearby_replay_commands(int(frame.get("frame_seq", -1)))
        if replay_nearby:
            lines.append("")
            lines.append("Nearby Replay Commands")
            for command in replay_nearby:
                lines.append(
                    f"- tick={command.get('tick')} type={command.get('type')} "
                    f"payload={command.get('payload')}"
                )

        lines.append("")
        lines.append("Frame Payload")
        lines.append(json.dumps(frame, indent=2, default=str))
        return "\n".join(lines)

    def _nearby_run_events(self, frame: dict[str, Any]) -> list[dict[str, Any]]:
        if self.loaded is None:
            return []
        ts = _parse_ts(frame.get("ts_utc"))
        if ts is None:
            return []

        selected: list[tuple[float, dict[str, Any]]] = []
        for record in self.loaded.run_records:
            rts = _parse_ts(record.get("ts"))
            if rts is None:
                continue
            delta_ms = abs((rts - ts).total_seconds() * 1000.0)
            if delta_ms <= 250.0:
                selected.append((delta_ms, record))
        selected.sort(key=lambda item: (item[0], str(item[1].get("ts", ""))))
        return [item[1] for item in selected[:16]]

    def _nearby_replay_commands(self, frame_seq: int) -> list[dict[str, Any]]:
        payload = self.loaded_replay_export
        if not isinstance(payload, dict):
            return []
        commands = payload.get("commands")
        if not isinstance(commands, list):
            return []
        out: list[dict[str, Any]] = []
        for command in commands:
            if not isinstance(command, dict):
                continue
            tick = int(command.get("tick", -(10**9)))
            if frame_seq >= 0 and abs(tick - frame_seq) <= 3:
                out.append(command)
        return out[:20]

    def _draw_frame(self, frame: dict[str, Any]) -> None:
        assert self.canvas is not None
        canvas = self.canvas
        canvas.delete("all")

        viewport = frame.get("viewport") if isinstance(frame.get("viewport"), dict) else {}
        world_w = float(viewport.get("width", 1920.0))
        world_h = float(viewport.get("height", 1080.0))
        canvas_w = max(1, canvas.winfo_width())
        canvas_h = max(1, canvas.winfo_height())
        scale_x = canvas_w / max(1.0, world_w)
        scale_y = canvas_h / max(1.0, world_h)

        primitives = frame.get("primitives")
        if not isinstance(primitives, list):
            return

        for primitive in primitives:
            if not isinstance(primitive, dict):
                continue
            prim_type = str(primitive.get("type", ""))
            transformed = primitive.get("transformed")
            if not isinstance(transformed, dict):
                continue

            x = float(transformed.get("x", 0.0))
            y = float(transformed.get("y", 0.0))
            w = float(transformed.get("w", 0.0))
            h = float(transformed.get("h", 0.0))

            if prim_type in {"rect", "window_rect"}:
                canvas.create_rectangle(
                    x * scale_x,
                    y * scale_y,
                    (x + w) * scale_x,
                    (y + h) * scale_y,
                    fill="#2e4d82",
                    outline="#8eb5f0",
                )
            elif prim_type == "text":
                canvas.create_rectangle(
                    x * scale_x,
                    y * scale_y,
                    (x + w) * scale_x,
                    (y + h) * scale_y,
                    fill="#4f7b4f",
                    outline="#a6d9a6",
                )

    def _filtered_events(self) -> list[UiEvent]:
        cutoff: datetime | None = None
        if self.events_range.get() != "all" and self.events:
            end = max((event.ts for event in self.events if event.ts is not None), default=None)
            if end is not None:
                seconds = {"last_5s": 5, "last_30s": 30, "last_120s": 120}.get(
                    self.events_range.get(),
                    0,
                )
                cutoff = end - timedelta(seconds=seconds)

        severity = self.events_severity.get()
        family = self.events_family.get()
        query = self.events_search.get().strip().lower()

        result: list[UiEvent] = []
        for event in self.events:
            if cutoff is not None and (event.ts is None or event.ts < cutoff):
                continue
            if severity == "warnings+" and event.severity not in {"warning", "error"}:
                continue
            if severity == "errors+" and event.severity != "error":
                continue
            if family != "all" and event.family != family:
                continue
            if query and query not in f"{event.source} {event.msg}".lower():
                continue
            result.append(event)
        return result

    def _refresh_events(self) -> None:
        if self.events_tree is None:
            return
        filtered = self._filtered_events()
        self.events_count_var.set(f"{len(filtered)} / {len(self.events)}")
        self.events_tree.delete(*self.events_tree.get_children())
        for idx, event in enumerate(filtered[:6000]):
            self.events_tree.insert(
                "",
                END,
                iid=f"e{idx}",
                values=(
                    event.ts.isoformat() if event.ts else "n/a",
                    event.source,
                    event.family,
                    event.severity,
                    event.msg[:240],
                ),
            )

    def _event_select(self, _event: object) -> None:
        if self.events_tree is None or self.events_detail is None:
            return
        selected = self.events_tree.selection()
        if not selected:
            return
        idx = int(selected[0][1:])
        filtered = self._filtered_events()
        if idx >= len(filtered):
            return
        self.events_detail.delete("1.0", END)
        pretty = json.dumps(filtered[idx].raw, indent=2, default=str, sort_keys=True)
        self.events_detail.insert(END, pretty)

    def _refresh_runs(self) -> None:
        if self.loaded is None or self.runs_tree is None or self.runs_text is None:
            return
        summary = self.loaded.summary
        self.runs_text.delete("1.0", END)
        self.runs_text.insert(
            END,
            f"frames={summary.frame_count}\n"
            f"fps_mean={getattr(summary, 'fps_mean', None)}\n"
            f"frame_time_p95_ms={getattr(summary, 'frame_time_p95_ms', None)}\n"
            f"frame_time_max_ms={getattr(summary, 'frame_time_max_ms', None)}\n"
            f"warnings={getattr(summary, 'warning_count', 0)}\n"
            f"errors={getattr(summary, 'error_count', 0)}",
        )
        self._refresh_crash_focus()

        query = self.runs_search.get().strip().lower()
        self.runs_tree.delete(*self.runs_tree.get_children())

        rows: list[dict[str, Any]] = []
        for record in self.loaded.run_records:
            level = str(record.get("level", "")).upper()
            msg = str(record.get("msg", ""))
            is_warning_or_error = level in {"WARNING", "WARN", "ERROR", "CRITICAL"}
            if not is_warning_or_error and "exception" not in msg.lower():
                continue
            if query and query not in f"{record.get('logger', '')} {msg}".lower():
                continue
            rows.append(record)

        self.runs_count_var.set(str(len(rows)))
        for idx, record in enumerate(rows[:3000]):
            self.runs_tree.insert(
                "",
                END,
                iid=f"r{idx}",
                values=(
                    str(record.get("ts", "n/a")),
                    str(record.get("logger", "")),
                    str(record.get("level", "")),
                    str(record.get("msg", ""))[:260],
                ),
            )

    def _refresh_crash_focus(self) -> None:
        if self.loaded is None or self.crash_text is None:
            return
        if isinstance(self.loaded_crash_bundle, dict):
            bundle = self.loaded_crash_bundle
            self.crash_text.delete("1.0", END)
            exception = bundle.get("exception")
            runtime = bundle.get("runtime")
            recent_events = bundle.get("recent_events")
            self.crash_text.insert(
                END,
                f"bundle_schema={bundle.get('schema_version', 'n/a')}\n"
                f"captured_at={bundle.get('captured_at_utc', 'n/a')}\n"
                f"tick={bundle.get('tick', 'n/a')}\n",
            )
            if isinstance(exception, dict):
                self.crash_text.insert(
                    END,
                    f"exception_type={exception.get('type', 'n/a')}\n"
                    f"exception_message={exception.get('message', 'n/a')}\n",
                )
                trace = exception.get("traceback")
                if isinstance(trace, list):
                    self.crash_text.insert(END, "\ntraceback:\n")
                    for line in trace[:20]:
                        self.crash_text.insert(END, str(line))
            if isinstance(runtime, dict):
                self.crash_text.insert(END, f"\nruntime={json.dumps(runtime, default=str)}\n")
            if isinstance(recent_events, list):
                self.crash_text.insert(END, f"\nrecent_events={len(recent_events)}\n")
            return
        crash_records: list[dict[str, Any]] = []
        for record in self.loaded.run_records:
            level = str(record.get("level", "")).upper()
            msg = str(record.get("msg", ""))
            if level in {"ERROR", "CRITICAL"} or "exception" in msg.lower():
                crash_records.append(record)

        self.crash_text.delete("1.0", END)
        if not crash_records:
            self.crash_text.insert(END, "No crash/error markers found in this session.")
            return

        head = crash_records[0]
        tail = crash_records[-1]
        exception_type = self._extract_exception_type(tail)
        stack_frames = self._extract_stack_frames(crash_records[-30:])
        self.crash_text.insert(
            END,
            "first_error_ts="
            f"{head.get('ts', 'n/a')} logger={head.get('logger', 'n/a')}\n"
            "last_error_ts="
            f"{tail.get('ts', 'n/a')} logger={tail.get('logger', 'n/a')}\n"
            f"exception_type={exception_type}\n\n",
        )
        self.crash_text.insert(END, "top_stack_frames:\n")
        if stack_frames:
            for frame_line in stack_frames[:10]:
                self.crash_text.insert(END, f"- {frame_line}\n")
        else:
            self.crash_text.insert(END, "n/a\n")
        self.crash_text.insert(END, "\n")
        self.crash_text.insert(END, "recent_error_messages:\n")
        for record in crash_records[-12:]:
            self.crash_text.insert(
                END,
                f"- [{record.get('ts', 'n/a')}] "
                f"{record.get('logger', 'n/a')}: {record.get('msg', '')}\n",
            )

    def _extract_exception_type(self, record: dict[str, Any]) -> str:
        message = str(record.get("msg", ""))
        lines = [line.strip() for line in message.splitlines() if line.strip()]
        if not lines:
            return "n/a"
        last = lines[-1]
        if ":" in last:
            return last.split(":", 1)[0].strip()
        return last

    def _extract_stack_frames(self, records: list[dict[str, Any]]) -> list[str]:
        frames: list[str] = []
        for record in records:
            message = str(record.get("msg", ""))
            for line in message.splitlines():
                stripped = line.strip()
                if stripped.startswith('File "') and stripped not in frames:
                    frames.append(stripped)
        return frames

    def _refresh_perf(self) -> None:
        if self.loaded is None or self.perf_text is None or self.hitch_tree is None:
            return

        summary = self.loaded.summary
        if self.profile_samples:
            frame_times = [sample.dt_ms for sample in self.profile_samples]
            fps_values = [sample.fps_rolling for sample in self.profile_samples]
        else:
            frame_times = [sample[1] for sample in self.samples]
            fps_values = [sample[2] for sample in self.samples]
        system_costs = self._aggregate_system_costs()
        event_counts = self._aggregate_event_counts()
        bottleneck_counts = self._aggregate_bottleneck_counts()
        memory_text = self._memory_summary_text()
        self.perf_text.delete("1.0", END)
        self.perf_text.insert(
            END,
            f"frame_count={getattr(summary, 'frame_count', 0)}\n"
            f"fps_mean={getattr(summary, 'fps_mean', None)}\n"
            f"frame_time_p50_ms={getattr(summary, 'frame_time_p50_ms', None)}\n"
            f"frame_time_p95_ms={getattr(summary, 'frame_time_p95_ms', None)}\n"
            f"frame_time_p99_ms={getattr(summary, 'frame_time_p99_ms', None)}\n"
            f"frame_time_max_ms={getattr(summary, 'frame_time_max_ms', None)}\n"
            f"event_to_frame_p95_ms={getattr(summary, 'event_to_frame_p95_ms', None)}\n"
            f"apply_to_frame_p95_ms={getattr(summary, 'apply_to_frame_p95_ms', None)}\n\n"
            f"frame_time_histogram={self._make_histogram(frame_times)}\n"
            f"fps_histogram={self._make_histogram(fps_values)}\n\n"
            f"memory_summary={memory_text}\n"
            f"top_event_topics={self._top_kv_text(event_counts, 6)}\n"
            f"top_bottlenecks={self._top_kv_text(bottleneck_counts, 6)}",
        )

        threshold = float(self.hitch_thresh.get())
        self.hitches = []
        self.hitch_tree.delete(*self.hitch_tree.get_children())

        if self.profile_samples:
            for sample in self.profile_samples:
                if sample.dt_ms < threshold:
                    continue
                bottleneck = sample.bottlenecks[0] if sample.bottlenecks else "n/a"
                self.hitches.append(
                    {
                        "frame": sample.frame_index,
                        "dt_ms": sample.dt_ms,
                        "bottleneck": bottleneck,
                        "top_system": sample.top_system_name or "n/a",
                        "top_event": sample.top_event_name or "n/a",
                        "queue": sample.scheduler_queue_size,
                        "ts": sample.ts,
                    }
                )
        else:
            for hitch in getattr(summary, "hitches_25ms", []):
                if float(hitch.frame_time_ms) >= threshold:
                    ts = hitch.ts_utc.isoformat() if hitch.ts_utc else "n/a"
                    self.hitches.append(
                        {
                            "frame": int(hitch.frame_seq),
                            "dt_ms": float(hitch.frame_time_ms),
                            "bottleneck": "frame_hitch",
                            "top_system": "n/a",
                            "top_event": "n/a",
                            "queue": 0,
                            "ts": ts,
                        }
                    )

        for idx, hitch in enumerate(self.hitches[:2500]):
            self.hitch_tree.insert(
                "",
                END,
                iid=f"h{idx}",
                values=(
                    hitch["frame"],
                    f"{hitch['dt_ms']:.2f}",
                    hitch["bottleneck"],
                    hitch["top_system"],
                    hitch["top_event"],
                    hitch["queue"],
                    hitch["ts"],
                ),
            )

        if self.sample_tree is None:
            return
        self.sample_tree.delete(*self.sample_tree.get_children())
        if self.profile_samples:
            heavy = sorted(self.profile_samples, key=lambda item: item.dt_ms, reverse=True)
        else:
            heavy = sorted(self.samples, key=lambda item: item[1], reverse=True)
        self.perf_count_var.set(
            f"hitches={len(self.hitches)} samples={len(self.profile_samples) or len(self.samples)}"
        )
        if self.profile_samples:
            for idx, sample in enumerate(heavy[:2500]):
                render = sample.systems_timings_ms.get("view_render")
                non_render = sample.dt_ms - render if render is not None else None
                self.sample_tree.insert(
                    "",
                    END,
                    iid=f"s{idx}",
                    values=(
                        sample.frame_index,
                        f"{sample.dt_ms:.2f}",
                        "n/a" if render is None else f"{render:.2f}",
                        "n/a" if non_render is None else f"{non_render:.2f}",
                        f"{sample.fps_rolling:.2f}",
                        sample.top_system_name or "n/a",
                        sample.top_event_name or "n/a",
                        sample.ts,
                    ),
                )
        else:
            for idx, (frame, dt_ms, fps, render, non_render, ts) in enumerate(heavy[:2500]):
                self.sample_tree.insert(
                    "",
                    END,
                    iid=f"s{idx}",
                    values=(
                        frame,
                        f"{dt_ms:.2f}",
                        "n/a" if render is None else f"{render:.2f}",
                        "n/a" if non_render is None else f"{non_render:.2f}",
                        f"{fps:.2f}",
                        "n/a",
                        "n/a",
                        ts,
                    ),
                )
        self._draw_perf_charts(frame_times, fps_values)
        self._draw_system_chart(system_costs)
        self._draw_event_chart(event_counts, bottleneck_counts)
        self._draw_memory_chart()
        self._refresh_system_tree(system_costs)

    def _aggregate_system_costs(self) -> dict[str, tuple[float, float, float]]:
        if self.profile_samples:
            totals: dict[str, float] = {}
            maxes: dict[str, float] = {}
            counts: dict[str, int] = {}
            grand_total = 0.0
            for sample in self.profile_samples:
                for key, value in sample.systems_timings_ms.items():
                    totals[key] = totals.get(key, 0.0) + value
                    maxes[key] = max(maxes.get(key, 0.0), value)
                    counts[key] = counts.get(key, 0) + 1
                    grand_total += value
            result: dict[str, tuple[float, float, float]] = {}
            for key in totals:
                mean = totals[key] / max(1, counts.get(key, 1))
                share = (totals[key] / grand_total * 100.0) if grand_total > 0.0 else 0.0
                result[key] = (mean, maxes.get(key, 0.0), share)
            return result

        totals: dict[str, float] = {}
        maxes: dict[str, float] = {}
        counts: dict[str, int] = {}
        grand_total = 0.0
        for costs in self.sample_top_by_frame.values():
            for key, value in costs.items():
                totals[key] = totals.get(key, 0.0) + value
                maxes[key] = max(maxes.get(key, 0.0), value)
                counts[key] = counts.get(key, 0) + 1
                grand_total += value
        result: dict[str, tuple[float, float, float]] = {}
        for key in totals:
            mean = totals[key] / max(1, counts.get(key, 1))
            share = (totals[key] / grand_total * 100.0) if grand_total > 0.0 else 0.0
            result[key] = (mean, maxes.get(key, 0.0), share)
        return result

    def _refresh_system_tree(self, system_costs: dict[str, tuple[float, float, float]]) -> None:
        if self.system_tree is None:
            return
        self.system_tree.delete(*self.system_tree.get_children())
        ranked = sorted(system_costs.items(), key=lambda item: item[1][0], reverse=True)
        for idx, (name, (mean_ms, max_ms, share)) in enumerate(ranked[:200]):
            self.system_tree.insert(
                "",
                END,
                iid=f"sys{idx}",
                values=(name, f"{mean_ms:.3f}", f"{max_ms:.3f}", f"{share:.2f}"),
            )

    def _aggregate_event_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for sample in self.profile_samples:
            for topic, value in sample.events_by_topic.items():
                counts[topic] = counts.get(topic, 0) + int(value)
        return counts

    def _aggregate_bottleneck_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for sample in self.profile_samples:
            for bottleneck in sample.bottlenecks:
                counts[bottleneck] = counts.get(bottleneck, 0) + 1
        return counts

    @staticmethod
    def _top_kv_text(values: dict[str, int], limit: int) -> str:
        if not values:
            return "n/a"
        top = sorted(values.items(), key=lambda item: item[1], reverse=True)[:limit]
        return ", ".join(f"{k}:{v}" for k, v in top)

    def _memory_summary_text(self) -> str:
        if self.profile_samples:
            key_values: dict[str, list[float]] = {}
            for sample in self.profile_samples:
                for key, value in sample.memory.items():
                    key_values.setdefault(key, []).append(value)
            if key_values:
                parts = []
                for key, values in sorted(key_values.items()):
                    parts.append(
                        f"{key}:mean={sum(values) / len(values):.1f},max={max(values):.1f}"
                    )
                return "; ".join(parts)
            return "n/a (profiling enabled but memory fields missing)"

        if not self.memory_samples:
            return "n/a (no memory metrics in logs)"
        parts: list[str] = []
        for key, values in sorted(self.memory_samples.items()):
            if not values:
                continue
            parts.append(f"{key}:mean={sum(values) / len(values):.1f},max={max(values):.1f}")
        return "; ".join(parts) if parts else "n/a (no memory metrics in logs)"

    def _draw_perf_charts(self, frame_times: list[float], fps_values: list[float]) -> None:
        if self.perf_canvas is None:
            return
        canvas = self.perf_canvas
        canvas.delete("all")
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        mid = height // 2
        canvas.create_line(0, mid, width, mid, fill="#2b3440")
        self._draw_series(canvas, frame_times[-240:], 0, mid - 2, "#ffad5a", "frame ms")
        self._draw_series(canvas, fps_values[-240:], mid + 2, height - 2, "#76e39c", "fps")

    def _draw_system_chart(self, system_costs: dict[str, tuple[float, float, float]]) -> None:
        if self.perf_system_canvas is None:
            return
        canvas = self.perf_system_canvas
        canvas.delete("all")
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        ranked = sorted(system_costs.items(), key=lambda item: item[1][0], reverse=True)[:10]
        if not ranked:
            canvas.create_text(12, 12, text="No system profiling data", fill="#d2d8e2", anchor="nw")
            return
        max_mean = max(item[1][0] for item in ranked) or 1.0
        row_h = max(14, (height - 20) // max(1, len(ranked)))
        for i, (name, (mean_ms, _max_ms, _share)) in enumerate(ranked):
            y0 = 10 + i * row_h
            y1 = y0 + row_h - 4
            bar_w = int((mean_ms / max_mean) * max(1, width - 240))
            canvas.create_rectangle(180, y0, 180 + bar_w, y1, fill="#4f8bd6", outline="")
            canvas.create_text(8, y0 + 1, text=name, fill="#d2d8e2", anchor="nw")
            canvas.create_text(
                width - 8,
                y0 + 1,
                text=f"{mean_ms:.3f} ms",
                fill="#9ec6ff",
                anchor="ne",
            )

    def _draw_event_chart(
        self,
        event_counts: dict[str, int],
        bottleneck_counts: dict[str, int],
    ) -> None:
        if self.perf_event_canvas is None:
            return
        canvas = self.perf_event_canvas
        canvas.delete("all")
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        mid = height // 2
        canvas.create_line(0, mid, width, mid, fill="#2b3440")
        self._draw_rank_bars(
            canvas=canvas,
            values=event_counts,
            y0=0,
            y1=mid - 2,
            color="#7fd1b9",
            title="Top event topics",
        )
        self._draw_rank_bars(
            canvas=canvas,
            values=bottleneck_counts,
            y0=mid + 2,
            y1=height - 2,
            color="#f2a65a",
            title="Top bottlenecks",
        )

    def _draw_memory_chart(self) -> None:
        if self.perf_memory_canvas is None:
            return
        canvas = self.perf_memory_canvas
        canvas.delete("all")
        height = max(1, canvas.winfo_height())
        if not self.profile_samples:
            canvas.create_text(
                12,
                12,
                text="No profiling memory series",
                fill="#d2d8e2",
                anchor="nw",
            )
            return
        series: dict[str, list[float]] = {}
        for sample in self.profile_samples[-300:]:
            for key in ("process_rss_mb", "python_current_mb", "python_peak_mb"):
                if key in sample.memory:
                    series.setdefault(key, []).append(sample.memory[key])
        if not series:
            canvas.create_text(
                12,
                12,
                text="No memory metrics found in profile payloads",
                fill="#d2d8e2",
                anchor="nw",
            )
            return
        colors = {
            "process_rss_mb": "#f07b7b",
            "python_current_mb": "#7bc8f0",
            "python_peak_mb": "#d6b97b",
        }
        top_pad = 18
        for key, values in series.items():
            self._draw_series(
                canvas,
                values,
                top_pad,
                height - 4,
                colors.get(key, "#d2d8e2"),
                key,
            )
            top_pad += 14
            if top_pad > height // 3:
                break

    def _draw_rank_bars(
        self,
        *,
        canvas: Canvas,
        values: dict[str, int],
        y0: int,
        y1: int,
        color: str,
        title: str,
    ) -> None:
        canvas.create_text(8, y0 + 6, text=title, fill=color, anchor="nw")
        if not values:
            canvas.create_text(8, y0 + 24, text="n/a", fill="#d2d8e2", anchor="nw")
            return
        ranked = sorted(values.items(), key=lambda item: item[1], reverse=True)[:5]
        max_value = max(v for _, v in ranked) or 1
        area_top = y0 + 20
        area_h = max(1, y1 - area_top)
        row_h = max(10, area_h // max(1, len(ranked)))
        width = max(1, canvas.winfo_width())
        for i, (name, value) in enumerate(ranked):
            ry0 = area_top + i * row_h
            ry1 = min(y1 - 1, ry0 + row_h - 2)
            bar_w = int((value / max_value) * max(1, width - 220))
            canvas.create_rectangle(170, ry0, 170 + bar_w, ry1, fill=color, outline="")
            canvas.create_text(8, ry0, text=name, fill="#d2d8e2", anchor="nw")
            canvas.create_text(width - 8, ry0, text=str(value), fill="#d2d8e2", anchor="ne")

    def _draw_series(
        self,
        canvas: Canvas,
        values: list[float],
        y0: int,
        y1: int,
        color: str,
        label: str,
    ) -> None:
        if not values:
            return
        width = max(1, canvas.winfo_width())
        min_v = min(values)
        max_v = max(values)
        rng = max(max_v - min_v, 1e-6)
        points: list[float] = []
        for idx, value in enumerate(values):
            x = (idx / max(1, len(values) - 1)) * (width - 1)
            norm = (value - min_v) / rng
            y = y1 - norm * max(1, (y1 - y0))
            points.extend([x, y])
        if len(points) >= 4:
            canvas.create_line(*points, fill=color, width=1.5)
        canvas.create_text(
            8,
            y0 + 8,
            text=f"{label} [{min_v:.1f}-{max_v:.1f}]",
            fill=color,
            anchor="w",
        )

    def _make_histogram(self, values: list[float]) -> str:
        if not values:
            return "n/a"
        bins = 8
        low = min(values)
        high = max(values)
        if high <= low:
            return f"[{low:.2f}] {'#' * min(40, len(values))}"

        step = (high - low) / bins
        counts = [0] * bins
        for value in values:
            idx = int((value - low) / step)
            if idx >= bins:
                idx = bins - 1
            counts[idx] += 1

        peak = max(counts) or 1
        segments: list[str] = []
        for i, count in enumerate(counts):
            start = low + i * step
            end = start + step
            bar_len = int(20 * (count / peak))
            segments.append(f"[{start:.1f}-{end:.1f}] {'#' * bar_len}")
        return " | ".join(segments)

    def _hitch_select(self, _event: object) -> None:
        if self.hitch_tree is None:
            return
        selected = self.hitch_tree.selection()
        if not selected:
            return
        idx = int(selected[0][1:])
        if idx >= len(self.hitches):
            return
        self._jump_seq(int(self.hitches[idx]["frame"]))

    def _jump_seq(self, seq: int) -> None:
        if self.frame_scale is None:
            return
        self._play_stop()
        idx = self.frame_idx_by_seq.get(seq)
        if idx is None:
            return
        self.frame_scale.set(idx)
        self._render_frame(idx)

    def _jump_hitch(self) -> None:
        if self.frame_scale is None:
            return
        current = int(float(self.frame_scale.get()))
        current_seq = int(self.frame_rows[current].get("frame_seq", -1))
        for hitch in self.hitches:
            frame_seq = int(hitch["frame"])
            if frame_seq > current_seq:
                self._jump_seq(frame_seq)
                return

    def _jump_resize(self) -> None:
        if self.frame_scale is None:
            return
        current = int(float(self.frame_scale.get()))
        for idx in range(current + 1, len(self.frame_rows)):
            reasons = self.frame_rows[idx].get("reasons")
            if isinstance(reasons, list) and any(str(reason) == "resize" for reason in reasons):
                self.frame_scale.set(idx)
                self._render_frame(idx)
                return

    def _jump_anomaly(self) -> None:
        if self.frame_scale is None:
            return
        current = int(float(self.frame_scale.get()))
        for idx in range(current + 1, len(self.frame_rows)):
            anomalies = self.frame_rows[idx].get("anomalies")
            if isinstance(anomalies, list) and anomalies:
                self.frame_scale.set(idx)
                self._render_frame(idx)
                return

    def _on_close(self) -> None:
        self._play_stop()
        self.root.destroy()


def _launch_gui(logs_dir: Path) -> int:
    root = Tk()
    App(root, logs_dir)
    root.mainloop()
    return 0


def _print_loaded_summary(loaded: DebugLoadedSession) -> None:
    summary = loaded.summary
    run_name = loaded.bundle.run_log.name if loaded.bundle.run_log else "n/a"
    ui_name = loaded.bundle.ui_log.name if loaded.bundle.ui_log else "n/a"
    print(f"run_log: {run_name}")
    print(f"ui_log: {ui_name}")
    print(f"frames: {getattr(summary, 'frame_count', 0)}")
    print(f"fps_mean: {getattr(summary, 'fps_mean', None)}")
    print(f"frame_time_p95_ms: {getattr(summary, 'frame_time_p95_ms', None)}")
    print(f"frame_time_p99_ms: {getattr(summary, 'frame_time_p99_ms', None)}")
    print(f"frame_time_max_ms: {getattr(summary, 'frame_time_max_ms', None)}")
    print(f"event_to_frame_p95_ms: {getattr(summary, 'event_to_frame_p95_ms', None)}")
    print(f"apply_to_frame_p95_ms: {getattr(summary, 'apply_to_frame_p95_ms', None)}")
    print(f"warnings: {getattr(summary, 'warning_count', 0)}")
    print(f"errors: {getattr(summary, 'error_count', 0)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unified engine observability tool.")
    parser.add_argument("--logs-dir", type=Path, default=_default_logs_dir())
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--session-index", type=int, default=0)
    parser.add_argument("--run-log", type=Path, default=None)
    parser.add_argument("--ui-log", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.list:
        bundles = discover_debug_sessions(args.logs_dir, recursive=True)
        if not bundles:
            print("No sessions discovered.")
            return 1
        for idx, bundle in enumerate(bundles):
            run_name = bundle.run_log.name if bundle.run_log else "n/a"
            ui_name = bundle.ui_log.name if bundle.ui_log else "n/a"
            print(f"[{idx}] run={run_name} | ui={ui_name}")
        return 0

    if args.run_log is not None or args.ui_log is not None:
        bundle = DebugSessionBundle(
            run_log=args.run_log,
            ui_log=args.ui_log,
            run_stamp=None,
            ui_stamp=None,
        )
        loaded = load_debug_session(bundle)
        _print_loaded_summary(loaded)
        return 0

    return _launch_gui(args.logs_dir)


if __name__ == "__main__":
    raise SystemExit(main())
