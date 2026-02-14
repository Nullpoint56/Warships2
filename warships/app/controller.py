"""Application controller for state transitions and game flow."""

from __future__ import annotations

import logging
import random

from warships.ai.hunt_target import HuntTargetAI
from warships.app.events import BoardCellPressed, ButtonPressed
from warships.app.state_machine import AppState
from warships.app.ui_state import AppUIState
from warships.core.board import BoardState
from warships.core.fleet import random_fleet, validate_fleet
from warships.core.models import Coord, FleetPlacement, Orientation, ShipPlacement, ShipType, ShotResult, Turn
from warships.core.rules import GameSession, ai_fire, create_session, player_fire
from warships.presets.service import PresetService
from warships.ui.overlays import buttons_for_state

_SHIP_ORDER = [
    ShipType.CARRIER,
    ShipType.BATTLESHIP,
    ShipType.CRUISER,
    ShipType.SUBMARINE,
    ShipType.DESTROYER,
]

logger = logging.getLogger(__name__)


class GameController:
    """Handles app events and owns game/session state."""

    def __init__(self, preset_service: PresetService, rng: random.Random, debug_ui: bool = False) -> None:
        self._preset_service = preset_service
        self._rng = rng
        self._debug_ui = debug_ui

        self._state = AppState.MAIN_MENU
        self._status = "Menu: New Game, Load Preset, Quit."
        self._placements: list[ShipPlacement] = []
        self._placement_orientation = Orientation.HORIZONTAL
        self._session: GameSession | None = None
        self._ai: HuntTargetAI | None = None
        self._is_closing = False

        self._has_presets = bool(self._preset_service.list_presets())
        self._placement_ready = False
        self._buttons = buttons_for_state(
            self._state,
            placement_ready=self._placement_ready,
            has_presets=self._has_presets,
        )
        self._announce_state()

    def ui_state(self) -> AppUIState:
        """Return current view-ready state."""
        return AppUIState(
            state=self._state,
            status=self._status,
            buttons=self._buttons,
            placements=list(self._placements),
            placement_orientation=self._placement_orientation,
            session=self._session,
            ship_order=list(_SHIP_ORDER),
            is_closing=self._is_closing,
        )

    def handle_button(self, event: ButtonPressed) -> bool:
        """Process button event. Returns whether UI changed."""
        button_id = event.button_id
        if button_id == "new_game":
            self._state = AppState.PLACEMENT_EDIT
            self._placements = []
            self._placement_orientation = Orientation.HORIZONTAL
            self._status = "Placement: click player board to place ships in order. Rotate toggles direction."
            self._refresh_placement_ready()
            self._refresh_buttons()
            self._announce_state()
            return True
        if button_id == "load_preset":
            return self._load_preset_into_placement()
        if button_id == "quit":
            self._is_closing = True
            return True
        if button_id == "rotate":
            self._placement_orientation = (
                Orientation.VERTICAL if self._placement_orientation is Orientation.HORIZONTAL else Orientation.HORIZONTAL
            )
            self._status = f"Placement orientation: {self._placement_orientation.value}."
            return True
        if button_id == "randomize":
            self._placements = random_fleet(self._rng).ships
            self._status = "Placement randomized."
            self._refresh_placement_ready()
            self._refresh_buttons()
            return True
        if button_id == "save_preset":
            return self._save_current_preset()
        if button_id == "start_battle":
            return self._start_battle()
        if button_id == "back_to_menu":
            self._state = AppState.MAIN_MENU
            self._status = "Menu: New Game, Load Preset, Quit."
            self._refresh_buttons()
            self._announce_state()
            return True
        if button_id == "menu_from_battle":
            self._state = AppState.MAIN_MENU
            self._session = None
            self._ai = None
            self._status = "Returned to menu."
            self._refresh_buttons()
            self._announce_state()
            return True
        if button_id == "play_again":
            self._state = AppState.PLACEMENT_EDIT
            self._session = None
            self._ai = None
            self._status = "Placement: prepare new fleet."
            self._refresh_placement_ready()
            self._refresh_buttons()
            self._announce_state()
            return True
        return False

    def handle_board_click(self, event: BoardCellPressed) -> bool:
        """Process board click event. Returns whether UI changed."""
        if self._state is AppState.PLACEMENT_EDIT and not event.is_ai_board:
            return self._handle_placement_click(event.coord)
        if self._state is AppState.BATTLE and event.is_ai_board:
            return self._handle_player_shot(event.coord)
        return False

    def _handle_placement_click(self, coord: Coord) -> bool:
        if len(self._placements) >= len(_SHIP_ORDER):
            self._status = "All ships already placed. Start battle or randomize."
            return True

        ship_type = _SHIP_ORDER[len(self._placements)]
        candidate = ShipPlacement(ship_type=ship_type, bow=coord, orientation=self._placement_orientation)
        trial = FleetPlacement(ships=[*self._placements, candidate])
        valid, _ = _validate_partial_fleet(trial)
        if not valid:
            self._status = f"Invalid placement for {ship_type.value} at ({coord.row}, {coord.col})."
            return True

        self._placements.append(candidate)
        if len(self._placements) == len(_SHIP_ORDER):
            self._status = "Fleet complete. Press Start Battle."
        else:
            next_ship = _SHIP_ORDER[len(self._placements)]
            self._status = f"Placed {ship_type.value}. Next: {next_ship.value}."
        self._refresh_placement_ready()
        self._refresh_buttons()
        return True

    def _handle_player_shot(self, coord: Coord) -> bool:
        if self._session is None or self._session.winner is not None:
            return False
        if self._session.turn is not Turn.PLAYER:
            return False

        result = player_fire(self._session, coord)
        if result is ShotResult.REPEAT:
            self._status = "Cell already fired. Choose another."
            return True
        if result is ShotResult.INVALID:
            return False

        self._status = self._session.last_message
        if self._session.winner:
            self._state = AppState.RESULT
            self._status = "Result: You win."
            self._refresh_buttons()
            self._announce_state()
            return True

        if self._session.turn is Turn.AI:
            self._run_ai_turn()
        return True

    def _run_ai_turn(self) -> None:
        if self._session is None or self._ai is None:
            return
        for _ in range(500):
            coord = self._ai.choose_shot()
            result = ai_fire(self._session, coord)
            if result in (ShotResult.INVALID, ShotResult.REPEAT):
                continue
            self._ai.notify_result(coord, result)
            self._status = self._session.last_message
            if self._session.winner:
                self._state = AppState.RESULT
                self._status = "Result: AI wins."
                self._refresh_buttons()
                self._announce_state()
            break

    def _start_battle(self) -> bool:
        fleet = FleetPlacement(ships=list(self._placements))
        valid, reason = validate_fleet(fleet)
        if not valid:
            self._status = f"Cannot start battle: {reason}"
            return True
        self._session = create_session(player_fleet=fleet, ai_fleet=random_fleet(self._rng))
        self._ai = HuntTargetAI(self._rng)
        self._state = AppState.BATTLE
        self._status = "Battle started. Click enemy board to fire."
        self._refresh_buttons()
        self._announce_state()
        return True

    def _save_current_preset(self) -> bool:
        fleet = FleetPlacement(ships=list(self._placements))
        valid, reason = validate_fleet(fleet)
        if not valid:
            self._status = f"Cannot save preset: {reason}"
            return True
        self._preset_service.save_preset("last_setup", fleet)
        self._has_presets = True
        self._refresh_buttons()
        self._status = "Preset saved as last_setup."
        return True

    def _load_preset_into_placement(self) -> bool:
        names = self._preset_service.list_presets()
        if not names:
            self._status = "No presets available."
            return True
        chosen = "last_setup" if "last_setup" in names else names[0]
        fleet = self._preset_service.load_preset(chosen)
        self._placements = list(fleet.ships)
        self._state = AppState.PLACEMENT_EDIT
        self._status = f"Loaded preset '{chosen}'."
        self._refresh_placement_ready()
        self._refresh_buttons()
        self._announce_state()
        return True

    def _refresh_placement_ready(self) -> None:
        if len(self._placements) != len(_SHIP_ORDER):
            self._placement_ready = False
        else:
            self._placement_ready = bool(validate_fleet(FleetPlacement(ships=list(self._placements)))[0])

    def _refresh_buttons(self) -> None:
        self._buttons = buttons_for_state(
            self._state,
            placement_ready=self._placement_ready,
            has_presets=self._has_presets,
        )

    def _announce_state(self) -> None:
        if self._state is AppState.MAIN_MENU:
            logger.info("state_main_menu")
        elif self._state is AppState.PLACEMENT_EDIT:
            logger.info("state_placement_edit order=%s", ",".join(s.value for s in _SHIP_ORDER))
        elif self._state is AppState.BATTLE:
            logger.info("state_battle")
        elif self._state is AppState.RESULT:
            logger.info("state_result")
        if self._debug_ui:
            logger.debug("ui_state state=%s buttons=%s", self._state.name, [b.id for b in self._buttons])


def _validate_partial_fleet(fleet: FleetPlacement) -> tuple[bool, str]:
    board = BoardState()
    seen: set[ShipType] = set()
    for idx, placement in enumerate(fleet.ships, start=1):
        if placement.ship_type in seen:
            return False, "Duplicate ship type."
        seen.add(placement.ship_type)
        if not board.can_place(placement):
            return False, "Invalid placement."
        board.place_ship(idx, placement)
    return True, ""
