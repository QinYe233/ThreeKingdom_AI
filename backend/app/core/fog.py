from typing import Optional

from ..models import (
    GameState, Block, BlockVisibility, WinRateLabel, Country,
)
from ..core.constants import GAME_CONSTANTS


class FogSystem:
    def get_visible_state(self, state: GameState, country_name: str) -> dict:
        fog_phase = self._get_fog_phase(state.round)
        owned_blocks = self._get_owned_blocks(state, country_name)
        adjacent_blocks = self._get_adjacent_blocks(state, owned_blocks)
        allied_blocks = self._get_allied_blocks(state, country_name)

        visible_blocks = {}
        for block_name, block in state.blocks.items():
            visibility = self._calculate_visibility(
                state, block_name, block, country_name,
                owned_blocks, adjacent_blocks, allied_blocks, fog_phase
            )
            visible_blocks[block_name] = visibility

        return {
            "country": country_name,
            "fog_phase": fog_phase,
            "visible_blocks": visible_blocks,
        }

    def _get_fog_phase(self, round_num: int) -> int:
        if round_num <= GAME_CONSTANTS["FOG_PHASE_1_END"]:
            return 1
        elif round_num <= GAME_CONSTANTS["FOG_PHASE_2_END"]:
            return 2
        else:
            return 3

    def _get_owned_blocks(self, state: GameState, country_name: str) -> set[str]:
        return {name for name, b in state.blocks.items() if b.owner == country_name}

    def _get_adjacent_blocks(self, state: GameState, owned: set[str]) -> set[str]:
        adjacent = set()
        for name in owned:
            block = state.blocks.get(name)
            if block:
                for neighbor in block.neighbors:
                    if neighbor not in owned:
                        adjacent.add(neighbor)
        return adjacent

    def _get_allied_blocks(self, state: GameState, country_name: str) -> set[str]:
        allies = set()
        for key, relation in state.relations.items():
            if relation.is_allied and country_name in (relation.country_a, relation.country_b):
                ally = relation.country_b if relation.country_a == country_name else relation.country_a
                allies.add(ally)

        allied_blocks = set()
        for name, block in state.blocks.items():
            if block.owner in allies:
                allied_blocks.add(name)
        return allied_blocks

    def _calculate_visibility(
        self,
        state: GameState,
        block_name: str,
        block: Block,
        country_name: str,
        owned: set[str],
        adjacent: set[str],
        allied_blocks: set[str],
        fog_phase: int,
    ) -> BlockVisibility:
        vis = BlockVisibility(name=block_name)

        if block_name in owned:
            vis.visible = True
            vis.owner = block.owner
            vis.garrison_estimate = block.garrison
            vis.order_range = (block.order, block.order)
            vis.morale_range = (block.morale, block.morale)
            vis.base_manpower = block.base_manpower
            return vis

        if block_name in adjacent:
            vis.visible = True
            vis.owner = block.owner
            if block.owner == "neutral":
                vis.garrison_estimate = block.garrison
                vis.order_range = (block.order, block.order)
                vis.morale_range = (block.morale, block.morale)
            elif block_name in allied_blocks:
                vis.garrison_estimate = block.garrison
                vis.order_range = (block.order, block.order)
                vis.morale_range = (block.morale, block.morale)
                vis.base_manpower = block.base_manpower
            else:
                vis.garrison_estimate = self._estimate_garrison(block.garrison)
                vis.order_range = self._value_to_range(block.order)
                vis.morale_range = self._value_to_range(block.morale)
            vis.win_rate_label = self._calculate_win_rate(state, country_name, block)
            return vis

        if block_name in allied_blocks:
            vis.visible = True
            vis.owner = block.owner
            if fog_phase >= 2:
                vis.garrison_estimate = self._estimate_garrison(block.garrison)
            else:
                vis.garrison_estimate = self._estimate_garrison_range(block.garrison)
            vis.order_range = self._value_to_range(block.order)
            vis.morale_range = self._value_to_range(block.morale)
            if fog_phase >= 2:
                vis.base_manpower = block.base_manpower
            return vis

        if fog_phase >= 3:
            vis.visible = True
            vis.owner = block.owner
            vis.garrison_estimate = self._estimate_garrison(block.garrison)
            vis.order_range = self._value_to_range(block.order)
            vis.morale_range = self._value_to_range(block.morale)
            return vis

        if fog_phase >= 2:
            vis.visible = True
            vis.owner = block.owner
            return vis

        vis.visible = False
        return vis

    def _estimate_garrison(self, actual: int) -> int:
        import random
        estimate = int(actual * 0.8)
        noise = int(estimate * random.uniform(-0.1, 0.1))
        return max(0, estimate + noise)

    def _estimate_garrison_range(self, actual: int) -> int:
        return self._estimate_garrison(actual)

    def _value_to_range(self, value: int) -> tuple[int, int]:
        if value >= 80:
            return (80, 100)
        elif value >= 50:
            return (50, 79)
        elif value >= 30:
            return (30, 49)
        else:
            return (0, 29)

    def _calculate_win_rate(
        self, state: GameState, country_name: str, target_block: Block
    ) -> WinRateLabel:
        country = state.countries.get(country_name)
        if not country:
            return WinRateLabel.UNKNOWN

        adjacent_owned = [
            n for n in target_block.neighbors
            if n in state.blocks and state.blocks[n].owner == country_name
        ]
        if not adjacent_owned:
            return WinRateLabel.UNKNOWN

        best_block = max(adjacent_owned, key=lambda n: state.blocks[n].garrison)
        attacker_troops = state.blocks[best_block].garrison

        attacker_power = attacker_troops * (1 + country.morale / 600)
        defender_power = target_block.garrison * (1 + 50 / 600) * 1.05

        if defender_power <= 0:
            return WinRateLabel.HIGH

        ratio = attacker_power / defender_power
        if ratio >= 1.5:
            return WinRateLabel.HIGH
        elif ratio >= 1.0:
            return WinRateLabel.MEDIUM
        else:
            return WinRateLabel.LOW
