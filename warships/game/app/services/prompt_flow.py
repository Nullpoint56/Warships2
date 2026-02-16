"""Prompt confirmation flow helpers extracted from controller."""

from __future__ import annotations

from dataclasses import dataclass

from warships.game.app.ports.runtime_primitives import PromptInteractionOutcome, PromptState, PromptView
from warships.game.app.ports.runtime_services import (
    close_prompt as close_prompt_runtime,
    handle_prompt_button,
    handle_prompt_char,
    handle_prompt_key,
    open_prompt as open_prompt_runtime,
    sync_prompt as sync_prompt_runtime,
)
from warships.game.core.models import FleetPlacement, ShipPlacement
from warships.game.presets.service import PresetService


@dataclass(frozen=True, slots=True)
class PromptConfirmOutcome:
    """Result of confirming prompt input."""

    handled: bool
    status: str | None
    prompt: PromptView | None
    prompt_mode: str | None
    prompt_target: str | None
    prompt_buffer: str
    pending_save_name: str | None
    editing_preset_name: str | None
    switch_to_preset_manage: bool = False
    refresh_preset_rows: bool = False
    refresh_buttons: bool = False
    announce_state: bool = False


class PromptFlowService:
    """Pure prompt confirmation operations for controller orchestration."""

    @staticmethod
    def open_prompt(title: str, initial_value: str, mode: str, target: str | None = None) -> PromptState:
        if mode == "save":
            confirm = "prompt_confirm_save"
        elif mode == "rename":
            confirm = "prompt_confirm_rename"
        else:
            confirm = "prompt_confirm_overwrite"
        return open_prompt_runtime(
            title=title,
            initial_value=initial_value,
            confirm_button_id=confirm,
            cancel_button_id="prompt_cancel",
            mode=mode,
            target=target,
        )

    @staticmethod
    def close_prompt() -> PromptState:
        return close_prompt_runtime()

    @staticmethod
    def sync_prompt(state: PromptState, value: str) -> PromptState:
        return sync_prompt_runtime(state, value)

    @staticmethod
    def handle_button(state: PromptState, button_id: str) -> PromptInteractionOutcome:
        return handle_prompt_button(
            state,
            button_id,
            confirm_button_ids={"prompt_confirm_save", "prompt_confirm_rename", "prompt_confirm_overwrite"},
        )

    @staticmethod
    def handle_key(state: PromptState, key: str) -> PromptInteractionOutcome:
        return handle_prompt_key(state, key)

    @staticmethod
    def handle_char(state: PromptState, ch: str, max_len: int = 32) -> PromptInteractionOutcome:
        return handle_prompt_char(state, ch, max_len=max_len)

    @staticmethod
    def confirm(
        *,
        mode: str | None,
        value: str,
        prompt_target: str | None,
        pending_save_name: str | None,
        editing_preset_name: str | None,
        preset_names: list[str],
        placements: list[ShipPlacement],
        preset_service: PresetService,
    ) -> PromptConfirmOutcome:
        stripped = value.strip()
        if not stripped:
            return PromptConfirmOutcome(
                handled=True,
                status="Name cannot be empty.",
                prompt=None,
                prompt_mode=mode,
                prompt_target=prompt_target,
                prompt_buffer=value,
                pending_save_name=pending_save_name,
                editing_preset_name=editing_preset_name,
            )

        if mode == "save":
            fleet = FleetPlacement(ships=list(placements))
            exists = stripped in preset_names
            if exists and stripped != (editing_preset_name or ""):
                prompt_state = PromptFlowService.open_prompt("Preset exists. Overwrite?", stripped, mode="overwrite")
                return PromptConfirmOutcome(
                    handled=True,
                    status=None,
                    prompt=prompt_state.prompt,
                    prompt_mode=prompt_state.mode,
                    prompt_target=prompt_state.target,
                    prompt_buffer=prompt_state.buffer,
                    pending_save_name=stripped,
                    editing_preset_name=editing_preset_name,
                    refresh_buttons=True,
                )
            try:
                preset_service.save_preset(stripped, fleet)
            except ValueError as exc:
                return PromptConfirmOutcome(
                    handled=True,
                    status=f"Save failed: {exc}",
                    prompt=None,
                    prompt_mode=mode,
                    prompt_target=prompt_target,
                    prompt_buffer=value,
                    pending_save_name=pending_save_name,
                    editing_preset_name=editing_preset_name,
                )
            return PromptConfirmOutcome(
                handled=True,
                status=f"Saved preset '{stripped}'.",
                prompt=None,
                prompt_mode=None,
                prompt_target=None,
                prompt_buffer="",
                pending_save_name=None,
                editing_preset_name=stripped,
                switch_to_preset_manage=True,
                refresh_preset_rows=True,
                refresh_buttons=True,
                announce_state=True,
            )

        if mode == "overwrite":
            target = pending_save_name or stripped
            try:
                preset_service.save_preset(target, FleetPlacement(ships=list(placements)))
            except ValueError as exc:
                return PromptConfirmOutcome(
                    handled=True,
                    status=f"Save failed: {exc}",
                    prompt=None,
                    prompt_mode=mode,
                    prompt_target=prompt_target,
                    prompt_buffer=value,
                    pending_save_name=pending_save_name,
                    editing_preset_name=editing_preset_name,
                )
            return PromptConfirmOutcome(
                handled=True,
                status=f"Overwrote preset '{target}'.",
                prompt=None,
                prompt_mode=None,
                prompt_target=None,
                prompt_buffer="",
                pending_save_name=None,
                editing_preset_name=target,
                switch_to_preset_manage=True,
                refresh_preset_rows=True,
                refresh_buttons=True,
                announce_state=True,
            )

        if mode == "rename" and prompt_target:
            try:
                preset_service.rename_preset(prompt_target, stripped)
            except (ValueError, FileNotFoundError) as exc:
                return PromptConfirmOutcome(
                    handled=True,
                    status=f"Rename failed: {exc}",
                    prompt=None,
                    prompt_mode=mode,
                    prompt_target=prompt_target,
                    prompt_buffer=value,
                    pending_save_name=pending_save_name,
                    editing_preset_name=editing_preset_name,
                )
            return PromptConfirmOutcome(
                handled=True,
                status=f"Renamed '{prompt_target}' to '{stripped}'.",
                prompt=None,
                prompt_mode=None,
                prompt_target=None,
                prompt_buffer="",
                pending_save_name=pending_save_name,
                editing_preset_name=editing_preset_name,
                refresh_preset_rows=True,
                refresh_buttons=True,
            )

        return PromptConfirmOutcome(
            handled=False,
            status=None,
            prompt=None,
            prompt_mode=mode,
            prompt_target=prompt_target,
            prompt_buffer=value,
            pending_save_name=pending_save_name,
            editing_preset_name=editing_preset_name,
        )

