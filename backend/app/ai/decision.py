import re
from typing import Optional
from ..models import GameState, Country, Block, StrategicGoal
from ..core.constants import GAME_CONSTANTS, ACTION_COSTS, HISTORICAL_CAPITALS

MAX_ATTACKS_PER_TURN = 2


class AIDecisionEngine:
    def __init__(self, state: GameState):
        self.state = state

    def _fuzzy_find_block(self, name: str, owner: str = None) -> Optional[Block]:
        block = self.state.blocks.get(name)
        if block and (owner is None or block.owner == owner):
            return block

        for bname, b in self.state.blocks.items():
            if name in bname or bname in name:
                if owner is None or b.owner == owner:
                    return b

        for bname, b in self.state.blocks.items():
            cleaned = name.replace("郡", "").replace("县", "").replace("城", "").replace("州", "")
            bcleaned = bname.replace("郡", "").replace("县", "").replace("城", "").replace("州", "")
            if cleaned and bcleaned and (cleaned in bcleaned or bcleaned in cleaned):
                if owner is None or b.owner == owner:
                    return b

        return None

    def decide_actions(self, country_name: str, action_points: float = 6.0) -> list[dict]:
        country = self.state.countries.get(country_name)
        if not country or country.is_defeated:
            return []

        goal = self._evaluate_goal(country, country_name)
        country.goal = goal

        actions = []

        if country.gold < 800 or self._avg_order(country_name) < 40:
            actions.append({
                "action_type": "tax",
                "country": country_name,
                "parameters": {},
                "priority": 10,
            })

        if goal == StrategicGoal.STABILIZE:
            actions.extend(self._stabilize_actions(country_name))
        elif goal == StrategicGoal.DEFEND:
            actions.extend(self._defend_actions(country_name))
        elif goal == StrategicGoal.REVENGE:
            actions.extend(self._revenge_actions(country_name))
        else:
            actions.extend(self._expand_actions(country_name))

        return self._filter_by_ap(actions, action_points)

    def parse_llm_actions(self, country_name: str, content: str, action_points: float = 6.0) -> list[dict]:
        country = self.state.countries.get(country_name)
        if not country or country.is_defeated:
            return []

        actions = []
        attack_count = 0
        seen_blocks = set()

        if re.search(r'征税', content):
            actions.append({
                "action_type": "tax",
                "country": country_name,
                "parameters": {},
                "priority": 10,
            })

        for from_b, to_b, troops in self._parse_attacks(content, country_name):
            if attack_count >= MAX_ATTACKS_PER_TURN:
                break
            actions.append({
                "action_type": "attack",
                "country": country_name,
                "parameters": {"from": from_b, "to": to_b, "troops": troops},
                "priority": 8,
            })
            attack_count += 1

        for block_name, troops in self._parse_recruits(content, country_name):
            if block_name not in seen_blocks:
                actions.append({
                    "action_type": "recruit",
                    "country": country_name,
                    "parameters": {"block": block_name, "troops": troops},
                    "priority": 6,
                })
                seen_blocks.add(block_name)

        for block_name in self._parse_develops(content, country_name):
            if block_name not in seen_blocks:
                actions.append({
                    "action_type": "develop",
                    "country": country_name,
                    "parameters": {"block": block_name},
                    "priority": 5,
                })
                seen_blocks.add(block_name)

        for from_b, to_b, troops in self._parse_moves(content, country_name):
            actions.append({
                "action_type": "move",
                "country": country_name,
                "parameters": {"from": from_b, "to": to_b, "troops": troops},
                "priority": 4,
            })

        for to_b, troops in self._parse_harass(content, country_name):
            actions.append({
                "action_type": "harass",
                "country": country_name,
                "parameters": {"to": to_b, "troops": troops},
                "priority": 3,
            })

        return self._filter_by_ap(actions, action_points)

    def hybrid_decide(self, country_name: str, llm_content: str, action_points: float = 6.0) -> list[dict]:
        country = self.state.countries.get(country_name)
        if not country or country.is_defeated:
            return []

        llm_actions = self.parse_llm_actions(country_name, llm_content, action_points)

        llm_action_types = set()
        for a in llm_actions:
            llm_action_types.add(a["action_type"])

        rule_actions = self.decide_actions(country_name, action_points)

        MIN_ACTION_DIVERSITY = 2
        if len(llm_action_types) >= MIN_ACTION_DIVERSITY and len(llm_actions) >= 2:
            return llm_actions

        supplemented = list(llm_actions)
        supplemented_types = set(llm_action_types)

        for action in rule_actions:
            atype = action["action_type"]
            if atype in supplemented_types:
                continue

            ap_used = sum(ACTION_COSTS.get(a["action_type"], 0) / 1000 for a in supplemented)
            cost = ACTION_COSTS.get(atype, 0) / 1000
            if ap_used + cost <= action_points:
                supplemented.append(action)
                supplemented_types.add(atype)

        if not supplemented:
            return rule_actions

        return supplemented

    def _parse_attacks(self, content: str, country_name: str) -> list[tuple[str, str, int]]:
        results = []
        my_blocks = {b.name: b for b in self.state.blocks.values() if b.owner == country_name}

        patterns = [
            re.compile(r'进攻[：:]*\s*从[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[出发攻][击打]?\s*[至到→]\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[，,]?\s*(?:出兵|派|领|率|带)?\s*(\d+)', re.IGNORECASE),
            re.compile(r'进攻[：:]*\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[→至到]\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[，,]?\s*(?:出兵|派|领|率|带)?\s*(\d+)', re.IGNORECASE),
            re.compile(r'(?:进攻|攻打|攻击|出兵)[：:]*\s*(.+?)\s*[，,]\s*(?:从|自)\s*(.+?)\s*(?:出兵|派|领|率|带)?\s*(\d+)', re.IGNORECASE),
            re.compile(r'从[「【\[(]?\s*(.+?)\s*[」】\])]??\s*(?:出兵|进攻|攻打|攻击)\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[，,]?\s*(?:出兵|派|领|率|带)?\s*(\d+)', re.IGNORECASE),
            re.compile(r'(?:进攻|攻打|攻击|出兵)[：:]*\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[，,]?\s*(?:出兵|派|领|率|带)?\s*(\d+)\s*(?:兵|人)?\s*[，,]?\s*(?:从|自)\s*(.+)', re.IGNORECASE),
            re.compile(r'(?:进攻|攻打|攻击)[：:]*\s*(.+?)\s*[，,]\s*从\s*(.+?)\s*[，,]?\s*(\d+)', re.IGNORECASE),
            re.compile(r'从\s*(.+?)\s*(?:进攻|攻打|攻击|出兵)\s*(.+?)\s*[，,]?\s*(\d+)', re.IGNORECASE),
        ]

        for pattern in patterns:
            for match in pattern.finditer(content):
                groups = [g.strip() if g else "" for g in match.groups()]
                if len(groups) < 3:
                    continue

                if pattern == patterns[2] or pattern == patterns[5]:
                    to_name, from_name, troops_str = groups[0], groups[1], groups[2]
                elif pattern == patterns[4]:
                    to_name, troops_str, from_name = groups[0], groups[1], groups[2]
                elif pattern == patterns[6]:
                    from_name, to_name, troops_str = groups[0], groups[1], groups[2]
                else:
                    from_name, to_name, troops_str = groups[0], groups[1], groups[2]

                from_block = self._fuzzy_find_block(from_name, country_name)
                to_block = self._fuzzy_find_block(to_name)
                troops = int(troops_str) if troops_str.isdigit() else 0

                if not from_block or not to_block:
                    continue
                if from_block.owner != country_name:
                    continue
                if to_block.owner == country_name:
                    continue
                if to_block.name not in from_block.neighbors:
                    continue
                if troops <= 0:
                    troops = max(int(from_block.garrison * 0.35), 80)
                troops = min(troops, from_block.garrison)
                if troops < 50:
                    continue

                if to_block.owner not in ["neutral", country_name] and not self._is_at_war(country_name, to_block.owner):
                    if not self._should_declare_war(country_name, to_block.owner):
                        continue

                results.append((from_block.name, to_block.name, troops))

        if not results:
            simple_patterns = [
                re.compile(r'(?:进攻|攻打|攻击|出兵|伐)[：:]*\s*[「【\[(]?\s*(.+?)\s*[」】\])]?', re.IGNORECASE),
                re.compile(r'(?:取|夺|克|下|破)[「【\[(]?\s*(.+?)\s*[」】\])]?', re.IGNORECASE),
            ]
            for pattern in simple_patterns:
                for match in pattern.finditer(content):
                    to_name = match.group(1).strip().rstrip('，,。.！!？?')
                    to_block = self._fuzzy_find_block(to_name)
                    if not to_block or to_block.owner == country_name:
                        continue

                    best_from = None
                    best_garrison = 0
                    for bname, block in my_blocks.items():
                        if to_name in block.neighbors and block.garrison > best_garrison:
                            best_from = bname
                            best_garrison = block.garrison

                    if best_from and best_garrison >= 80:
                        troops = max(int(best_garrison * 0.35), 80)
                        if to_block.owner not in ["neutral", country_name] and not self._is_at_war(country_name, to_block.owner):
                            if not self._should_declare_war(country_name, to_block.owner):
                                continue
                        results.append((best_from, to_block.name, troops))

        return results

    def _parse_recruits(self, content: str, country_name: str) -> list[tuple[str, int]]:
        results = []
        patterns = [
            re.compile(r'征兵[：:]*\s*(?:在|于)?\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[，,]?\s*(?:征|招|募)?\s*(\d+)', re.IGNORECASE),
            re.compile(r'(?:在|于)\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*征兵\s*[，,]?\s*(\d+)', re.IGNORECASE),
            re.compile(r'征兵[：:]*\s*[「【\[(]?\s*(.+?)\s*[」】\])]??', re.IGNORECASE),
            re.compile(r'(?:招募|募兵|招兵)[：:]*\s*(?:在|于)?\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[，,]?\s*(\d+)?', re.IGNORECASE),
        ]

        seen = set()
        for pattern in patterns:
            for match in pattern.finditer(content):
                block_name = match.group(1).strip().rstrip('，,。.！?')
                if block_name in seen:
                    continue

                block = self._fuzzy_find_block(block_name, country_name)
                if not block:
                    continue
                if block.manpower_pool < 5:
                    continue

                troops_str = match.group(2).strip() if match.lastindex and match.lastindex >= 2 and match.group(2) else ""
                troops = int(troops_str) if troops_str and troops_str.isdigit() else min(block.manpower_pool, 200)
                troops = min(troops, block.manpower_pool)
                if troops <= 0:
                    continue

                results.append((block.name, troops))
                seen.add(block.name)

        if not results and re.search(r'征兵', content):
            my_blocks = [b for b in self.state.blocks.values() if b.owner == country_name and b.manpower_pool >= 10]
            if my_blocks:
                target = max(my_blocks, key=lambda b: b.manpower_pool)
                troops = min(target.manpower_pool, 200)
                results.append((target.name, troops))

        return results

    def _parse_develops(self, content: str, country_name: str) -> list[str]:
        results = []
        patterns = [
            re.compile(r'发展[：:]*\s*(?:在|于)?\s*[「【\[(]?\s*(.+?)\s*[」】\])]??', re.IGNORECASE),
            re.compile(r'(?:在|于)\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*发展', re.IGNORECASE),
            re.compile(r'(?:建设|开发|经营)[：:]*\s*(?:在|于)?\s*[「【\[(]?\s*(.+?)\s*[」】\])]??', re.IGNORECASE),
        ]

        seen = set()
        for pattern in patterns:
            for match in pattern.finditer(content):
                block_name = match.group(1).strip().rstrip('，,。.！?')
                if block_name in seen:
                    continue
                block = self._fuzzy_find_block(block_name, country_name)
                if not block:
                    continue
                if block.develop_count >= 3:
                    continue
                results.append(block.name)
                seen.add(block.name)

        return results

    def _parse_moves(self, content: str, country_name: str) -> list[tuple[str, str, int]]:
        results = []
        patterns = [
            re.compile(r'调兵[：:]*\s*从[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[至到→]\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[，,]?\s*(\d+)', re.IGNORECASE),
            re.compile(r'(?:从|自)\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*调兵\s*[至到→]\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[，,]?\s*(\d+)', re.IGNORECASE),
            re.compile(r'(?:调|移|派|遣)兵[：:]*\s*(.+?)\s*[→至到]\s*(.+?)\s*[，,]?\s*(\d+)', re.IGNORECASE),
        ]

        for pattern in patterns:
            for match in pattern.finditer(content):
                from_name, to_name, troops_str = match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
                from_block = self._fuzzy_find_block(from_name, country_name)
                to_block = self._fuzzy_find_block(to_name, country_name)
                troops = int(troops_str) if troops_str.isdigit() else 0
                if not from_block or not to_block:
                    continue
                if from_block.owner != country_name or to_block.owner != country_name:
                    continue
                if to_block.name not in from_block.neighbors:
                    continue
                if troops <= 0:
                    troops = max(int(from_block.garrison * 0.3), 50)
                troops = min(troops, from_block.garrison - 50)
                if troops <= 0:
                    continue
                results.append((from_block.name, to_block.name, troops))

        return results

    def _parse_harass(self, content: str, country_name: str) -> list[tuple[str, int]]:
        results = []
        patterns = [
            re.compile(r'骚扰[：:]*\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[，,]?\s*(\d+)?', re.IGNORECASE),
            re.compile(r'(?:袭扰|偷袭|劫掠|骚扰)[：:]*\s*(.+?)\s*[，,]?\s*(\d+)?', re.IGNORECASE),
        ]

        for pattern in patterns:
            for match in pattern.finditer(content):
                to_name = match.group(1).strip().rstrip('，,。.！?')
                to_block = self._fuzzy_find_block(to_name)
                if not to_block or to_block.owner == country_name:
                    continue

                my_border = [b for b in self.state.blocks.values()
                             if b.owner == country_name and to_block.name in b.neighbors]
                if not my_border:
                    continue

                best = max(my_border, key=lambda b: b.garrison)
                troops_str = match.group(2).strip() if match.lastindex and match.lastindex >= 2 and match.group(2) else ""
                troops = int(troops_str) if troops_str and troops_str.isdigit() else min(best.garrison // 3, 300)
                troops = max(50, min(troops, 500, best.garrison - 50))
                if troops >= 50:
                    results.append((to_block.name, troops))

        return results

    def _filter_by_ap(self, actions: list[dict], total_ap: float) -> list[dict]:
        filtered = []
        remaining = total_ap
        attack_count = 0

        tax_actions = [a for a in actions if a["action_type"] == "tax"]
        attack_actions = [a for a in actions if a["action_type"] == "attack"]
        recruit_actions = [a for a in actions if a["action_type"] == "recruit"]
        develop_actions = [a for a in actions if a["action_type"] == "develop"]
        move_actions = [a for a in actions if a["action_type"] == "move"]
        harass_actions = [a for a in actions if a["action_type"] == "harass"]
        other_actions = [a for a in actions if a["action_type"] not in ("tax", "attack", "recruit", "develop", "move", "harass")]

        for action in tax_actions:
            cost = ACTION_COSTS.get(action["action_type"], 0) / 1000
            if remaining >= cost:
                filtered.append(action)
                remaining -= cost

        for action in recruit_actions[:2]:
            cost = ACTION_COSTS.get(action["action_type"], 0) / 1000
            if remaining >= cost:
                filtered.append(action)
                remaining -= cost

        for action in develop_actions[:2]:
            cost = ACTION_COSTS.get(action["action_type"], 0) / 1000
            if remaining >= cost:
                filtered.append(action)
                remaining -= cost

        for action in attack_actions:
            if attack_count >= MAX_ATTACKS_PER_TURN:
                break
            cost = ACTION_COSTS.get(action["action_type"], 0) / 1000
            if remaining >= cost:
                filtered.append(action)
                remaining -= cost
                attack_count += 1

        for action in move_actions[:2]:
            cost = ACTION_COSTS.get(action["action_type"], 0) / 1000
            if remaining >= cost:
                filtered.append(action)
                remaining -= cost

        for action in harass_actions[:1]:
            cost = ACTION_COSTS.get(action["action_type"], 0) / 1000
            if remaining >= cost:
                filtered.append(action)
                remaining -= cost

        for action in other_actions:
            cost = ACTION_COSTS.get(action["action_type"], 0) / 1000
            if remaining >= cost:
                filtered.append(action)
                remaining -= cost

        return filtered[:8]

    def _avg_order(self, country_name: str) -> float:
        blocks = [b for b in self.state.blocks.values() if b.owner == country_name]
        if not blocks:
            return 50
        return sum(b.order for b in blocks) / len(blocks)

    def _evaluate_goal(self, country: Country, country_name: str) -> StrategicGoal:
        blocks = [b for b in self.state.blocks.values() if b.owner == country_name]
        blocks_count = len(blocks)
        low_order_count = sum(1 for b in blocks if b.order < 30)

        if country.order < 40 or low_order_count > 2:
            return StrategicGoal.STABILIZE
        if self._has_high_grudge(country_name):
            return StrategicGoal.REVENGE
        if blocks_count >= GAME_CONSTANTS.get("EMPEROR_REQUIRED_BLOCKS", 45):
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
        historical = HISTORICAL_CAPITALS
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
        for key, rel in self.state.relations.items():
            if country_name in (rel.country_a, rel.country_b) and target in (rel.country_a, rel.country_b):
                if rel.at_war:
                    return True
                if rel.is_allied:
                    return False

        country = self.state.countries.get(country_name)
        target_country = self.state.countries.get(target)
        if not country or not target_country:
            return False

        my_garrison = sum(b.garrison for b in self.state.blocks.values() if b.owner == country_name)
        target_garrison = sum(b.garrison for b in self.state.blocks.values() if b.owner == target)

        if my_garrison > target_garrison * 1.3 and country.morale > 40:
            return True
        if country.gold > 1500 and my_garrison > 2000:
            return True
        return False

    def _is_at_war(self, country_a: str, country_b: str) -> bool:
        for key, rel in self.state.relations.items():
            if country_a in (rel.country_a, rel.country_b) and country_b in (rel.country_a, rel.country_b):
                return rel.at_war
        return False

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
                if neighbor.owner not in ["neutral"] and not self._is_at_war(country_name, neighbor.owner):
                    if not self._should_declare_war(country_name, neighbor.owner):
                        continue
                targets.append((block, neighbor))
        targets.sort(key=lambda x: x[1].garrison)
        return targets

    def _stabilize_actions(self, country_name: str) -> list[dict]:
        actions = []
        country = self.state.countries[country_name]

        if country.gold >= 300:
            low_order_blocks = [
                b for b in self.state.blocks.values()
                if b.owner == country_name and b.order < 60 and b.develop_count < 3 and b.supply_connected
            ]
            if low_order_blocks:
                target = max(low_order_blocks, key=lambda b: 60 - b.order)
                actions.append({"action_type": "develop", "country": country_name, "parameters": {"block": target.name}, "priority": 9})

        if country.gold >= 150:
            for block in self.state.blocks.values():
                if block.owner == country_name and block.manpower_pool >= 10 and not block.recently_conquered:
                    if self.state.round - block.last_recruit_round >= 2:
                        actions.append({"action_type": "recruit", "country": country_name, "parameters": {"block": block.name}, "priority": 7})
                        break

        neutral_targets = self._find_attack_targets(country_name, "neutral")
        if neutral_targets:
            attacker, target = neutral_targets[0]
            if attacker.garrison >= 150:
                troops = max(int(attacker.garrison * 0.35), 80)
                actions.append({"action_type": "attack", "country": country_name, "parameters": {"from": attacker.name, "to": target.name, "troops": troops}, "priority": 5})

        return actions

    def _defend_actions(self, country_name: str) -> list[dict]:
        actions = []
        country = self.state.countries[country_name]

        border_blocks = self._get_border_blocks(country_name)
        for block in border_blocks:
            if block.garrison < 200:
                safe_blocks = [
                    b for b in self.state.blocks.values()
                    if b.owner == country_name and b.garrison > 300 and b.name not in [bb.name for bb in border_blocks]
                ]
                if safe_blocks:
                    source = max(safe_blocks, key=lambda b: b.garrison)
                    troops = min(source.garrison - 100, 200)
                    if troops > 0:
                        actions.append({"action_type": "move", "country": country_name, "parameters": {"from": source.name, "to": block.name, "troops": troops}, "priority": 9})
                        break

        if country.gold >= 150:
            recruit_blocks = [b for b in self.state.blocks.values() if b.owner == country_name and b.manpower_pool >= 20 and not b.recently_conquered]
            if recruit_blocks:
                target = max(recruit_blocks, key=lambda b: b.manpower_pool)
                actions.append({"action_type": "recruit", "country": country_name, "parameters": {"block": target.name}, "priority": 6})

        neutral_targets = self._find_attack_targets(country_name, "neutral")
        if neutral_targets:
            attacker, target = neutral_targets[0]
            if attacker.garrison >= 150:
                troops = max(int(attacker.garrison * 0.35), 80)
                actions.append({"action_type": "attack", "country": country_name, "parameters": {"from": attacker.name, "to": target.name, "troops": troops}, "priority": 5})

        return actions

    def _revenge_actions(self, country_name: str) -> list[dict]:
        actions = []
        country = self.state.countries[country_name]
        enemy = self._get_enemy_from_grudge(country_name)
        if not enemy:
            return self._expand_actions(country_name)

        if country.gold >= 150:
            recruit_blocks = [b for b in self.state.blocks.values() if b.owner == country_name and b.manpower_pool >= 20 and not b.recently_conquered]
            if recruit_blocks:
                target = max(recruit_blocks, key=lambda b: b.manpower_pool)
                actions.append({"action_type": "recruit", "country": country_name, "parameters": {"block": target.name}, "priority": 6})

        enemy_border_blocks = []
        for block in self.state.blocks.values():
            if block.owner != country_name:
                continue
            for neighbor_name in block.neighbors:
                neighbor = self.state.blocks.get(neighbor_name)
                if neighbor and neighbor.owner == enemy:
                    enemy_border_blocks.append((block, neighbor))

        if enemy_border_blocks:
            attackable = [(a, t) for a, t in enemy_border_blocks if a.garrison >= 150]
            attackable.sort(key=lambda x: x[0].garrison - x[1].garrison * 0.5)
            for attacker, target in attackable[:MAX_ATTACKS_PER_TURN]:
                troops = max(int(attacker.garrison * 0.5), 100)
                actions.append({"action_type": "attack", "country": country_name, "parameters": {"from": attacker.name, "to": target.name, "troops": troops}, "priority": 7})

        return actions

    def _expand_actions(self, country_name: str) -> list[dict]:
        actions = []
        country = self.state.countries[country_name]
        my_blocks = [b for b in self.state.blocks.values() if b.owner == country_name]

        if country.gold >= 150:
            recruit_blocks = [b for b in my_blocks if b.manpower_pool >= 20 and not b.recently_conquered and self.state.round - b.last_recruit_round >= 2]
            if recruit_blocks:
                target = max(recruit_blocks, key=lambda b: b.manpower_pool)
                actions.append({"action_type": "recruit", "country": country_name, "parameters": {"block": target.name}, "priority": 7})

        if country.gold >= 300:
            develop_blocks = [b for b in my_blocks if b.develop_count < 3 and b.supply_connected and not b.recently_conquered]
            if develop_blocks:
                target = max(develop_blocks, key=lambda b: b.base_manpower)
                actions.append({"action_type": "develop", "country": country_name, "parameters": {"block": target.name}, "priority": 6})

        neutral_targets = self._find_attack_targets(country_name, "neutral")
        if neutral_targets:
            for attacker, target in neutral_targets[:MAX_ATTACKS_PER_TURN]:
                if attacker.garrison >= 120:
                    troops = max(int(attacker.garrison * 0.35), 80)
                    actions.append({"action_type": "attack", "country": country_name, "parameters": {"from": attacker.name, "to": target.name, "troops": troops}, "priority": 8})

        faction_targets = [(a, t) for a, t in self._find_attack_targets(country_name) if t.owner not in ["neutral"]]
        if faction_targets:
            for attacker, target in faction_targets[:1]:
                if attacker.garrison >= 200:
                    troops = max(int(attacker.garrison * 0.4), 120)
                    actions.append({"action_type": "attack", "country": country_name, "parameters": {"from": attacker.name, "to": target.name, "troops": troops}, "priority": 7})

        return actions
