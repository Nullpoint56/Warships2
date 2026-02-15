"""Preset/new-game flow helpers extracted from controller."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from warships.app.ui_state import PresetRowView, TextPromptView
from warships.core.models import FleetPlacement, ShipPlacement
from warships.presets.service import PresetService


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
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("Skipping invalid preset '%s': %s", name, exc)
                continue
            rows.append(PresetRowView(name=name, placements=list(fleet.ships)))
        names = [row.name for row in rows]
        next_selected = selected_preset if selected_preset in names else None
        max_scroll = max(0, len(names) - visible_rows)
        next_scroll = min(scroll, max_scroll)
        return RefreshRowsResult(rows=rows, selected_preset=next_selected, scroll=next_scroll)

    @staticmethod
    def visible_new_game_preset_names(rows: list[PresetRowView], scroll: int, visible_rows: int) -> list[str]:
        names = [row.name for row in rows]
        return names[scroll : scroll + visible_rows]

    @staticmethod
    def can_scroll_down(rows: list[PresetRowView], scroll: int, visible_rows: int) -> bool:
        return scroll + visible_rows < len(rows)

    @staticmethod
    def select_new_game_preset(preset_service: PresetService, name: str) -> SelectPresetResult:
        try:
            fleet = preset_service.load_preset(name)
        except Exception as exc:  # pylint: disable=broad-exception-caught
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
    def open_prompt(title: str, initial_value: str, mode: str) -> TextPromptView:
        if mode == "save":
            confirm = "prompt_confirm_save"
        elif mode == "rename":
            confirm = "prompt_confirm_rename"
        else:
            confirm = "prompt_confirm_overwrite"
        return TextPromptView(
            title=title,
            value=initial_value,
            confirm_button_id=confirm,
            cancel_button_id="prompt_cancel",
        )

    @staticmethod
    def sync_prompt(prompt: TextPromptView, value: str) -> TextPromptView:
        return TextPromptView(
            title=prompt.title,
            value=value,
            confirm_button_id=prompt.confirm_button_id,
            cancel_button_id=prompt.cancel_button_id,
        )

