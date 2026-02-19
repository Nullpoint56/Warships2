from __future__ import annotations

from pathlib import Path
from tkinter import (
    BOTH,
    END,
    HORIZONTAL,
    LEFT,
    RIGHT,
    VERTICAL,
    Canvas,
    StringVar,
    Tk,
    X,
    Y,
    simpledialog,
    ttk,
)
from tkinter.scrolledtext import ScrolledText

from tools.engine_obs_core.datasource.file_source import FileObsSource
from tools.engine_session_inspector.presets import EventFilterPreset, load_presets, save_presets
from tools.engine_session_inspector.state import InspectorState
from tools.engine_session_inspector.views.crash import build_crash_focus_text
from tools.engine_session_inspector.views.events import (
    EventFilter,
    apply_event_filter,
    event_to_row,
    format_event_payload,
)
from tools.engine_session_inspector.views.profiling import build_profiling_view_model
from tools.engine_session_inspector.views.replay import (
    build_replay_timeline_model,
    clamp_index,
    frame_interval_ms,
    next_playback_index,
    step_index,
)
from tools.engine_session_inspector.views.summary import build_summary_lines


class SessionInspectorApp:
    def __init__(self, root: Tk, *, logs_root: Path) -> None:
        self.root = root
        self.root.title("Engine Session Inspector")
        self.root.geometry("1500x980")

        self.source = FileObsSource(logs_root, recursive=True)
        self.state = InspectorState()

        self.status_var = StringVar(value="No session loaded.")
        self.session_var = StringVar(value="")
        self.category_var = StringVar(value="all")
        self.level_var = StringVar(value="all")
        self.query_var = StringVar(value="")
        self.replay_fps_var = StringVar(value="60")
        self.replay_mode_var = StringVar(value="stopped")
        self.replay_pos_var = StringVar(value="tick=n/a")
        self.preset_var = StringVar(value="")

        self.summary_text: ScrolledText | None = None
        self.events_tree: ttk.Treeview | None = None
        self.payload_text: ScrolledText | None = None
        self.crash_text: ScrolledText | None = None
        self.profiling_text: ScrolledText | None = None
        self.profiling_total_tree: ttk.Treeview | None = None
        self.profiling_p95_tree: ttk.Treeview | None = None
        self.profiling_hitch_tree: ttk.Treeview | None = None
        self.profiling_canvas: Canvas | None = None
        self.replay_text: ScrolledText | None = None
        self.replay_commands_tree: ttk.Treeview | None = None
        self.replay_checkpoints_tree: ttk.Treeview | None = None
        self.replay_canvas: Canvas | None = None
        self.replay_preview_canvas: Canvas | None = None
        self.replay_scale: ttk.Scale | None = None
        self.category_combo: ttk.Combobox | None = None
        self.preset_combo: ttk.Combobox | None = None
        self.events_query_entry: ttk.Entry | None = None
        self._presets: list[EventFilterPreset] = load_presets()
        self._filtered_events = []
        self._profiling_total_iid_by_key: dict[str, str] = {}
        self._profiling_selected_hitch_tick: int | None = None
        self._replay_checkpoint_mismatch_ticks: set[int] = set()
        self._replay_render_packets: dict[int, dict[str, object]] = {}
        self._replay_index = 0
        self._replay_after_id: str | None = None

        self._build()
        self._bind_shortcuts()
        self._refresh_sessions()

    def _build(self) -> None:
        top = ttk.Frame(self.root)
        top.pack(fill=X, padx=8, pady=8)

        ttk.Label(top, text="Session").pack(side=LEFT)
        self.session_combo = ttk.Combobox(
            top, width=84, textvariable=self.session_var, state="readonly"
        )
        self.session_combo.pack(side=LEFT, padx=6)
        self.session_combo.bind("<<ComboboxSelected>>", lambda _e: self._load_selected_session())
        ttk.Button(top, text="Refresh", command=self._refresh_sessions).pack(side=LEFT, padx=6)

        ttk.Label(self.root, textvariable=self.status_var).pack(anchor="w", padx=8)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=BOTH, expand=True, padx=8, pady=8)

        summary_tab = ttk.Frame(notebook)
        events_tab = ttk.Frame(notebook)
        replay_tab = ttk.Frame(notebook)
        crash_tab = ttk.Frame(notebook)
        profiling_tab = ttk.Frame(notebook)
        notebook.add(summary_tab, text="Summary")
        notebook.add(events_tab, text="Events")
        notebook.add(replay_tab, text="Replay")
        notebook.add(crash_tab, text="Crash")
        notebook.add(profiling_tab, text="Profiling")

        self._build_summary(summary_tab)
        self._build_events(events_tab)
        self._build_replay(replay_tab)
        self._build_crash(crash_tab)
        self._build_profiling(profiling_tab)

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-f>", self._on_shortcut_focus_search)
        self.root.bind("<Control-r>", self._on_shortcut_apply_filters)
        self.root.bind("<F5>", self._on_shortcut_refresh_sessions)
        self.root.bind("<space>", self._on_shortcut_toggle_replay)

    def _on_shortcut_focus_search(self, _event: object) -> str:
        if self.events_query_entry is not None:
            self.events_query_entry.focus_set()
            self.events_query_entry.selection_range(0, END)
        return "break"

    def _on_shortcut_apply_filters(self, _event: object) -> str:
        self._refresh_events_view()
        return "break"

    def _on_shortcut_refresh_sessions(self, _event: object) -> str:
        self._refresh_sessions()
        return "break"

    def _on_shortcut_toggle_replay(self, _event: object) -> str:
        if self.replay_mode_var.get() == "playing":
            self._replay_pause()
        else:
            self._replay_play()
        return "break"

    def _refresh_preset_combo(self) -> None:
        if self.preset_combo is None:
            return
        names = [preset.name for preset in self._presets]
        self.preset_combo["values"] = tuple(names)
        if names and not self.preset_var.get():
            self.preset_var.set(names[0])

    def _apply_selected_preset(self) -> None:
        name = self.preset_var.get().strip()
        if not name:
            return
        selected = next((preset for preset in self._presets if preset.name == name), None)
        if selected is None:
            return
        self.category_var.set(selected.category)
        self.level_var.set(selected.level)
        self.query_var.set(selected.query)
        self._refresh_events_view()

    def _save_current_preset(self) -> None:
        name = simpledialog.askstring("Save Preset", "Preset name:", parent=self.root)
        if name is None:
            return
        clean_name = name.strip()
        if not clean_name:
            return
        preset = EventFilterPreset(
            name=clean_name,
            category=self.category_var.get() or "all",
            level=self.level_var.get() or "all",
            query=self.query_var.get(),
        )
        self._presets = [item for item in self._presets if item.name != clean_name]
        self._presets.append(preset)
        self._presets.sort(key=lambda item: item.name.lower())
        save_presets(self._presets)
        self._refresh_preset_combo()
        self.preset_var.set(clean_name)
        self.status_var.set(f"Preset saved: {clean_name}")

    def _build_summary(self, tab: ttk.Frame) -> None:
        self.summary_text = ScrolledText(tab, wrap="none")
        self.summary_text.pack(fill=BOTH, expand=True)

    def _build_events(self, tab: ttk.Frame) -> None:
        controls = ttk.LabelFrame(tab, text="Filters")
        controls.pack(fill=X, pady=6)

        ttk.Label(controls, text="Preset").pack(side=LEFT, padx=4)
        preset_combo = ttk.Combobox(
            controls, width=22, textvariable=self.preset_var, state="readonly"
        )
        preset_combo.pack(side=LEFT)
        preset_combo.bind("<<ComboboxSelected>>", lambda _e: self._apply_selected_preset())
        self.preset_combo = preset_combo
        ttk.Button(controls, text="Save Preset", command=self._save_current_preset).pack(
            side=LEFT, padx=4
        )

        ttk.Label(controls, text="Category").pack(side=LEFT, padx=4)
        category_combo = ttk.Combobox(
            controls,
            width=14,
            textvariable=self.category_var,
            state="readonly",
            values=("all",),
        )
        category_combo.pack(side=LEFT)
        self.category_combo = category_combo

        ttk.Label(controls, text="Level").pack(side=LEFT, padx=4)
        level_combo = ttk.Combobox(
            controls,
            width=10,
            textvariable=self.level_var,
            state="readonly",
            values=("all", "info", "warning", "error", "critical"),
        )
        level_combo.pack(side=LEFT)

        ttk.Label(controls, text="Search").pack(side=LEFT, padx=4)
        query_entry = ttk.Entry(controls, width=36, textvariable=self.query_var)
        query_entry.pack(side=LEFT)
        self.events_query_entry = query_entry
        ttk.Button(controls, text="Apply", command=self._refresh_events_view).pack(
            side=LEFT, padx=6
        )

        category_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_events_view())
        level_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_events_view())
        query_entry.bind("<Return>", lambda _e: self._refresh_events_view())

        split = ttk.Panedwindow(tab, orient="horizontal")
        split.pack(fill=BOTH, expand=True)

        events_frame = ttk.LabelFrame(split, text="Events")
        payload_frame = ttk.LabelFrame(split, text="Payload")
        split.add(events_frame, weight=3)
        split.add(payload_frame, weight=2)

        columns = ("ts", "tick", "category", "name", "value")
        tree = ttk.Treeview(events_frame, columns=columns, show="headings")
        for col, width in (
            ("ts", 190),
            ("tick", 70),
            ("category", 120),
            ("name", 220),
            ("value", 760),
        ):
            tree.heading(col, text=col.upper())
            tree.column(col, width=width, anchor="w")

        bar = ttk.Scrollbar(events_frame, orient=VERTICAL, command=tree.yview)
        xbar = ttk.Scrollbar(events_frame, orient=HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=bar.set)
        tree.configure(xscrollcommand=xbar.set)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        bar.pack(side=RIGHT, fill=Y)
        xbar.pack(side="bottom", fill=X)
        tree.bind("<<TreeviewSelect>>", self._on_event_select)
        self.events_tree = tree

        self.payload_text = ScrolledText(payload_frame, wrap="none")
        payload_xbar = ttk.Scrollbar(
            payload_frame, orient=HORIZONTAL, command=self.payload_text.xview
        )
        self.payload_text.configure(xscrollcommand=payload_xbar.set)
        self.payload_text.pack(fill=BOTH, expand=True)
        payload_xbar.pack(side="bottom", fill=X)
        self._refresh_preset_combo()

    def _build_replay(self, tab: ttk.Frame) -> None:
        controls = ttk.LabelFrame(tab, text="Replay Controls")
        controls.pack(fill=X, pady=6)

        ttk.Button(controls, text="Prev", command=lambda: self._replay_step(-1)).pack(
            side=LEFT, padx=4, pady=4
        )
        ttk.Button(controls, text="Next", command=lambda: self._replay_step(1)).pack(
            side=LEFT, padx=4, pady=4
        )
        ttk.Button(controls, text="Play", command=self._replay_play).pack(side=LEFT, padx=4, pady=4)
        ttk.Button(controls, text="Pause", command=self._replay_pause).pack(
            side=LEFT, padx=4, pady=4
        )
        ttk.Label(controls, text="FPS").pack(side=LEFT, padx=4)
        fps_combo = ttk.Combobox(
            controls,
            width=6,
            textvariable=self.replay_fps_var,
            state="readonly",
            values=("15", "30", "60", "120"),
        )
        fps_combo.pack(side=LEFT)
        ttk.Label(controls, textvariable=self.replay_mode_var).pack(side=LEFT, padx=8)
        ttk.Label(controls, textvariable=self.replay_pos_var).pack(side=LEFT, padx=8)

        split = ttk.Panedwindow(tab, orient="vertical")
        split.pack(fill=BOTH, expand=True)

        tracks_frame = ttk.LabelFrame(split, text="Replay Tracks")
        details_frame = ttk.LabelFrame(split, text="Frame Details")
        split.add(tracks_frame, weight=2)
        split.add(details_frame, weight=3)

        self.replay_canvas = Canvas(tracks_frame, bg="#10141a", height=180)
        self.replay_canvas.pack(fill=BOTH, expand=True)

        lower_split = ttk.Panedwindow(details_frame, orient="horizontal")
        lower_split.pack(fill=BOTH, expand=True)

        commands_frame = ttk.LabelFrame(lower_split, text="Commands")
        checkpoints_frame = ttk.LabelFrame(lower_split, text="Checkpoints")
        preview_frame = ttk.LabelFrame(lower_split, text="State Preview")
        text_frame = ttk.LabelFrame(lower_split, text="Current Frame")
        lower_split.add(commands_frame, weight=2)
        lower_split.add(checkpoints_frame, weight=1)
        lower_split.add(preview_frame, weight=2)
        lower_split.add(text_frame, weight=2)

        commands_tree = ttk.Treeview(
            commands_frame, columns=("tick", "type", "payload"), show="headings"
        )
        for col, width in (("tick", 90), ("type", 180), ("payload", 420)):
            commands_tree.heading(col, text=col.upper())
            commands_tree.column(col, width=width, anchor="w")
        commands_bar = ttk.Scrollbar(commands_frame, orient=VERTICAL, command=commands_tree.yview)
        commands_tree.configure(yscrollcommand=commands_bar.set)
        commands_tree.pack(side=LEFT, fill=BOTH, expand=True)
        commands_bar.pack(side=RIGHT, fill=Y)
        self.replay_commands_tree = commands_tree

        checkpoints_tree = ttk.Treeview(
            checkpoints_frame, columns=("tick", "hash"), show="headings"
        )
        for col, width in (("tick", 90), ("hash", 260)):
            checkpoints_tree.heading(col, text=col.upper())
            checkpoints_tree.column(col, width=width, anchor="w")
        checkpoints_bar = ttk.Scrollbar(
            checkpoints_frame, orient=VERTICAL, command=checkpoints_tree.yview
        )
        checkpoints_tree.configure(yscrollcommand=checkpoints_bar.set)
        checkpoints_tree.pack(side=LEFT, fill=BOTH, expand=True)
        checkpoints_bar.pack(side=RIGHT, fill=Y)
        self.replay_checkpoints_tree = checkpoints_tree

        self.replay_preview_canvas = Canvas(preview_frame, bg="#0c1118")
        self.replay_preview_canvas.pack(fill=BOTH, expand=True)

        self.replay_text = ScrolledText(text_frame, wrap="none")
        self.replay_text.pack(fill=BOTH, expand=True)

        self.replay_scale = ttk.Scale(
            tab, from_=0, to=0, orient="horizontal", command=self._on_replay_seek
        )
        self.replay_scale.pack(fill=X, pady=6)

    def _build_crash(self, tab: ttk.Frame) -> None:
        self.crash_text = ScrolledText(tab, wrap="none")
        self.crash_text.pack(fill=BOTH, expand=True)

    def _build_profiling(self, tab: ttk.Frame) -> None:
        split = ttk.Panedwindow(tab, orient="vertical")
        split.pack(fill=BOTH, expand=True)

        summary_frame = ttk.LabelFrame(split, text="Summary")
        timeline_frame = ttk.LabelFrame(split, text="Span Timeline (mean duration by bucket)")
        tables_frame = ttk.LabelFrame(split, text="Top Offenders")
        hitches_frame = ttk.LabelFrame(split, text="Hitch Correlation")
        split.add(summary_frame, weight=1)
        split.add(timeline_frame, weight=2)
        split.add(tables_frame, weight=3)
        split.add(hitches_frame, weight=2)

        self.profiling_text = ScrolledText(summary_frame, wrap="none", height=6)
        self.profiling_text.pack(fill=BOTH, expand=True)

        self.profiling_canvas = Canvas(timeline_frame, bg="#10141a", height=180)
        self.profiling_canvas.pack(fill=BOTH, expand=True)

        table_split = ttk.Panedwindow(tables_frame, orient="horizontal")
        table_split.pack(fill=BOTH, expand=True)
        total_frame = ttk.LabelFrame(table_split, text="Top by Total")
        p95_frame = ttk.LabelFrame(table_split, text="Top by P95")
        table_split.add(total_frame, weight=1)
        table_split.add(p95_frame, weight=1)

        total_tree = ttk.Treeview(
            total_frame, columns=("key", "count", "total_ms", "p95_ms"), show="headings"
        )
        for col, width in (("key", 340), ("count", 80), ("total_ms", 110), ("p95_ms", 110)):
            total_tree.heading(col, text=col.upper())
            total_tree.column(col, width=width, anchor="w")
        total_bar = ttk.Scrollbar(total_frame, orient=VERTICAL, command=total_tree.yview)
        total_tree.configure(yscrollcommand=total_bar.set)
        total_tree.pack(side=LEFT, fill=BOTH, expand=True)
        total_bar.pack(side=RIGHT, fill=Y)
        self.profiling_total_tree = total_tree

        p95_tree = ttk.Treeview(
            p95_frame, columns=("key", "count", "p95_ms", "max_ms"), show="headings"
        )
        for col, width in (("key", 340), ("count", 80), ("p95_ms", 110), ("max_ms", 110)):
            p95_tree.heading(col, text=col.upper())
            p95_tree.column(col, width=width, anchor="w")
        p95_bar = ttk.Scrollbar(p95_frame, orient=VERTICAL, command=p95_tree.yview)
        p95_tree.configure(yscrollcommand=p95_bar.set)
        p95_tree.pack(side=LEFT, fill=BOTH, expand=True)
        p95_bar.pack(side=RIGHT, fill=Y)
        self.profiling_p95_tree = p95_tree

        hitch_tree = ttk.Treeview(
            hitches_frame,
            columns=("tick", "frame_ms", "top_span_key", "top_span_total_ms"),
            show="headings",
        )
        for col, width in (
            ("tick", 90),
            ("frame_ms", 120),
            ("top_span_key", 320),
            ("top_span_total_ms", 140),
        ):
            hitch_tree.heading(col, text=col.upper())
            hitch_tree.column(col, width=width, anchor="w")
        hitch_bar = ttk.Scrollbar(hitches_frame, orient=VERTICAL, command=hitch_tree.yview)
        hitch_tree.configure(yscrollcommand=hitch_bar.set)
        hitch_tree.pack(side=LEFT, fill=BOTH, expand=True)
        hitch_bar.pack(side=RIGHT, fill=Y)
        hitch_tree.bind("<<TreeviewSelect>>", self._on_profiling_hitch_select)
        self.profiling_hitch_tree = hitch_tree

    def _refresh_sessions(self) -> None:
        sessions = self.source.list_sessions()
        self.state.sessions = sessions
        if not sessions:
            self.session_combo["values"] = []
            self.status_var.set("No sessions discovered.")
            return

        labels = [self._session_label(session) for session in sessions]
        self.session_combo["values"] = labels
        self.session_var.set(labels[0])
        self._load_selected_session()

    def _load_selected_session(self) -> None:
        selected = self.session_var.get().strip()
        session = None
        for item in self.state.sessions:
            if self._session_label(item) == selected:
                session = item
                break
        if session is None:
            return

        self._replay_pause()
        self.state.selected_session = session
        self.state.events = self.source.load_events(session)
        self.state.spans = self.source.load_spans(session, limit=3_000)
        self.state.metrics = self.source.load_metrics(session)
        self.state.replay = self.source.load_replay(session)
        self.state.crash = self.source.load_crash(session)
        self._replay_render_packets = self._extract_replay_render_packets(self.state.events)

        self._refresh_summary_view()
        self._refresh_events_view()
        self._refresh_replay_view()
        self._refresh_crash_view()
        self._refresh_profiling_view()

        self.status_var.set(
            "Loaded "
            f"{session.id}: events={len(self.state.events)} "
            f"frames={len(self._replay_points())} "
            f"spans={len(self.state.spans)} "
            f"commands={len(self.state.replay.commands)}"
        )

    def _refresh_summary_view(self) -> None:
        if self.summary_text is None:
            return
        lines = build_summary_lines(
            session=self.state.selected_session,
            metrics=self.state.metrics,
            events=self.state.events,
            crash=self.state.crash,
        )
        self.summary_text.delete("1.0", END)
        self.summary_text.insert(END, "\n".join(lines))

    def _refresh_events_view(self) -> None:
        if self.events_tree is None:
            return
        filt = EventFilter(
            category=self.category_var.get() or "all",
            level=self.level_var.get() or "all",
            query=self.query_var.get(),
        )
        categories = sorted({event.category for event in self.state.events})
        filtered = apply_event_filter(self.state.events, filt)
        self._filtered_events = filtered

        category_values = ["all", *categories]
        for child in self.events_tree.get_children():
            self.events_tree.delete(child)
        for index, event in enumerate(filtered):
            self.events_tree.insert("", END, iid=str(index), values=event_to_row(event))

        if self.category_combo is not None:
            self.category_combo["values"] = tuple(category_values)

        if self.payload_text is not None:
            self.payload_text.delete("1.0", END)

    def _refresh_replay_view(self) -> None:
        replay_points = self._replay_points()
        model = build_replay_timeline_model(self.state.replay, replay_points)
        self._replay_checkpoint_mismatch_ticks = set(model.checkpoint_mismatch_ticks)
        frame_count = len(model.frame_ticks)
        self._replay_index = clamp_index(self._replay_index, frame_count)

        if self.replay_scale is not None:
            self.replay_scale.configure(to=max(0, frame_count - 1))
            self.replay_scale.set(self._replay_index)

        if self.replay_commands_tree is not None:
            for child in self.replay_commands_tree.get_children():
                self.replay_commands_tree.delete(child)
            for cmd in self.state.replay.commands[-200:]:
                payload = str(cmd.payload)
                if len(payload) > 120:
                    payload = payload[:117] + "..."
                self.replay_commands_tree.insert("", END, values=(cmd.tick, cmd.type, payload))

        if self.replay_checkpoints_tree is not None:
            for child in self.replay_checkpoints_tree.get_children():
                self.replay_checkpoints_tree.delete(child)
            for cp in self.state.replay.checkpoints[-200:]:
                self.replay_checkpoints_tree.insert("", END, values=(cp.tick, cp.hash))

        self._draw_replay_tracks(model)
        self._render_replay_index()

    def _draw_replay_tracks(self, model) -> None:
        canvas = self.replay_canvas
        if canvas is None:
            return
        canvas.delete("all")
        width = max(200, int(canvas.winfo_width() or 1000))
        height = max(120, int(canvas.winfo_height() or 180))
        canvas.create_rectangle(0, 0, width, height, fill="#10141a", outline="")

        ticks = model.frame_ticks
        if len(ticks) < 2:
            canvas.create_text(
                10, 10, anchor="nw", text="No replay frame track available.", fill="#95a0ac"
            )
            return

        min_tick = min(ticks)
        max_tick = max(ticks)
        span = max(1, max_tick - min_tick)
        pad_x = 24
        mid_y = height // 2
        plot_w = max(1, width - 2 * pad_x)

        canvas.create_line(pad_x, mid_y, pad_x + plot_w, mid_y, fill="#576574", width=1)

        max_density = max(1, model.max_command_density)
        for tick, density in model.command_count_by_tick.items():
            x = pad_x + ((tick - min_tick) / span) * plot_w
            bar_h = max(2, int((density / max_density) * (height * 0.35)))
            canvas.create_line(x, mid_y, x, mid_y - bar_h, fill="#4dd2ff", width=2)

        for tick in model.checkpoint_hash_by_tick:
            x = pad_x + ((tick - min_tick) / span) * plot_w
            canvas.create_line(x, mid_y, x, mid_y + 18, fill="#ffd166", width=2)

        for tick in model.checkpoint_mismatch_ticks:
            x = pad_x + ((tick - min_tick) / span) * plot_w
            canvas.create_line(x, mid_y - 24, x, mid_y + 24, fill="#ff4d6d", width=2)

        canvas.create_text(
            pad_x, 8, anchor="nw", text=f"ticks {min_tick}..{max_tick}", fill="#95a0ac"
        )
        canvas.create_text(
            width - pad_x,
            8,
            anchor="ne",
            text=f"max cmd density={model.max_command_density}",
            fill="#95a0ac",
        )

    def _render_replay_index(self) -> None:
        points = self._replay_points()
        idx = clamp_index(self._replay_index, len(points))
        self._replay_index = idx

        if not points:
            self.replay_pos_var.set("tick=n/a")
            if self.replay_text is not None:
                self.replay_text.delete("1.0", END)
                self.replay_text.insert(END, "No frame points available for replay.")
            return

        point = points[idx]
        tick = int(point.tick)
        self.replay_pos_var.set(f"tick={tick} index={idx + 1}/{len(points)}")

        commands = [cmd for cmd in self.state.replay.commands if int(cmd.tick) == tick]
        checkpoint = next(
            (cp for cp in self.state.replay.checkpoints if int(cp.tick) == tick), None
        )

        if self.replay_text is not None:
            mismatch = tick in self._replay_checkpoint_mismatch_ticks
            self.replay_text.delete("1.0", END)
            self.replay_text.insert(
                END,
                "\n".join(
                    [
                        f"tick={tick}",
                        f"frame_ms={point.frame_ms:.3f}",
                        f"render_ms={point.render_ms:.3f}",
                        f"fps_rolling={point.fps_rolling:.2f}",
                        f"commands_at_tick={len(commands)}",
                        f"checkpoint_hash={(checkpoint.hash if checkpoint is not None else 'n/a')}",
                        f"checkpoint_mismatch={mismatch}",
                    ]
                ),
            )
        self._draw_replay_state_preview(tick)

    def _on_replay_seek(self, value: str) -> None:
        self._replay_index = clamp_index(int(float(value)), len(self._replay_points()))
        self._render_replay_index()

    def _replay_step(self, delta: int) -> None:
        self._replay_index = step_index(self._replay_index, delta, len(self._replay_points()))
        if self.replay_scale is not None:
            self.replay_scale.set(self._replay_index)
        self._render_replay_index()

    def _replay_play(self) -> None:
        if self._replay_after_id is not None:
            return
        self.replay_mode_var.set("playing")

        def _tick() -> None:
            self._replay_index = next_playback_index(
                self._replay_index,
                len(self._replay_points()),
                loop=False,
            )
            if self.replay_scale is not None:
                self.replay_scale.set(self._replay_index)
            self._render_replay_index()
            point_count = len(self._replay_points())
            if point_count <= 0:
                self._replay_pause()
                return
            if self._replay_index >= point_count - 1:
                self._replay_pause()
                return
            interval = frame_interval_ms(float(self.replay_fps_var.get() or "60"))
            self._replay_after_id = self.root.after(interval, _tick)

        interval = frame_interval_ms(float(self.replay_fps_var.get() or "60"))
        self._replay_after_id = self.root.after(interval, _tick)

    def _replay_pause(self) -> None:
        if self._replay_after_id is not None:
            self.root.after_cancel(self._replay_after_id)
            self._replay_after_id = None
        self.replay_mode_var.set("stopped")

    def _refresh_crash_view(self) -> None:
        if self.crash_text is None:
            return
        text = build_crash_focus_text(self.state.crash, self.state.events)
        self.crash_text.delete("1.0", END)
        self.crash_text.insert(END, text)

    def _refresh_profiling_view(self) -> None:
        model = build_profiling_view_model(self.state.spans, self.state.metrics.frame_points)

        if self.profiling_text is not None:
            self.profiling_text.delete("1.0", END)
            self.profiling_text.insert(
                END,
                "\n".join(
                    [
                        f"total_spans={model.total_spans}",
                        f"timeline_points={len(model.timeline_points)}",
                        f"frame_timeline_points={len(model.frame_timeline_points)}",
                        f"render_timeline_points={len(model.render_timeline_points)}",
                        f"top_total_rows={len(model.top_total_rows)}",
                        f"top_p95_rows={len(model.top_p95_rows)}",
                        f"hitch_correlations={len(model.hitch_correlations)}",
                    ]
                ),
            )

        if self.profiling_total_tree is not None:
            self._profiling_total_iid_by_key = {}
            for child in self.profiling_total_tree.get_children():
                self.profiling_total_tree.delete(child)
            for index, row in enumerate(model.top_total_rows):
                iid = f"total-{index}"
                self.profiling_total_tree.insert(
                    "",
                    END,
                    iid=iid,
                    values=(row[0], row[1], f"{row[2]:.3f}", f"{row[3]:.3f}"),
                )
                self._profiling_total_iid_by_key[str(row[0])] = iid

        if self.profiling_p95_tree is not None:
            for child in self.profiling_p95_tree.get_children():
                self.profiling_p95_tree.delete(child)
            for row in model.top_p95_rows:
                self.profiling_p95_tree.insert(
                    "", END, values=(row[0], row[1], f"{row[2]:.3f}", f"{row[3]:.3f}")
                )

        if self.profiling_hitch_tree is not None:
            for child in self.profiling_hitch_tree.get_children():
                self.profiling_hitch_tree.delete(child)
            for index, item in enumerate(model.hitch_correlations):
                self.profiling_hitch_tree.insert(
                    "",
                    END,
                    iid=f"hitch-{index}",
                    values=(
                        item.tick,
                        f"{item.frame_ms:.3f}",
                        item.top_span_key,
                        f"{item.top_span_total_ms:.3f}",
                    ),
                )

        self._draw_profiling_timeline(model)

    def _draw_profiling_timeline(self, model: object) -> None:
        canvas = self.profiling_canvas
        if canvas is None:
            return
        canvas.delete("all")
        width = max(200, int(canvas.winfo_width() or 900))
        height = max(120, int(canvas.winfo_height() or 180))
        canvas.create_rectangle(0, 0, width, height, fill="#10141a", outline="")
        span_points = list(getattr(model, "timeline_points", []) or [])
        frame_points = list(getattr(model, "frame_timeline_points", []) or [])
        render_points = list(getattr(model, "render_timeline_points", []) or [])
        if len(span_points) < 2 and len(frame_points) < 2 and len(render_points) < 2:
            canvas.create_text(
                10,
                10,
                anchor="nw",
                text="No profiling timeline points available.",
                fill="#95a0ac",
            )
            return
        all_values = [point[1] for point in span_points + frame_points + render_points]
        min_v = min(all_values)
        max_v = max(all_values)
        span = max(1e-6, max_v - min_v)
        pad_x = 24
        pad_y = 18
        plot_w = max(1, int(width * 0.62) - 2 * pad_x)
        plot_h = max(1, height - 2 * pad_y)
        min_tick = min(point[0] for point in span_points + frame_points + render_points)
        max_tick = max(point[0] for point in span_points + frame_points + render_points)
        tick_span = max(1, max_tick - min_tick)

        def _draw_series(points: list[tuple[int, float]], color: str) -> None:
            if len(points) < 2:
                return
            poly: list[float] = []
            for tick, value in points:
                x = pad_x + ((tick - min_tick) / tick_span) * plot_w
                y = pad_y + (1.0 - ((value - min_v) / span)) * plot_h
                poly.extend((x, y))
            canvas.create_line(*poly, fill=color, width=2, smooth=True)

        _draw_series(frame_points, "#4dd2ff")
        _draw_series(render_points, "#7bf1a8")
        _draw_series(span_points, "#ffa657")

        # Visual summary of top offenders as an inline bar chart.
        bars = list(getattr(model, "top_total_rows", []) or [])[:8]
        bar_left = int(width * 0.66)
        bar_right = width - 16
        bar_top = 26
        bar_bottom = height - 18
        if bars:
            max_total = max(float(row[2]) for row in bars) or 1.0
            row_h = max(12, int((bar_bottom - bar_top) / len(bars)))
            for idx, row in enumerate(bars):
                key = str(row[0]).split(".", 1)[-1]
                total_ms = float(row[2])
                y0 = bar_top + idx * row_h
                y1 = min(bar_bottom, y0 + row_h - 3)
                fill_w = int((bar_right - bar_left) * (total_ms / max_total))
                canvas.create_rectangle(
                    bar_left, y0, bar_left + fill_w, y1, fill="#3b82f6", outline=""
                )
                canvas.create_text(
                    bar_left - 6, (y0 + y1) / 2, anchor="e", text=key[:28], fill="#95a0ac"
                )
                canvas.create_text(
                    bar_right, (y0 + y1) / 2, anchor="e", text=f"{total_ms:.1f}ms", fill="#d8dee9"
                )
        if self._profiling_selected_hitch_tick is not None:
            if max_tick > min_tick:
                marker_x = (
                    pad_x
                    + ((self._profiling_selected_hitch_tick - min_tick) / (max_tick - min_tick))
                    * plot_w
                )
                marker_x = max(float(pad_x), min(float(pad_x + plot_w), float(marker_x)))
                canvas.create_line(
                    marker_x, pad_y, marker_x, pad_y + plot_h, fill="#ff6b6b", width=2
                )
        canvas.create_text(pad_x, 4, anchor="nw", text=f"min={min_v:.3f}ms", fill="#7fd2ff")
        canvas.create_text(
            int(width * 0.33),
            4,
            anchor="nw",
            text="frame=#4dd2ff render=#7bf1a8 span=#ffa657",
            fill="#95a0ac",
        )
        canvas.create_text(width - pad_x, 4, anchor="ne", text=f"max={max_v:.3f}ms", fill="#7fd2ff")

    def _on_profiling_hitch_select(self, _event: object) -> None:
        if self.profiling_hitch_tree is None:
            return
        selected = self.profiling_hitch_tree.selection()
        if not selected:
            return
        values = self.profiling_hitch_tree.item(selected[0], "values")
        if len(values) < 3:
            return
        try:
            hitch_tick = int(values[0])
        except TypeError, ValueError:
            hitch_tick = None
        span_key = str(values[2])
        if self.profiling_total_tree is not None:
            iid = self._profiling_total_iid_by_key.get(span_key)
            if iid is not None:
                self.profiling_total_tree.selection_set(iid)
                self.profiling_total_tree.focus(iid)
                self.profiling_total_tree.see(iid)
        self._profiling_selected_hitch_tick = hitch_tick
        model = build_profiling_view_model(self.state.spans, self.state.metrics.frame_points)
        self._draw_profiling_timeline(model)

    def _on_event_select(self, _event: object) -> None:
        if self.events_tree is None or self.payload_text is None:
            return
        selected = self.events_tree.selection()
        if not selected:
            return
        try:
            index = int(selected[0])
        except ValueError:
            return
        if not (0 <= index < len(self._filtered_events)):
            return
        payload = format_event_payload(self._filtered_events[index])
        self.payload_text.delete("1.0", END)
        self.payload_text.insert(END, payload)

    def _replay_points(self) -> list[object]:
        if self.state.metrics.frame_points:
            return self.state.metrics.frame_points
        ticks = sorted(self._replay_render_packets)
        if not ticks:
            ticks = sorted(
                {int(cmd.tick) for cmd in self.state.replay.commands}
                | {int(cp.tick) for cp in self.state.replay.checkpoints}
            )
        if not ticks:
            return []
        # Fallback timeline when metrics stream is unavailable.
        from tools.engine_obs_core.contracts import FramePoint

        return [
            FramePoint(tick=tick, frame_ms=0.0, render_ms=0.0, fps_rolling=0.0) for tick in ticks
        ]

    @staticmethod
    def _extract_replay_render_packets(events: list[object]) -> dict[int, dict[str, object]]:
        packets: dict[int, dict[str, object]] = {}
        for event in events:
            category = getattr(event, "category", "")
            name = getattr(event, "name", "")
            if category != "ui_diag" or name != "ui.frame":
                continue
            metadata = getattr(event, "metadata", None)
            if not isinstance(metadata, dict):
                continue
            packet = metadata.get("render_packet")
            if not isinstance(packet, dict):
                continue
            tick = int(getattr(event, "tick", packet.get("frame_seq", 0)))
            packets[tick] = packet
        return packets

    def _draw_replay_state_preview(self, tick: int) -> None:
        canvas = self.replay_preview_canvas
        if canvas is None:
            return
        canvas.delete("all")
        width = max(200, int(canvas.winfo_width() or 560))
        height = max(140, int(canvas.winfo_height() or 260))
        canvas.create_rectangle(0, 0, width, height, fill="#0c1118", outline="")
        packet = self._replay_render_packets.get(int(tick))
        if packet is None:
            canvas.create_text(
                12, 12, anchor="nw", text="No render packet for this tick.", fill="#95a0ac"
            )
            return
        keyed = packet.get("keyed_transforms")
        if not isinstance(keyed, dict) or not keyed:
            canvas.create_text(
                12, 12, anchor="nw", text="Render packet has no keyed transforms.", fill="#95a0ac"
            )
            return
        bounds = packet.get("scene_bounds")
        if not isinstance(bounds, dict):
            canvas.create_text(
                12, 12, anchor="nw", text="Render packet missing scene bounds.", fill="#95a0ac"
            )
            return
        bx = float(bounds.get("x", 0.0))
        by = float(bounds.get("y", 0.0))
        bw = max(1.0, float(bounds.get("w", 1.0)))
        bh = max(1.0, float(bounds.get("h", 1.0)))
        pad = 14.0
        sx = (width - 2 * pad) / bw
        sy = (height - 2 * pad) / bh
        scale = max(0.001, min(sx, sy))
        for key, item in keyed.items():
            if not isinstance(item, dict):
                continue
            x = float(item.get("x", 0.0))
            y = float(item.get("y", 0.0))
            w = max(1.0, float(item.get("w", 1.0)))
            h = max(1.0, float(item.get("h", 1.0)))
            x0 = pad + (x - bx) * scale
            y0 = pad + (y - by) * scale
            x1 = x0 + w * scale
            y1 = y0 + h * scale
            if str(key).startswith("button:bg:"):
                color = "#3b82f6"
            elif str(key).startswith("button:text:"):
                color = "#f59e0b"
            elif str(key).startswith("bg:"):
                color = "#334155"
            else:
                color = "#22c55e"
            canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=2)
        canvas.create_text(
            12, 12, anchor="nw", text=f"tick={tick} primitives={len(keyed)}", fill="#d8dee9"
        )

    @staticmethod
    def _session_label(session: object) -> str:
        run_log = getattr(session, "run_log", None)
        ui_log = getattr(session, "ui_log", None)
        session_id = str(getattr(session, "id", "session"))
        run_name = run_log.name if run_log is not None else "n/a"
        ui_name = ui_log.name if ui_log is not None else "n/a"
        return f"{session_id} | run={run_name} | ui={ui_name}"


def run_app(*, logs_root: Path) -> int:
    root = Tk()
    SessionInspectorApp(root, logs_root=logs_root)
    root.mainloop()
    return 0
