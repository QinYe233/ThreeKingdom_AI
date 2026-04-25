import random
from typing import Optional
from ..models import GameState, Country, Block, StrategicGoal, ActionType
from ..core.constants import GAME_CONSTANTS, ACTION_COSTS


class AIDecisionEngine:
    def __init__(self, state: GameState):
        self.state = state

    def decide_actions(self, country_name: str, action_points: float = 6.0) -> list[dict]:
        country = self.state.countries.get(country_name)
        if not country or country.is_defeated:
            return []

        actions = []
        remaining_ap = action_points * 1000

        goal = self._evaluate_goal(country, country_name)
        country.goal = goal

        actions.extend(self._tax_action(country_name))

        if goal == StrategicGoal.STABILIZE:
            actions.extend(self._stabilize_actions(country_name, remaining_ap))
        elif goal == StrategicGoal.DEFEND:
            actions.extend(self._defend_actions(country_name, remaining_ap))
        elif goal == StrategicGoal.REVENGE:
            actions.extend(self._revenge_actions(country_name, remaining_ap))
        elif goal == StrategicGoal.DECLARE_EMPEROR:
            actions.extend(self._emperor_actions(country_name, remaining_ap))
        else:
            actions.extend(self._expand_actions(country_name, remaining_ap))

        return actions[:10]

    def _tax_action(self, country_name: str) -> list[dict]:
        country = self.state.countries.get(country_name)
        if not country:
            return []

        blocks = [b for b in self.state.blocks.values() if b.owner == country_name]
        avg_order = sum(b.order for b in blocks) / max(1, len(blocks))

        if country.gold < 800 or avg_order > 40:
            return [{
                "action_type": "tax",
                "country": country_name,
                "parameters": {},
                "priority": 10,
            }]
        return []

    def _evaluate_goal(self, country: Country, country_name: str) -> StrategicGoal:
        blocks = [b for b in self.state.blocks.values() if b.owner == country_name]
        blocks_count = len(blocks)

        low_order_count = sum(1 for b in blocks if b.order < 25)

        if country.order < 20 or low_order_count > 4:
            return StrategicGoal.STABILIZE

        if self._has_high_grudge(country_name):
            return StrategicGoal.REVENGE

        if blocks_count >= GAME_CONSTANTS["EMPEROR_REQUIRED_BLOCKS"]:
            if self._controls_historical_capital(country_name):
                return StrategicGoal.DECLARE_EMPEROR

        if country.morale < 30:
            return StrategicGoal.DEFEND

        return StrategicGoal.EXPAND

    def _has_high_grudge(self, country_name: str) -> bool:
        for key, rel in self.state.relations.items():
            if country_name in (rel.country_a, rel.country_b) and rel.grudge >= 0.6:
                return True
        return False

    def _controls_historical_capital(self, country_name: str) -> bool:
        historical = {
            "魏": ["许昌", "洛阳"],
            "蜀": ["成都", "长安"],
            "吴": ["建业", "武昌"],
        }
        for cap in historical.get(country_name, []):
            block = self.state.blocks.get(cap)
            if block and block.owner == country_name:
                return True
        return False

    def _get_enemy_from_grudge(self, country_name: str) -> Optional[str]:
        for key, rel in self.state.relations.items():
            if country_name in (rel.country_a, rel.country_b) and rel.grudge >= 0.6:
                return rel.country_b if rel.country_a == country_name else rel.country_a
        return None

    def _should_declare_war(self, country_name: str, target: str) -> bool:
        from ..core import DiplomacySystem
        dip = DiplomacySystem()
        rel_key = dip._get_relation_key(country_name, target)
        relation = self.state.relations.get(rel_key)
        if not relation:
            return False
        if relation.at_war:
            return False
        if relation.is_allied:
            return False

        country = self.state.countries.get(country_name)
        target_country = self.state.countries.get(target)
        if not country or not target_country:
            return False

        my_blocks = [b for b in self.state.blocks.values() if b.owner == country_name]
        my_garrison = sum(b.garrison for b in my_blocks)
        target_blocks = [b for b in self.state.blocks.values() if b.owner == target]
        target_garrison = sum(b.garrison for b in target_blocks)

        if my_garrison > target_garrison * 1.3 and country.morale > 40:
            return True
        if country.gold > 1500 and my_garrison > 2000:
            return True
        return False

    def _stabilize_actions(self, country_name: str, ap: int) -> list[dict]:
        actions = []
        country = self.state.countries[country_name]

        attack_cost = ACTION_COSTS.get("attack", 1000)
        max_attacks = int(ap * 1000 / attack_cost) if attack_cost > 0 else 6
        attacks_planned = 0

        if country.gold >= 300:
            low_order_blocks = [
                b for b in self.state.blocks.values()
                if b.owner == country_name and b.order < 60 and b.develop_count < 3 and b.supply_connected
            ]
            if low_order_blocks:
                target = max(low_order_blocks, key=lambda b: 60 - b.order)
                actions.append({
                    "action_type": "develop",
                    "country": country_name,
                    "parameters": {"block": target.name},
                    "priority": 9,
                })

        if country.gold >= 150:
            blocks = [b for b in self.state.blocks.values() if b.owner == country_name]
            for block in blocks:
                if block.manpower_pool >= 10 and not block.recently_conquered:
                    if self.state.round - block.last_recruit_round >= 2:
                        actions.append({
                            "action_type": "recruit",
                            "country": country_name,
                            "parameters": {"block": block.name},
                            "priority": 7,
                        })
                        break

        border_blocks = self._get_border_blocks(country_name)
        for block in border_blocks:
            for neighbor_name in block.neighbors:
                neighbor = self.state.blocks.get(neighbor_name)
                if neighbor and neighbor.owner not in [country_name, "neutral"] and neighbor.garrison < block.garrison * 0.5:
                    if attacks_planned >= max_attacks:
                        break
                    if block.garrison >= 150:
                        troops = max(int(block.garrison * 0.4), 100)
                        actions.append({
                            "action_type": "attack",
                            "country": country_name,
                            "parameters": {"from": block.name, "to": neighbor.name, "troops": troops},
                            "priority": 6,
                        })
                        attacks_planned += 1

        return actions

    def _defend_actions(self, country_name: str, ap: int) -> list[dict]:
        actions = []

        move_cost = ACTION_COSTS.get("move", 500)
        max_moves = int(ap * 1000 / move_cost) if move_cost > 0 else 12
        moves_planned = 0

        border_blocks = self._get_border_blocks(country_name)
        for block in border_blocks:
            if moves_planned >= max_moves:
                break
            if block.garrison < 200:
                safe_blocks = [
                    b for b in self.state.blocks.values()
                    if b.owner == country_name and b.garrison > 300 and b.name not in [bb.name for bb in border_blocks]
                ]
                if safe_blocks:
                    source = max(safe_blocks, key=lambda b: b.garrison)
                    troops = min(source.garrison - 100, 200)
                    if troops > 0:
                        actions.append({
                            "action_type": "move",
                            "country": country_name,
                            "parameters": {"from": source.name, "to": block.name, "troops": troops},
                            "priority": 9,
                        })
                        moves_planned += 1

        country = self.state.countries[country_name]
        if country.gold >= 150:
            recruit_blocks = [
                b for b in self.state.blocks.values()
                if b.owner == country_name and b.manpower_pool >= 20 and not block.recently_conquered
            ]
            if recruit_blocks:
                target = max(recruit_blocks, key=lambda b: b.manpower_pool)
                actions.append({
                    "action_type": "recruit",
                    "country": country_name,
                    "parameters": {"block": target.name},
                    "priority": 6,
                })

        remaining_ap = ap - moves_planned * move_cost

        neutral_targets = self._find_attack_targets(country_name, "neutral")
        if neutral_targets and remaining_ap >= 1000:
            attacker, target = neutral_targets[0]
            if attacker.garrison >= 150:
                troops = max(int(attacker.garrison * 0.4), 100)
                actions.append({
                    "action_type": "attack",
                    "country": country_name,
                    "parameters": {"from": attacker.name, "to": target.name, "troops": troops},
                    "priority": 5,
                })

        return actions

    def _revenge_actions(self, country_name: str, ap: int) -> list[dict]:
        actions = []
        enemy = self._get_enemy_from_grudge(country_name)

        if not enemy:
            return self._expand_actions(country_name, ap)

        attack_cost = ACTION_COSTS.get("attack", 1000)
        max_attacks = int(ap * 1000 / attack_cost) if attack_cost > 0 else 6
        attacks_planned = 0

        enemy_border_blocks = []
        my_blocks = [b for b in self.state.blocks.values() if b.owner == country_name]
        for block in my_blocks:
            for neighbor_name in block.neighbors:
                neighbor = self.state.blocks.get(neighbor_name)
                if neighbor and neighbor.owner == enemy:
                    enemy_border_blocks.append((block, neighbor))

        if enemy_border_blocks:
            attackable = [
                (attacker, target) for attacker, target in enemy_border_blocks
                if attacker.garrison >= 150
            ]

            attackable.sort(key=lambda x: x[0].garrison - x[1].garrison * 0.5)

            for attacker, target in attackable:
                if attacks_planned >= max_attacks:
                    break
                troops = max(int(attacker.garrison * 0.5), 100)
                actions.append({
                    "action_type": "attack",
                    "country": country_name,
                    "parameters": {"from": attacker.name, "to": target.name, "troops": troops},
                    "priority": 7,
                })
                attacks_planned += 1

        return actions

    def _emperor_actions(self, country_name: str, ap: int) -> list[dict]:
        actions = []
        country = self.state.countries[country_name]

        if not country.has_declared_emperor:
            actions.append({
                "action_type": "declare_emperor",
                "country": country_name,
                "parameters": {},
                "priority": 10,
            })

        actions.extend(self._defend_actions(country_name, ap))
        return actions

    def _find_attack_targets(self, country_name: str, target_owner: str = None) -> list[tuple[Block, Block]]:
        border_blocks = self._get_border_blocks(country_name)
        targets = []

        for block in border_blocks:
            for neighbor_name in block.neighbors:
                neighbor = self.state.blocks.get(neighbor_name)
                if not neighbor or neighbor.owner == country_name:
                    continue

                if target_owner and neighbor.owner != target_owner:
                    continue

                if neighbor.owner != "neutral" and not self._is_at_war(country_name, neighbor.owner):
                    if not self._should_declare_war(country_name, neighbor.owner):
                        continue

                targets.append((block, neighbor))

        targets.sort(key=lambda x: x[1].garrison)
        return targets

    def _expand_actions(self, country_name: str, ap: int) -> list[dict]:
        actions = []
        country = self.state.countries[country_name]

        my_blocks = [b for b in self.state.blocks.values() if b.owner == country_name]
        total_garrison = sum(b.garrison for b in my_blocks)

        attack_cost = ACTION_COSTS.get("attack", 1000)
        recruit_cost = ACTION_COSTS.get("recruit", 500)
        develop_cost = ACTION_COSTS.get("develop", 800)

        max_attacks = int(ap * 1000 / attack_cost) if attack_cost > 0 else 6

        neutral_targets = self._find_attack_targets(country_name, "neutral")
        attacks_planned = 0

        if neutral_targets:
            for attacker, target in neutral_targets:
                if attacks_planned >= max_attacks:
                    break
                if attacker.garrison >= 120:
                    troops = max(int(attacker.garrison * 0.35), 80)
                    actions.append({
                        "action_type": "attack",
                        "country": country_name,
                        "parameters": {"from": attacker.name, "to": target.name, "troops": troops},
                        "priority": 8,
                    })
                    attacks_planned += 1

        faction_targets = self._find_attack_targets(country_name)
        faction_targets = [(a, t) for a, t in faction_targets if t.owner != "neutral"]

        if faction_targets and attacks_planned < max_attacks:
            for attacker, target in faction_targets:
                if attacks_planned >= max_attacks:
                    break
                if attacker.garrison >= 200:
                    troops = max(int(attacker.garrison * 0.4), 120)
                    actions.append({
                        "action_type": "attack",
                        "country": country_name,
                        "parameters": {"from": attacker.name, "to": target.name, "troops": troops},
                        "priority": 7,
                    })
                    attacks_planned += 1

        remaining_ap = ap - attacks_planned * attack_cost

        if country.gold >= 150 and remaining_ap >= recruit_cost:
            recruit_blocks = [
                b for b in my_blocks
                if b.manpower_pool >= 20 and not block.recently_conquered
                and self.state.round - b.last_recruit_round >= 2
            ]
            if recruit_blocks:
                target = max(recruit_blocks, key=lambda b: b.manpower_pool)
                actions.append({
                    "action_type": "recruit",
                    "country": country_name,
                    "parameters": {"block": target.name},
                    "priority": 6,
                })
                remaining_ap -= recruit_cost

        if country.gold >= 300 and remaining_ap >= develop_cost:
            develop_blocks = [
                b for b in my_blocks
                if b.develop_count < 3 and b.supply_connected and not block.recently_conquered
            ]
            if develop_blocks:
                target = max(develop_blocks, key=lambda b: b.base_manpower)
                actions.append({
                    "action_type": "develop",
                    "country": country_name,
                    "parameters": {"block": target.name},
                    "priority": 5,
                })

        return actions

    def _get_border_blocks(self, country_name: str) -> list[Block]:
        border = []
        for block in self.state.blocks.values():
            if block.owner != country_name:
                continue
            for neighbor_name in block.neighbors:
                neighbor = self.state.blocks.get(neighbor_name)
                if neighbor and neighbor.owner != country_name:
                    border.append(block)
                    break
        return border

    def _is_at_war(self, country_a: str, country_b: str) -> bool:
        for key, rel in self.state.relations.items():
            if country_a in (rel.country_a, rel.country_b) and country_b in (rel.country_a, rel.country_b):
                return rel.at_war
        return False
