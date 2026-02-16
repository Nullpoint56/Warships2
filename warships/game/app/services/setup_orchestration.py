"""Preset and new-game setup orchestration helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from warships.game.app.ports.runtime_services import clamp_scroll
from warships.game.app.services.new_game_flow import NewGameFlowService
from warships.game.app.services.preset_flow import PresetFlowService
from warships.game.app.ui_state import PresetRowView
from warships.game.core.models import FleetPlacement, ShipPlacement
from warships.game.presets.service import PresetService


@dataclass(frozen=True, slots=True)
class RefreshedPresetState:
    """Normalized preset list and scroll state after refresh."""

    rows: list[PresetRowView]
    selected_preset: str | None
    new_game_scroll: int
    preset_manage_scroll: int


@dataclass(frozen=True, slots=True)
class NewGameSelectionState:
    """Selected setup state for new-game screen."""

    selected_preset: str | None
    random_fleet: FleetPlacement | None
    preview: list[ShipPlacement]
    source_label: str | None


def refresh_preset_state(
    *,
    preset_service: PresetService,
    selected_preset: str | None,
    new_game_scroll: int,
    preset_manage_scroll: int,
    new_game_visible_rows: int,
    preset_manage_visible_rows: int,
    logger: logging.Logger,
) -> RefreshedPresetState:
    """Refresh preset rows and clamp related scroll state."""
    result = PresetFlowService.refresh_rows(
        preset_service=preset_service,
        selected_preset=selected_preset,
        scroll=new_game_scroll,
        visible_rows=new_game_visible_rows,
        logger=logger,
    )
    return RefreshedPresetState(
        rows=result.rows,
        selected_preset=result.selected_preset,
        new_game_scroll=result.scroll,
        preset_manage_scroll=clamp_scroll(preset_manage_scroll, preset_manage_visible_rows, len(result.rows)),
    )


def resolve_new_game_selection(
    *,
    preset_service: PresetService,
    preset_rows: list[PresetRowView],
) -> NewGameSelectionState:
    """Resolve default selected setup for new-game screen."""
    default_name = NewGameFlowService.default_selection(preset_rows)
    if default_name is None:
        return NewGameSelectionState(
            selected_preset=None,
            random_fleet=None,
            preview=[],
            source_label=None,
        )
    selection = NewGameFlowService.select_preset(preset_service, default_name)
    return NewGameSelectionState(
        selected_preset=selection.selected_preset,
        random_fleet=selection.random_fleet,
        preview=selection.preview,
        source_label=selection.source_label,
    )
