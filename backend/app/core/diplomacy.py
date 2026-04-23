import uuid
from datetime import datetime
from typing import Optional

from ..models import (
    GameState, Relation, DiplomaticMessage, Memory, MemoryImpact, MemoryEmotion,
    CountryMemory,
)


class DiplomacySystem:
    def send_message(
        self,
        state: GameState,
        from_country: str,
        to_country: str,
        content: str,
        visibility: str = "private",
    ) -> dict:
        if from_country not in state.countries or to_country not in state.countries:
            return {"error": "Country not found"}

        msg = DiplomaticMessage(
            id=str(uuid.uuid4()),
            from_country=from_country,
            to_country=to_country,
            content=content,
            visibility=visibility,
            round=state.round,
            timestamp=datetime.now(),
        )
        state.diplomatic_messages.append(msg)

        alliance_keywords = ["结盟", "同盟"]
        surrender_keywords = ["归附", "归顺", "招降", "劝降", "归降"]
        break_keywords = ["断交", "解盟"]

        result = {"message_sent": True, "message_id": msg.id}

        for kw in alliance_keywords:
            if kw in content:
                result["alliance_intent"] = True
                break

        for kw in break_keywords:
            if kw in content:
                self._break_alliance(state, from_country, to_country)
                result["alliance_broken"] = True
                break

        for kw in surrender_keywords:
            if to_country == "士燮" and from_country == "吴":
                result["surrender_attempt"] = True
                result["surrender_result"] = self._attempt_jiaozhi_surrender(state, from_country, content)

        return result

    def process_alliance_check(self, state: GameState) -> list[dict]:
        events = []
        recent_messages = [m for m in state.diplomatic_messages if state.round - m.round <= 3]

        country_pairs = {}
        for msg in recent_messages:
            if msg.visibility == "public":
                key = tuple(sorted([msg.from_country, msg.to_country]))
                if key not in country_pairs:
                    country_pairs[key] = {"messages": [], "has_negation": False}
                country_pairs[key]["messages"].append(msg)

                negation_words = ["不", "否", "拒", "绝"]
                for nw in negation_words:
                    if nw in msg.content:
                        country_pairs[key]["has_negation"] = True

        for pair, data in country_pairs.items():
            if data["has_negation"]:
                continue

            alliance_keywords = ["结盟", "同盟"]
            has_alliance_intent = False
            for msg in data["messages"]:
                for kw in alliance_keywords:
                    if kw in msg.content:
                        has_alliance_intent = True
                        break

            if has_alliance_intent:
                both_sent = len(set(m.from_country for m in data["messages"])) >= 2
                if both_sent:
                    result = self._form_alliance(state, pair[0], pair[1])
                    if result:
                        events.append(result)

        return events

    def _form_alliance(self, state: GameState, country_a: str, country_b: str) -> Optional[dict]:
        key = self._get_relation_key(country_a, country_b)
        relation = state.relations.get(key)
        if not relation:
            return None
        if relation.is_allied:
            return None

        relation.is_allied = True
        relation.alliance_round = state.round
        relation.trust = min(1.0, relation.trust + 0.2)

        self._add_memory(state, country_a, f"与{country_b}结盟", MemoryImpact.MEDIUM, MemoryEmotion.GRATITUDE, country_b)
        self._add_memory(state, country_b, f"与{country_a}结盟", MemoryImpact.MEDIUM, MemoryEmotion.GRATITUDE, country_a)

        return {
            "event": "alliance_formed",
            "country_a": country_a,
            "country_b": country_b,
        }

    def _break_alliance(self, state: GameState, country_a: str, country_b: str) -> None:
        key = self._get_relation_key(country_a, country_b)
        relation = state.relations.get(key)
        if relation and relation.is_allied:
            relation.is_allied = False
            relation.trust = max(0, relation.trust - 0.1)

    def process_betrayal(self, state: GameState, attacker: str, defender: str) -> dict:
        key = self._get_relation_key(attacker, defender)
        relation = state.relations.get(key)
        if not relation:
            return {"error": "No relation found"}

        was_allied = relation.is_allied
        relation.is_allied = False
        relation.trust = 0.0
        relation.grudge = min(1.0, relation.grudge + 0.7)
        relation.at_war = True

        self._add_memory(state, defender, f"{attacker}背刺", MemoryImpact.HIGH, MemoryEmotion.ANGER, attacker)
        self._add_memory(state, attacker, f"背刺{defender}", MemoryImpact.HIGH, MemoryEmotion.ANGER, defender)

        attacker_country = state.countries.get(attacker)
        if attacker_country:
            attacker_country.last_betrayal_round = state.round

        return {
            "event": "betrayal",
            "attacker": attacker,
            "defender": defender,
            "was_allied": was_allied,
        }

    def process_attack_declaration(self, state: GameState, attacker: str, defender: str) -> dict:
        key = self._get_relation_key(attacker, defender)
        relation = state.relations.get(key)
        if not relation:
            key = self._get_relation_key(attacker, defender)
            relation = Relation(country_a=attacker, country_b=defender)
            state.relations[key] = relation

        was_allied = relation.is_allied
        if was_allied:
            return self.process_betrayal(state, attacker, defender)

        relation.trust = 0.0
        relation.grudge = min(1.0, relation.grudge + 0.5)
        relation.at_war = True

        self._add_memory(state, defender, f"{attacker}宣战", MemoryImpact.MEDIUM, MemoryEmotion.ANGER, attacker)

        return {
            "event": "war_declared",
            "attacker": attacker,
            "defender": defender,
        }

    def process_truce(self, state: GameState, country_a: str, country_b: str) -> dict:
        key = self._get_relation_key(country_a, country_b)
        relation = state.relations.get(key)
        if not relation:
            return {"error": "No relation found"}

        relation.at_war = False
        relation.trust = min(1.0, relation.trust + 0.1)

        country_a_obj = state.countries.get(country_a)
        country_b_obj = state.countries.get(country_b)
        if country_a_obj:
            country_a_obj.order = min(100, country_a_obj.order + 3)
            country_a_obj.morale = min(100, country_a_obj.morale + 5)
        if country_b_obj:
            country_b_obj.order = min(100, country_b_obj.order + 3)
            country_b_obj.morale = min(100, country_b_obj.morale + 5)

        return {
            "event": "truce",
            "country_a": country_a,
            "country_b": country_b,
        }

    def decay_relations(self, state: GameState) -> None:
        for key, relation in state.relations.items():
            if not relation.at_war:
                relation.trust = max(0, relation.trust - 0.05)
            relation.grudge = max(0, relation.grudge - 0.05)

    def decay_memories(self, state: GameState) -> None:
        for country_name, cm in state.country_memories.items():
            to_remove = []
            for memory in cm.memories:
                memory.current_value = max(0, memory.current_value - memory.decay)
                if memory.current_value < 0.2:
                    to_remove.append(memory)
            for m in to_remove:
                cm.memories.remove(m)
            if len(cm.memories) > 5:
                cm.memories.sort(key=lambda m: m.current_value, reverse=True)
                cm.memories = cm.memories[:5]

    def _attempt_jiaozhi_surrender(self, state: GameState, from_country: str, content: str) -> dict:
        shi_xie_blocks = [b for b in state.blocks.values() if b.owner == "士燮"]
        if not shi_xie_blocks:
            return {"success": False, "reason": "士燮已不存在"}

        relation = None
        for key, rel in state.relations.items():
            if "吴" in (rel.country_a, rel.country_b) and "士燮" in (rel.country_a, rel.country_b):
                relation = rel
                break

        if not relation or relation.trust < 0.6:
            return {"success": False, "reason": "信任不足"}

        if relation.at_war:
            return {"success": False, "reason": "处于交战状态"}

        wu_country = state.countries.get("吴")
        base_prob = 0.6
        if wu_country and wu_country.order > 70:
            bonus = int((wu_country.order - 70) / 10) * 0.05
            base_prob = min(0.8, base_prob + bonus)

        import random
        if random.random() < base_prob:
            for block in shi_xie_blocks:
                block.owner = "吴"
                block.garrison = int(block.garrison * 0.5)
            if wu_country:
                wu_country.order = min(100, wu_country.order + 8)
            return {"success": True, "blocks_gained": len(shi_xie_blocks)}
        else:
            return {"success": False, "reason": "招降失败"}

    def _add_memory(
        self,
        state: GameState,
        country_name: str,
        event: str,
        impact: MemoryImpact,
        emotion: MemoryEmotion,
        target: str,
    ) -> None:
        cm = state.country_memories.get(country_name)
        if not cm:
            cm = CountryMemory(country_name=country_name)
            state.country_memories[country_name] = cm

        memory = Memory(
            round=state.round,
            event=event,
            impact=impact,
            emotion=emotion,
            target=target,
        )
        cm.memories.append(memory)

    def _get_relation_key(self, country_a: str, country_b: str) -> str:
        pair = sorted([country_a, country_b])
        return f"{pair[0]}-{pair[1]}"
