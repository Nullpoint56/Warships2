"""Preset/new-game flow helpers extracted from controller."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from warships.game.app.ports.runtime_services import (
    can_scroll_list_down,
    clamp_scroll,
    visible_slice,
)
from warships.game.app.ui_state import PresetRowView
from warships.game.core.models import FleetPlacement, ShipPlacement
from warships.game.presets.service import PresetService


@dataclass(frozen=True, slots=True)
class RefreshRowsResult:
    rows: list[PresetRowView]
    selected_preset: str | None
    scroll: int


@dataclass(frozen=True, slots=True)
class SelectPresetResult:
    selected_preset: str | None
    random_fleet: FleetPlacement | None
    preview: list[ShipPlacement]
    source_label: str | None
    status: str


@dataclass(frozen=True, slots=True)
class EditPresetResult:
    placements: list[ShipPlacement]
    status: str
    success: bool


class PresetFlowService:
    """Pure preset flow operations for controller orchestration."""

    @staticmethod
    def refresh_rows(
        preset_service: PresetService,
        selected_preset: str | None,
        scroll: int,
        visible_rows: int,
        logger: logging.Logger,
    ) -> RefreshRowsResult:
        rows: list[PresetRowView] = []
        for name in preset_service.list_presets():
            try:
                fleet = preset_service.load_preset(name)
            except (ValueError, FileNotFoundError) as exc:
                logger.warning("Skipping invalid preset '%s': %s", name, exc)
                continue
            rows.append(PresetRowView(name=name, placements=list(fleet.ships)))
        names = [row.name for row in rows]
        next_selected = selected_preset if selected_preset in names else None
        next_scroll = clamp_scroll(scroll, visible_rows, len(names))
        return RefreshRowsResult(rows=rows, selected_preset=next_selected, scroll=next_scroll)

    @staticmethod
    def visible_new_game_preset_names(
        rows: list[PresetRowView], scroll: int, visible_rows: int
    ) -> list[str]:
        names = [row.name for row in rows]
        return visible_slice(names, scroll, visible_rows)

    @staticmethod
    def can_scroll_down(rows: list[PresetRowView], scroll: int, visible_rows: int) -> bool:
        return can_scroll_list_down(scroll, visible_rows, len(rows))

    @staticmethod
    def select_new_game_preset(preset_service: PresetService, name: str) -> SelectPresetResult:
        try:
            fleet = preset_service.load_preset(name)
        except (ValueError, FileNotFoundError) as exc:
            return SelectPresetResult(
                selected_preset=None,
                random_fleet=None,
                preview=[],
                source_label=None,
                status=f"Failed to load preset '{name}': {exc}",
            )
        return SelectPresetResult(
            selected_preset=name,
            random_fleet=None,
            preview=list(fleet.ships),
            source_label=f"Preset: {name}",
            status=f"Selected preset '{name}'.",
        )

    @staticmethod
    def load_preset_for_edit(preset_service: PresetService, name: str) -> EditPresetResult:
        try:
            fleet = preset_service.load_preset(name)
        except (ValueError, FileNotFoundError) as exc:
            return EditPresetResult(
                placements=[], status=f"Failed to load preset '{name}': {exc}", success=False
            )
        return EditPresetResult(
            placements=list(fleet.ships),
            status=f"Editing preset '{name}'. Drag ships to adjust.",
            success=True,
        )
