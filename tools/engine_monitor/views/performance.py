from __future__ import annotations

from dataclasses import dataclass

from tools.engine_obs_core.datasource.live_source import LiveSnapshot


@dataclass(frozen=True)
class PerformanceBreakdownModel:
    sample_count: int
    frame_mean_ms: float
    render_mean_ms: float
    host_estimated_mean_ms: float
    render_share_pct: float
    host_share_pct: float
    bottleneck_lane: str
    top_render_span_name: str
    top_render_span_ms: float
    render_build_ms: float
    render_execute_ms: float
    render_present_ms: float
    render_total_ms: float
    render_mem_delta_mb: float
    render_present_mode: str
    render_execute_packet_count: int
    render_execute_pass_count: int
    render_execute_static_packet_count: int
    render_execute_dynamic_packet_count: int
    render_execute_packet_build_ms: float
    render_execute_auto_static_ms: float
    render_execute_static_packet_cache_hits: int
    render_execute_static_reused: bool
    render_execute_static_bundle_replayed: bool
    render_execute_static_upload_bytes: int
    render_execute_dynamic_upload_bytes: int
    render_execute_static_rebuild_count: int
    render_execute_static_run_count: int
    render_execute_dynamic_run_count: int
    render_execute_stage_upload_ms: float
    render_execute_translate_ms: float
    render_execute_expand_ms: float
    render_execute_rect_batch_ms: float
    render_execute_text_batch_ms: float
    render_execute_text_layout_ms: float
    render_execute_text_shape_ms: float
    render_execute_text_shape_calls: int
    render_execute_atlas_upload_ms: float
    render_execute_atlas_upload_bytes: int
    render_execute_atlas_upload_count: int
    render_execute_packet_translate_count: int
    render_execute_rect_count: int
    render_execute_text_quad_count: int
    render_execute_draw_calls: int
    render_execute_pipeline_binds: int
    render_execute_vertex_buffer_binds: int
    render_execute_bind_group_binds: int
    render_execute_bundle_replays: int
    render_execute_cffi_type_miss_total: int
    render_execute_cffi_type_miss_delta: int
    render_execute_cffi_type_miss_unique: int
    render_execute_cffi_type_miss_top: tuple[tuple[str, int], ...]
    render_execute_pass_packet_counts: tuple[tuple[str, int], ...]
    render_execute_kind_packet_counts: tuple[tuple[str, int], ...]
    render_execute_kind_rect_counts: tuple[tuple[str, int], ...]
    render_execute_kind_text_quad_counts: tuple[tuple[str, int], ...]
    top_system_name: str
    top_system_ms: float
    top_systems: tuple[tuple[str, float], ...]
    python_current_mb: float
    process_rss_mb: float
    profile_capture_state: str
    profile_capture_frames: int
    profile_capture_target_frames: int
    profile_capture_report_path: str
    profile_capture_error: str
    render_stage_event_counts: tuple[tuple[str, int], ...]


