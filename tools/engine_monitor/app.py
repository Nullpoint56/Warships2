from __future__ import annotations

from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, VERTICAL, BooleanVar, Canvas, StringVar, Tk, X, Y, ttk
from tkinter.scrolledtext import ScrolledText

from tools.engine_monitor.views.health import build_health_view_model
from tools.engine_monitor.views.hitches import build_hitch_rows
from tools.engine_monitor.views.performance import build_performance_breakdown_model
from tools.engine_monitor.views.render_resize import build_render_resize_model
from tools.engine_monitor.views.timeline import build_timeline_points
from tools.engine_obs_core.datasource.live_source import LiveObsSource


class MonitorApp:
    def __init__(
        self,
        root: Tk,
        *,
        logs_root: Path,
        refresh_ms: int,
        hitch_threshold_ms: float,
        remote_url: str,
    ) -> None:
        self.root = root
        self.root.title("Engine Monitor")
        self.root.geometry("1280x860")
        self.source = LiveObsSource(logs_root, remote_url=remote_url)
        self.refresh_ms = max(100, int(refresh_ms))
        self.hitch_threshold_ms = float(hitch_threshold_ms)
        self.status_var = StringVar(value="Live source idle.")
        self.freeze_var = BooleanVar(value=False)
        self.health_text: ScrolledText | None = None
        self.timeline_canvas: Canvas | None = None
        self.hitch_tree: ttk.Treeview | None = None
        self.render_text: ScrolledText | None = None
        self.performance_text: ScrolledText | None = None
        self._last_snapshot_signature: tuple[object, ...] | None = None
        self._last_health_text: str = ""
        self._last_render_text: str = ""
        self._last_performance_text: str = ""
        self._last_hitch_rows: tuple[tuple[object, ...], ...] = ()
        self._build()
        self._tick()

    def _build(self) -> None:
        top = ttk.Frame(self.root)
        top.pack(fill=X, padx=8, pady=8)
        ttk.Label(top, textvariable=self.status_var).pack(side=LEFT)
        ttk.Checkbutton(top, text="Freeze", variable=self.freeze_var).pack(side=RIGHT, padx=4)
        ttk.Button(top, text="Copy Perf", command=self._copy_performance).pack(side=RIGHT, padx=4)
        ttk.Button(top, text="Poll now", command=self._tick_once).pack(side=RIGHT, padx=4)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=BOTH, expand=True, padx=8, pady=8)
        health_tab = ttk.Frame(notebook)
        timeline_tab = ttk.Frame(notebook)
        hitches_tab = ttk.Frame(notebook)
        render_tab = ttk.Frame(notebook)
        performance_tab = ttk.Frame(notebook)
        notebook.add(health_tab, text="Health")
        notebook.add(timeline_tab, text="Timeline")
        notebook.add(hitches_tab, text="Hitch Analyzer")
        notebook.add(render_tab, text="Render/Resize")
        notebook.add(performance_tab, text="Perf Breakdown")

        self.health_text = ScrolledText(health_tab, wrap="none")
        self.health_text.pack(fill=BOTH, expand=True)

        self.timeline_canvas = Canvas(timeline_tab, bg="#10141a")
        self.timeline_canvas.pack(fill=BOTH, expand=True)

        columns = ("tick", "frame_ms", "top_span", "top_span_ms")
        tree = ttk.Treeview(hitches_tab, columns=columns, show="headings")
        for col, width in (
            ("tick", 90),
            ("frame_ms", 120),
            ("top_span", 420),
            ("top_span_ms", 120),
        ):
            tree.heading(col, text=col.upper())
            tree.column(col, width=width, anchor="w")
        bar = ttk.Scrollbar(hitches_tab, orient=VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=bar.set)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        bar.pack(side=RIGHT, fill=Y)
        self.hitch_tree = tree

        self.render_text = ScrolledText(render_tab, wrap="none")
        self.render_text.pack(fill=BOTH, expand=True)

        self.performance_text = ScrolledText(performance_tab, wrap="none")
        self.performance_text.pack(fill=BOTH, expand=True)

    def _tick(self) -> None:
        self._tick_once()
        self.root.after(self.refresh_ms, self._tick)

    def _tick_once(self) -> None:
        snap = self.source.poll()
        if self.freeze_var.get():
            self.status_var.set("Frozen. Polling continues in background; UI updates paused.")
            return
        signature = self._snapshot_signature(snap)
        if signature == self._last_snapshot_signature:
            self.status_var.set(
                f"No new engine data. events={len(snap.events)} spans={len(snap.spans)}"
            )
            return
        self._last_snapshot_signature = signature
        polled_at = snap.polled_at_utc or "n/a"
        self.status_var.set(f"events={len(snap.events)} spans={len(snap.spans)} polled={polled_at}")
        self._update_health(snap)
        self._update_timeline(snap)
        self._update_hitches(snap)
        self._update_render(snap)
        self._update_performance(snap)

    def _update_health(self, snapshot) -> None:
        if self.health_text is None:
            return
        model = build_health_view_model(snapshot, hitch_threshold_ms=self.hitch_threshold_ms)
        lines = [
            f"fps: {model.fps:.2f}",
            f"frame_mean_ms: {model.frame_ms_mean:.3f}",
            f"frame_p95_ms: {model.frame_ms_p95:.3f}",
            f"frame_p99_ms: {model.frame_ms_p99:.3f}",
            f"render_mean_ms: {model.render_ms_mean:.3f}",
            f"max_frame_ms: {model.max_frame_ms:.3f}",
            f"resize_count: {model.resize_count}",
            "",
            "alerts:",
        ]
        lines.extend([f"- {alert}" for alert in model.alerts] or ["- none"])
        content = "\n".join(lines)
        if content == self._last_health_text:
            return
        self._last_health_text = content
        self._replace_text(self.health_text, content)

    def _update_timeline(self, snapshot) -> None:
        if self.timeline_canvas is None:
            return
        points = build_timeline_points(snapshot.events)[-120:]
        canvas = self.timeline_canvas
        canvas.delete("all")
        width = max(1, int(canvas.winfo_width() or 1200))
        height = max(1, int(canvas.winfo_height() or 420))
        if not points:
            canvas.create_text(
                width // 2, height // 2, text="No live timeline points.", fill="#9aa3af"
            )
            return
        max_value = max(
            1.0,
            max(max(p.frame_ms, p.render_ms, p.queue_depth, p.publish_count) for p in points),
        )

        def y(value: float) -> float:
            return height - (value / max_value) * (height - 20.0) - 10.0

        step = width / max(1, len(points) - 1)
        frame_coords = []
        render_coords = []
        for idx, point in enumerate(points):
            x = idx * step
            frame_coords.extend((x, y(point.frame_ms)))
            render_coords.extend((x, y(point.render_ms)))
        canvas.create_line(*frame_coords, fill="#55d8ff", width=2)
        canvas.create_line(*render_coords, fill="#ffa657", width=2)
        canvas.create_text(80, 16, text="frame.time_ms", fill="#55d8ff")
        canvas.create_text(220, 16, text="render.frame_ms", fill="#ffa657")

    def _update_hitches(self, snapshot) -> None:
        if self.hitch_tree is None:
            return
        rows = build_hitch_rows(snapshot, threshold_ms=self.hitch_threshold_ms)
        tree = self.hitch_tree
        rows_payload = tuple(
            (
                row.tick,
                f"{row.frame_ms:.3f}",
                row.top_span,
                f"{row.top_span_ms:.3f}",
            )
            for row in rows[:200]
        )
        if rows_payload == self._last_hitch_rows:
            return
        self._last_hitch_rows = rows_payload
        for item in tree.get_children():
            tree.delete(item)
        for payload in rows_payload:
            tree.insert(
                "",
                END,
                values=payload,
            )

    def _update_render(self, snapshot) -> None:
        if self.render_text is None:
            return
        model = build_render_resize_model(snapshot.events)
        lines = [
            f"resize_events: {model.resize_events}",
            f"viewport_updates: {model.viewport_updates}",
            f"camera_projection_updates: {model.camera_projection_updates}",
            f"pixel_ratio_updates: {model.pixel_ratio_updates}",
            f"surface_dim_updates: {model.surface_dim_updates}",
            f"present_interval_updates: {model.present_interval_updates}",
            "",
            f"last_resize_value: {model.last_resize_value}",
        ]
        content = "\n".join(lines)
        if content == self._last_render_text:
            return
        self._last_render_text = content
        self._replace_text(self.render_text, content)

    def _update_performance(self, snapshot) -> None:
        if self.performance_text is None:
            return
        model = build_performance_breakdown_model(snapshot)
        lines = [
            f"sample_count: {model.sample_count}",
            f"frame_mean_ms: {model.frame_mean_ms:.3f}",
            f"render_mean_ms: {model.render_mean_ms:.3f}",
            f"host_estimated_mean_ms: {model.host_estimated_mean_ms:.3f}",
            f"render_share_pct: {model.render_share_pct:.2f}",
            f"host_share_pct: {model.host_share_pct:.2f}",
            f"bottleneck_lane: {model.bottleneck_lane}",
            "",
            f"top_render_span: {model.top_render_span_name}",
            f"top_render_span_total_ms: {model.top_render_span_ms:.3f}",
            "",
            "latest renderer block profile:",
            f"- build_ms: {model.render_build_ms:.3f}",
            f"- execute_ms: {model.render_execute_ms:.3f}",
            f"- present_ms: {model.render_present_ms:.3f}",
            f"- total_ms: {model.render_total_ms:.3f}",
            f"- mem_delta_mb: {model.render_mem_delta_mb:.3f}",
            f"- execute_packet_total: {model.render_execute_packet_count}",
            f"- execute_passes_total: {model.render_execute_pass_count}",
            f"- execute_static_packets: {model.render_execute_static_packet_count}",
            f"- execute_dynamic_packets: {model.render_execute_dynamic_packet_count}",
            f"- execute_static_reused: {model.render_execute_static_reused}",
            f"- execute_static_bundle_replayed: {model.render_execute_static_bundle_replayed}",
            f"- execute_static_upload_bytes: {model.render_execute_static_upload_bytes}",
            f"- execute_dynamic_upload_bytes: {model.render_execute_dynamic_upload_bytes}",
            f"- execute_static_rebuild_count: {model.render_execute_static_rebuild_count}",
            f"- execute_static_run_count: {model.render_execute_static_run_count}",
            f"- execute_dynamic_run_count: {model.render_execute_dynamic_run_count}",
            "",
            "latest renderer execute breakdown:",
        ]
        if model.render_execute_pass_packet_counts:
            lines.extend(
                [f"- pass:{name} packets={count}" for name, count in model.render_execute_pass_packet_counts]
            )
        else:
            lines.append("- pass counts: n/a")
        if model.render_execute_kind_packet_counts:
            lines.extend(
                [f"- kind:{name} packets={count}" for name, count in model.render_execute_kind_packet_counts]
            )
        else:
            lines.append("- kind counts: n/a")
        lines.extend(
            [
            "",
            "latest system/profile snapshot:",
            f"- top_system: {model.top_system_name}",
            f"- top_system_ms: {model.top_system_ms:.3f}",
            f"- python_current_mb: {model.python_current_mb:.3f}",
            f"- process_rss_mb: {model.process_rss_mb:.3f}",
            "",
            "render.stage event counts:",
            ]
        )
        if model.render_stage_event_counts:
            lines.extend(
                [f"- {stage}: {count}" for stage, count in model.render_stage_event_counts]
            )
        else:
            lines.append("- none")
        content = "\n".join(lines)
        if content == self._last_performance_text:
            return
        self._last_performance_text = content
        self._replace_text(self.performance_text, content)

    def _copy_performance(self) -> None:
        if self.performance_text is None:
            return
        content = self.performance_text.get("1.0", END).strip()
        if not content:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.status_var.set("Performance panel copied to clipboard.")

    @staticmethod
    def _replace_text(widget: ScrolledText, content: str) -> None:
        widget.delete("1.0", END)
        widget.insert("1.0", content)

    @staticmethod
    def _snapshot_signature(snapshot) -> tuple[object, ...]:
        max_event_tick = max((int(event.tick) for event in snapshot.events), default=-1)
        max_span_tick = max((int(span.tick) for span in snapshot.spans), default=-1)
        max_point_tick = max((int(point.tick) for point in snapshot.frame_points), default=-1)
        return (
            max_event_tick,
            max_span_tick,
            max_point_tick,
            int(len(snapshot.events)),
            int(len(snapshot.spans)),
            int(len(snapshot.frame_points)),
            float(snapshot.rolling_frame_ms),
            float(snapshot.rolling_render_ms),
            int(snapshot.resize_count),
        )