def build_performance_breakdown_model(
    snapshot: LiveSnapshot, *, max_points: int = 180
) -> PerformanceBreakdownModel:
    points = snapshot.frame_points[-max(1, int(max_points)) :]
    if not points:
        return PerformanceBreakdownModel(
            sample_count=0,
            frame_mean_ms=0.0,
            render_mean_ms=0.0,
            host_estimated_mean_ms=0.0,
            render_share_pct=0.0,
            host_share_pct=0.0,
            bottleneck_lane="unknown",
            top_render_span_name="n/a",
            top_render_span_ms=0.0,
            render_build_ms=0.0,
            render_execute_ms=0.0,
            render_present_ms=0.0,
            render_total_ms=0.0,
            render_mem_delta_mb=0.0,
            render_present_mode="unknown",
            render_execute_packet_count=0,
            render_execute_pass_count=0,
            render_execute_static_packet_count=0,
            render_execute_dynamic_packet_count=0,
            render_execute_packet_build_ms=0.0,
            render_execute_auto_static_ms=0.0,
            render_execute_static_packet_cache_hits=0,
            render_execute_static_reused=False,
            render_execute_static_bundle_replayed=False,
            render_execute_static_upload_bytes=0,
            render_execute_dynamic_upload_bytes=0,
            render_execute_static_rebuild_count=0,
            render_execute_static_run_count=0,
            render_execute_dynamic_run_count=0,
            render_execute_stage_upload_ms=0.0,
            render_execute_translate_ms=0.0,
            render_execute_expand_ms=0.0,
            render_execute_rect_batch_ms=0.0,
            render_execute_text_batch_ms=0.0,
            render_execute_text_layout_ms=0.0,
            render_execute_text_shape_ms=0.0,
            render_execute_text_shape_calls=0,
            render_execute_atlas_upload_ms=0.0,
            render_execute_atlas_upload_bytes=0,
            render_execute_atlas_upload_count=0,
            render_execute_packet_translate_count=0,
            render_execute_rect_count=0,
            render_execute_text_quad_count=0,
            render_execute_draw_calls=0,
            render_execute_pipeline_binds=0,
            render_execute_vertex_buffer_binds=0,
            render_execute_bind_group_binds=0,
            render_execute_bundle_replays=0,
            render_execute_cffi_type_miss_total=0,
            render_execute_cffi_type_miss_delta=0,
            render_execute_cffi_type_miss_unique=0,
            render_execute_cffi_type_miss_top=(),
            render_execute_pass_packet_counts=(),
            render_execute_kind_packet_counts=(),
            render_execute_kind_rect_counts=(),
            render_execute_kind_text_quad_counts=(),
            top_system_name="n/a",
            top_system_ms=0.0,
            top_systems=(),
            python_current_mb=0.0,
            process_rss_mb=0.0,
            profile_capture_state="off",
            profile_capture_frames=0,
            profile_capture_target_frames=0,
            profile_capture_report_path="",
            profile_capture_error="",
            render_stage_event_counts=(),
        )
    frame_sum = 0.0
    render_sum = 0.0
    for point in points:
        frame_sum += max(0.0, float(point.frame_ms))
        render_sum += max(0.0, float(point.render_ms))
    count = len(points)
    frame_mean = frame_sum / count
    render_mean = render_sum / count
    host_mean = max(0.0, frame_mean - render_mean)
    total = max(0.0001, frame_mean)
    render_share = min(100.0, max(0.0, (render_mean / total) * 100.0))
    host_share = min(100.0, max(0.0, (host_mean / total) * 100.0))
    if render_share >= 65.0:
        lane = "render"
    elif host_share >= 65.0:
        lane = "host/sim/input"
    else:
        lane = "mixed"

    span_totals: dict[str, float] = {}
    for span in snapshot.spans:
        if str(span.category) != "render":
            continue
        name = str(span.name) or "render.unknown"
        span_totals[name] = span_totals.get(name, 0.0) + max(0.0, float(span.duration_ms))
    if span_totals:
        top_span_name, top_span_ms = max(span_totals.items(), key=lambda item: item[1])
    else:
        top_span_name, top_span_ms = ("n/a", 0.0)

    stage_counts: dict[str, int] = {}
    for event in snapshot.events:
        name = str(event.name)
        if not name.startswith("render.stage."):
            continue
        stage = name.removeprefix("render.stage.")
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
    sorted_stage_counts = tuple(
        sorted(stage_counts.items(), key=lambda item: item[1], reverse=True)[:8]
    )
    render_profile = _latest_dict_event_value(snapshot, "render.profile_frame")
    render_build_ms = _safe_float(render_profile.get("build_ms"), 0.0)
    render_execute_ms = _safe_float(render_profile.get("execute_ms"), 0.0)
    render_present_ms = _safe_float(render_profile.get("present_ms"), 0.0)
    render_total_ms = _safe_float(render_profile.get("total_ms"), 0.0)
    render_mem_delta_mb = _safe_float(render_profile.get("mem_delta_mb"), 0.0)
    render_present_mode = str(render_profile.get("present_mode", "unknown")).strip() or "unknown"
    render_execute_packet_count = _safe_int(render_profile.get("execute_packet_count"), 0)
    render_execute_pass_count = _safe_int(render_profile.get("execute_pass_count"), 0)
    render_execute_static_packet_count = _safe_int(
        render_profile.get("execute_static_packet_count"), 0
    )
    render_execute_dynamic_packet_count = _safe_int(
        render_profile.get("execute_dynamic_packet_count"), 0
    )
    render_execute_packet_build_ms = _safe_float(
        render_profile.get("execute_packet_build_ms"), 0.0
    )
    render_execute_auto_static_ms = _safe_float(
        render_profile.get("execute_auto_static_ms"), 0.0
    )
    render_execute_static_packet_cache_hits = _safe_int(
        render_profile.get("execute_static_packet_cache_hits"), 0
    )
    render_execute_static_reused = bool(render_profile.get("execute_static_reused", False))
    render_execute_static_bundle_replayed = bool(
        render_profile.get("execute_static_bundle_replayed", False)
    )
    render_execute_static_upload_bytes = _safe_int(
        render_profile.get("execute_static_upload_bytes"), 0
    )
    render_execute_dynamic_upload_bytes = _safe_int(
        render_profile.get("execute_dynamic_upload_bytes"), 0
    )
    render_execute_static_rebuild_count = _safe_int(
        render_profile.get("execute_static_rebuild_count"), 0
    )
    render_execute_static_run_count = _safe_int(
        render_profile.get("execute_static_run_count"), 0
    )
    render_execute_dynamic_run_count = _safe_int(
        render_profile.get("execute_dynamic_run_count"), 0
    )
    render_execute_stage_upload_ms = _safe_float(render_profile.get("execute_stage_upload_ms"), 0.0)
    render_execute_translate_ms = _safe_float(render_profile.get("execute_translate_ms"), 0.0)
    render_execute_expand_ms = _safe_float(render_profile.get("execute_expand_ms"), 0.0)
    render_execute_rect_batch_ms = _safe_float(render_profile.get("execute_rect_batch_ms"), 0.0)
    render_execute_text_batch_ms = _safe_float(render_profile.get("execute_text_batch_ms"), 0.0)
    render_execute_text_layout_ms = _safe_float(render_profile.get("execute_text_layout_ms"), 0.0)
    render_execute_text_shape_ms = _safe_float(render_profile.get("execute_text_shape_ms"), 0.0)
    render_execute_text_shape_calls = _safe_int(render_profile.get("execute_text_shape_calls"), 0)
    render_execute_atlas_upload_ms = _safe_float(render_profile.get("execute_atlas_upload_ms"), 0.0)
    render_execute_atlas_upload_bytes = _safe_int(
        render_profile.get("execute_atlas_upload_bytes"), 0
    )
    render_execute_atlas_upload_count = _safe_int(
        render_profile.get("execute_atlas_upload_count"), 0
    )
    render_execute_packet_translate_count = _safe_int(
        render_profile.get("execute_packet_translate_count"), 0
    )
    render_execute_rect_count = _safe_int(render_profile.get("execute_rect_count"), 0)
    render_execute_text_quad_count = _safe_int(render_profile.get("execute_text_quad_count"), 0)
    render_execute_draw_calls = _safe_int(render_profile.get("execute_draw_calls"), 0)
    render_execute_pipeline_binds = _safe_int(render_profile.get("execute_pipeline_binds"), 0)
    render_execute_vertex_buffer_binds = _safe_int(
        render_profile.get("execute_vertex_buffer_binds"), 0
    )
    render_execute_bind_group_binds = _safe_int(
        render_profile.get("execute_bind_group_binds"), 0
    )
    render_execute_bundle_replays = _safe_int(render_profile.get("execute_bundle_replays"), 0)
    render_execute_cffi_type_miss_total = _safe_int(
        render_profile.get("execute_cffi_type_miss_total"), 0
    )
    render_execute_cffi_type_miss_delta = _safe_int(
        render_profile.get("execute_cffi_type_miss_delta"), 0
    )
    render_execute_cffi_type_miss_unique = _safe_int(
        render_profile.get("execute_cffi_type_miss_unique"), 0
    )
    render_execute_cffi_type_miss_top = _safe_sorted_counts(
        render_profile.get("execute_cffi_type_miss_top")
    )
    render_execute_pass_packet_counts = _safe_sorted_counts(
        render_profile.get("execute_pass_packet_counts")
    )
    render_execute_kind_packet_counts = _safe_sorted_counts(
        render_profile.get("execute_kind_packet_counts")
    )
    render_execute_kind_rect_counts = _safe_sorted_counts(
        render_profile.get("execute_kind_rect_counts")
    )
    render_execute_kind_text_quad_counts = _safe_sorted_counts(
        render_profile.get("execute_kind_text_quad_counts")
    )
    frame_profile = _latest_dict_event_value(snapshot, "perf.frame_profile")
    top_system_name = "n/a"
    top_system_ms = 0.0
    top_systems: tuple[tuple[str, float], ...] = ()
    python_current_mb = 0.0
    process_rss_mb = 0.0
    profile_capture_state = "off"
    profile_capture_frames = 0
    profile_capture_target_frames = 0
    profile_capture_report_path = ""
    profile_capture_error = ""
    systems = frame_profile.get("systems")
    if isinstance(systems, dict):
        top = systems.get("top_system")
        if isinstance(top, dict):
            top_system_name = str(top.get("name", "n/a"))
            top_system_ms = _safe_float(top.get("ms"), 0.0)
        top_rows = systems.get("top_systems")
        if isinstance(top_rows, (list, tuple)):
            parsed_rows: list[tuple[str, float]] = []
            for row in top_rows:
                if not isinstance(row, dict):
                    continue
                parsed_rows.append(
                    (
                        str(row.get("name", "")),
                        _safe_float(row.get("ms"), 0.0),
                    )
                )
            top_systems = tuple(parsed_rows)
    memory = frame_profile.get("memory")
    if isinstance(memory, dict):
        python_current_mb = _safe_float(memory.get("python_current_mb"), 0.0)
        process_rss_mb = _safe_float(memory.get("process_rss_mb"), 0.0)
    capture = frame_profile.get("capture")
    if isinstance(capture, dict):
        profile_capture_state = str(capture.get("state", "off"))
        profile_capture_frames = _safe_int(capture.get("captured_frames"), 0)
        profile_capture_target_frames = _safe_int(capture.get("target_frames"), 0)
        profile_capture_report_path = str(capture.get("report_path", ""))
        profile_capture_error = str(capture.get("error", ""))
    if top_span_name == "n/a":
        block_candidates = (
            ("render.build", render_build_ms),
            ("render.execute", render_execute_ms),
            ("render.present", render_present_ms),
        )
        top_block_name, top_block_ms = max(block_candidates, key=lambda item: item[1])
        if top_block_ms > 0.0:
            top_span_name = top_block_name
            top_span_ms = float(top_block_ms)

    return PerformanceBreakdownModel(
        sample_count=count,
        frame_mean_ms=frame_mean,
        render_mean_ms=render_mean,
        host_estimated_mean_ms=host_mean,
        render_share_pct=render_share,
        host_share_pct=host_share,
        bottleneck_lane=lane,
        top_render_span_name=top_span_name,
        top_render_span_ms=float(top_span_ms),
        render_build_ms=render_build_ms,
        render_execute_ms=render_execute_ms,
        render_present_ms=render_present_ms,
        render_total_ms=render_total_ms,
        render_mem_delta_mb=render_mem_delta_mb,
        render_present_mode=render_present_mode,
        render_execute_packet_count=render_execute_packet_count,
        render_execute_pass_count=render_execute_pass_count,
        render_execute_static_packet_count=render_execute_static_packet_count,
        render_execute_dynamic_packet_count=render_execute_dynamic_packet_count,
        render_execute_packet_build_ms=render_execute_packet_build_ms,
        render_execute_auto_static_ms=render_execute_auto_static_ms,
        render_execute_static_packet_cache_hits=render_execute_static_packet_cache_hits,
        render_execute_static_reused=render_execute_static_reused,
        render_execute_static_bundle_replayed=render_execute_static_bundle_replayed,
        render_execute_static_upload_bytes=render_execute_static_upload_bytes,
        render_execute_dynamic_upload_bytes=render_execute_dynamic_upload_bytes,
        render_execute_static_rebuild_count=render_execute_static_rebuild_count,
        render_execute_static_run_count=render_execute_static_run_count,
        render_execute_dynamic_run_count=render_execute_dynamic_run_count,
        render_execute_stage_upload_ms=render_execute_stage_upload_ms,
        render_execute_translate_ms=render_execute_translate_ms,
        render_execute_expand_ms=render_execute_expand_ms,
        render_execute_rect_batch_ms=render_execute_rect_batch_ms,
        render_execute_text_batch_ms=render_execute_text_batch_ms,
        render_execute_text_layout_ms=render_execute_text_layout_ms,
        render_execute_text_shape_ms=render_execute_text_shape_ms,
        render_execute_text_shape_calls=render_execute_text_shape_calls,
        render_execute_atlas_upload_ms=render_execute_atlas_upload_ms,
        render_execute_atlas_upload_bytes=render_execute_atlas_upload_bytes,
        render_execute_atlas_upload_count=render_execute_atlas_upload_count,
        render_execute_packet_translate_count=render_execute_packet_translate_count,
        render_execute_rect_count=render_execute_rect_count,
        render_execute_text_quad_count=render_execute_text_quad_count,
        render_execute_draw_calls=render_execute_draw_calls,
        render_execute_pipeline_binds=render_execute_pipeline_binds,
        render_execute_vertex_buffer_binds=render_execute_vertex_buffer_binds,
        render_execute_bind_group_binds=render_execute_bind_group_binds,
        render_execute_bundle_replays=render_execute_bundle_replays,
        render_execute_cffi_type_miss_total=render_execute_cffi_type_miss_total,
        render_execute_cffi_type_miss_delta=render_execute_cffi_type_miss_delta,
        render_execute_cffi_type_miss_unique=render_execute_cffi_type_miss_unique,
        render_execute_cffi_type_miss_top=render_execute_cffi_type_miss_top,
        render_execute_pass_packet_counts=render_execute_pass_packet_counts,
        render_execute_kind_packet_counts=render_execute_kind_packet_counts,
        render_execute_kind_rect_counts=render_execute_kind_rect_counts,
        render_execute_kind_text_quad_counts=render_execute_kind_text_quad_counts,
        top_system_name=top_system_name,
        top_system_ms=top_system_ms,
        top_systems=top_systems,
        python_current_mb=python_current_mb,
        process_rss_mb=process_rss_mb,
        profile_capture_state=profile_capture_state,
        profile_capture_frames=profile_capture_frames,
        profile_capture_target_frames=profile_capture_target_frames,
        profile_capture_report_path=profile_capture_report_path,
        profile_capture_error=profile_capture_error,
        render_stage_event_counts=sorted_stage_counts,
    )


def _latest_dict_event_value(snapshot: LiveSnapshot, name: str) -> dict[str, object]:
    for event in reversed(snapshot.events):
        if str(event.name) != name:
            continue
        value = event.value
        if isinstance(value, dict):
            return value
        return {}
    return {}


def _safe_float(value: object, default: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return float(default)


def _safe_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return int(default)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return int(value)
    return int(default)


def _safe_sorted_counts(value: object) -> tuple[tuple[str, int], ...]:
    if not isinstance(value, dict):
        return ()
    parsed: list[tuple[str, int]] = []
    for key, raw_count in value.items():
        parsed.append((str(key), max(0, _safe_int(raw_count, 0))))
    return tuple(sorted(parsed, key=lambda item: item[1], reverse=True))
