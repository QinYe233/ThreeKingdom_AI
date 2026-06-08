"""
外交系统模块

实现三国博弈中的外交交互逻辑，包括消息发送、同盟形成与破裂、
背叛处理、宣战与停战、关系衰减、记忆衰减，以及士燮招降特殊机制。

外交系统通过关键词匹配来识别AI外交消息的意图（结盟、断交、招降等），
并通过记忆系统让AI记住历史事件，影响后续决策。

主要功能：
- 消息发送与意图识别
- 同盟形成（双方互发结盟消息）
- 背叛处理（攻击盟友触发背叛机制）
- 宣战与停战
- 关系衰减（信任和仇怨随时间消退）
- 记忆衰减（记忆强度随时间降低）
- 士燮招降（吴国对交州士燮的特殊招降机制）
"""
import uuid
import random
from datetime import datetime
from typing import Optional

from ..models import (
    GameState, Relation, DiplomaticMessage, Memory, MemoryImpact, MemoryEmotion,
    CountryMemory,
)


class DiplomacySystem:
    """外交系统，管理国家间的外交关系和交互。

    处理消息发送、同盟形成/破裂、背叛、宣战、停战等外交行为，
    以及关系和记忆的衰减机制。通过关键词匹配识别AI消息意图。
    """

    def send_message(
        self,
        state: GameState,
        from_country: str,
        to_country: str,
        content: str,
        visibility: str = "private",
    ) -> dict:
        """发送外交消息，并根据内容识别外交意图。

        通过关键词匹配识别以下意图：
        - 结盟意图：消息包含"结盟"或"同盟"
        - 断交意图：消息包含"断交"或"解盟"，立即执行断盟
        - 招降意图：吴→士燮的消息包含"归附/归顺/招降/劝降/归降"，触发招降流程

        Args:
            state: 游戏状态
            from_country: 发送方国家名
            to_country: 接收方国家名
            content: 消息内容
            visibility: 消息可见性，"private"（仅双方可见）或"public"（公开）

        Returns:
            包含message_sent（是否发送成功）、message_id（消息ID）、
            以及可能的alliance_intent/alliance_broken/surrender_attempt/surrender_result的字典

        Side Effects:
            - 向state.diplomatic_messages追加新消息
            - 断交时修改relation.is_allied和trust
            - 招降成功时修改士燮区块的所有权和守军
        """
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

        # 关键词列表，用于识别外交意图
        alliance_keywords = ["结盟", "同盟"]
        surrender_keywords = ["归附", "归顺", "招降", "劝降", "归降"]
        break_keywords = ["断交", "解盟"]

        result = {"message_sent": True, "message_id": msg.id}

        # 检测结盟意图
        for kw in alliance_keywords:
            if kw in content:
                result["alliance_intent"] = True
                break

        # 检测断交意图，立即执行断盟
        for kw in break_keywords:
            if kw in content:
                self._break_alliance(state, from_country, to_country)
                result["alliance_broken"] = True
                break

        # 检测招降意图（仅吴→士燮方向有效）
        for kw in surrender_keywords:
            if to_country == "士燮" and from_country == "吴":
                result["surrender_attempt"] = True
                result["surrender_result"] = self._attempt_jiaozhi_surrender(state, from_country, content)

        return result

    def process_alliance_check(self, state: GameState) -> list[dict]:
        """检查是否形成新的同盟关系。

        同盟形成条件：
        1. 双方在最近3回合内互发了包含结盟关键词的公开消息
        2. 消息中没有否定词（"不"/"否"/"拒"/"绝"）

        这确保了同盟需要双方同意，且任一方拒绝都不会形成同盟。

        Args:
            state: 游戏状态

        Returns:
            本回合新形成的同盟事件列表
        """
        events = []
        # 只检查最近3回合的消息
        recent_messages = [m for m in state.diplomatic_messages if state.round - m.round <= 3]

        # 按国家对分组收集公开消息
        country_pairs = {}
        for msg in recent_messages:
            if msg.visibility == "public":
                key = tuple(sorted([msg.from_country, msg.to_country]))
                if key not in country_pairs:
                    country_pairs[key] = {"messages": [], "has_negation": False}
                country_pairs[key]["messages"].append(msg)

                # 检测否定词，表示拒绝结盟
                negation_words = ["不", "否", "拒", "绝"]
                for nw in negation_words:
                    if nw in msg.content:
                        country_pairs[key]["has_negation"] = True

        for pair, data in country_pairs.items():
            # 有否定词则不形成同盟
            if data["has_negation"]:
                continue

            # 检查是否有结盟意图
            alliance_keywords = ["结盟", "同盟"]
            has_alliance_intent = False
            for msg in data["messages"]:
                for kw in alliance_keywords:
                    if kw in msg.content:
                        has_alliance_intent = True
                        break

            if has_alliance_intent:
                # 双方都必须发送过消息（双向同意）
                both_sent = len(set(m.from_country for m in data["messages"])) >= 2
                if both_sent:
                    result = self._form_alliance(state, pair[0], pair[1])
                    if result:
                        events.append(result)

        return events

    def _form_alliance(self, state: GameState, country_a: str, country_b: str) -> Optional[dict]:
        """形成同盟关系。

        同盟效果：
        - 设置relation.is_allied = True
        - 记录同盟形成回合
        - 双方信任+0.2
        - 为双方添加感恩记忆

        Args:
            state: 游戏状态
            country_a: 同盟方A
            country_b: 同盟方B

        Returns:
            同盟形成事件字典，已同盟或关系不存在时返回None
        """
        key = self.get_relation_key(country_a, country_b)
        relation = state.relations.get(key)
        if not relation:
            return None
        if relation.is_allied:
            return None

        relation.is_allied = True
        relation.alliance_round = state.round
        relation.trust = min(1.0, relation.trust + 0.2)

        # 为双方添加感恩记忆
        self._add_memory(state, country_a, f"与{country_b}结盟", MemoryImpact.MEDIUM, MemoryEmotion.GRATITUDE, country_b)
        self._add_memory(state, country_b, f"与{country_a}结盟", MemoryImpact.MEDIUM, MemoryEmotion.GRATITUDE, country_a)

        return {
            "event": "alliance_formed",
            "country_a": country_a,
            "country_b": country_b,
        }

    def _break_alliance(self, state: GameState, country_a: str, country_b: str) -> None:
        """解除同盟关系。

        断盟效果：
        - 设置relation.is_allied = False
        - 信任-0.1

        注意：断盟的惩罚比背叛轻得多，背叛会清零信任并大幅增加仇怨。

        Args:
            state: 游戏状态
            country_a: 一方国家名
            country_b: 另一方国家名
        """
        key = self.get_relation_key(country_a, country_b)
        relation = state.relations.get(key)
        if relation and relation.is_allied:
            relation.is_allied = False
            relation.trust = max(0, relation.trust - 0.1)

    def process_betrayal(self, state: GameState, attacker: str, defender: str) -> dict:
        """处理背叛事件（攻击盟友）。

        背叛是最严重的外交行为，效果：
        - 解除同盟
        - 信任归零
        - 仇怨+0.7
        - 进入交战状态
        - 为双方添加愤怒记忆
        - 记录攻击方最后背叛回合

        Args:
            state: 游戏状态
            attacker: 背叛方（攻击方）
            defender: 被背叛方（防守方）

        Returns:
            包含event/attacker/defender/was_allied的字典
        """
        key = self.get_relation_key(attacker, defender)
        relation = state.relations.get(key)
        if not relation:
            return {"error": "No relation found"}

        was_allied = relation.is_allied
        relation.is_allied = False
        relation.trust = 0.0
        relation.grudge = min(1.0, relation.grudge + 0.7)
        relation.at_war = True

        # 为双方添加愤怒记忆
        self._add_memory(state, defender, f"{attacker}背刺", MemoryImpact.HIGH, MemoryEmotion.ANGER, attacker)
        self._add_memory(state, attacker, f"背刺{defender}", MemoryImpact.HIGH, MemoryEmotion.ANGER, defender)

        # 记录攻击方最后背叛回合，用于冷却期计算
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
        """处理宣战事件。

        如果攻击方与防守方是盟友，自动转为背叛处理。
        否则：
        - 信任归零
        - 仇怨+0.5
        - 进入交战状态
        - 为防守方添加愤怒记忆

        Args:
            state: 游戏状态
            attacker: 宣战方
            defender: 被宣战方

        Returns:
            包含event/attacker/defender的字典，盟友间宣战时返回背叛事件
        """
        key = self.get_relation_key(attacker, defender)
        relation = state.relations.get(key)
        if not relation:
            # 关系不存在时创建新关系
            key = self.get_relation_key(attacker, defender)
            relation = Relation(country_a=attacker, country_b=defender)
            state.relations[key] = relation

        was_allied = relation.is_allied
        if was_allied:
            # 盟友间宣战视为背叛
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
        """处理停战事件。

        停战效果：
        - 退出交战状态
        - 信任+0.1
        - 双方秩序+3、士气+5（和平恢复）

        Args:
            state: 游戏状态
            country_a: 一方国家名
            country_b: 另一方国家名

        Returns:
            包含event/country_a/country_b的字典
        """
        key = self.get_relation_key(country_a, country_b)
        relation = state.relations.get(key)
        if not relation:
            return {"error": "No relation found"}

        relation.at_war = False
        relation.trust = min(1.0, relation.trust + 0.1)

        # 停战恢复秩序和士气
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
        """衰减外交关系值。

        每回合执行：
        - 非交战状态下，信任-0.05（信任需要维护）
        - 仇怨-0.05（时间冲淡仇恨）

        Args:
            state: 游戏状态

        Side Effects:
            - 修改所有relation的trust和grudge值
        """
        for key, relation in state.relations.items():
            if not relation.at_war:
                relation.trust = max(0, relation.trust - 0.05)
            relation.grudge = max(0, relation.grudge - 0.05)

    def decay_memories(self, state: GameState) -> None:
        """衰减国家记忆。

        每回合执行：
        - 每条记忆的current_value减少其decay值
        - current_value低于0.2的记忆被移除（遗忘）
        - 保留记忆数量上限为5条，只保留最重要的

        Args:
            state: 游戏状态

        Side Effects:
            - 修改/删除country_memories中的记忆
        """
        for country_name, cm in state.country_memories.items():
            to_remove = []
            for memory in cm.memories:
                memory.current_value = max(0, memory.current_value - memory.decay)
                # 记忆强度过低时遗忘
                if memory.current_value < 0.2:
                    to_remove.append(memory)
            for m in to_remove:
                cm.memories.remove(m)
            # 记忆上限5条，保留最重要的
            if len(cm.memories) > 5:
                cm.memories.sort(key=lambda m: m.current_value, reverse=True)
                cm.memories = cm.memories[:5]

    def _attempt_jiaozhi_surrender(self, state: GameState, from_country: str, content: str) -> dict:
        """尝试招降士燮（交州特殊机制）。

        仅吴国可对士燮发起招降。招降条件：
        - 士燮仍有区块存在
        - 吴-士燮关系信任>=0.6
        - 双方未处于交战状态

        招降概率：
        - 基础概率60%
        - 吴国秩序>70时，每10点秩序额外+5%概率，上限80%

        招降成功效果：
        - 士燮所有区块归吴，守军减半
        - 吴国秩序+8

        Args:
            state: 游戏状态
            from_country: 发起方（应为"吴"）
            content: 消息内容（未使用，但保留接口一致性）

        Returns:
            包含success（是否成功）和reason/blocks_gained的字典
        """
        shi_xie_blocks = [b for b in state.blocks.values() if b.owner == "士燮"]
        if not shi_xie_blocks:
            return {"success": False, "reason": "士燮已不存在"}

        # 查找吴-士燮关系
        relation = None
        for key, rel in state.relations.items():
            if "吴" in (rel.country_a, rel.country_b) and "士燮" in (rel.country_a, rel.country_b):
                relation = rel
                break

        if not relation or relation.trust < 0.6:
            return {"success": False, "reason": "信任不足"}

        if relation.at_war:
            return {"success": False, "reason": "处于交战状态"}

        # 计算招降概率
        wu_country = state.countries.get("吴")
        base_prob = 0.6
        # 吴国秩序高时增加招降概率
        if wu_country and wu_country.order > 70:
            bonus = int((wu_country.order - 70) / 10) * 0.05
            base_prob = min(0.8, base_prob + bonus)

        if random.random() < base_prob:
            # 招降成功：士燮所有区块归吴，守军减半
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
        """为国家添加外交记忆。

        记忆用于AI决策时参考历史事件，影响对其他国家的态度。
        每条记忆包含：发生回合、事件描述、影响程度、情感类型、目标国家、
        衰减率和当前强度。

        Args:
            state: 游戏状态
            country_name: 记忆所属国家
            event: 事件描述
            impact: 影响程度（HIGH/MEDIUM/LOW）
            emotion: 情感类型（ANGER/FEAR/GRATITUDE/GRIEF）
            target: 事件目标国家

        Side Effects:
            - 向country_memories添加新记忆
        """
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

    def get_relation_key(self, country_a: str, country_b: str) -> str:
        """生成两国关系的字典键。

        使用排序后的国家名拼接，确保A-B和B-A生成相同的键。

        Args:
            country_a: 国家A名称
            country_b: 国家B名称

        Returns:
            格式为"国家A-国家B"的关系键（按字典序排列）
        """
        pair = sorted([country_a, country_b])
        return f"{pair[0]}-{pair[1]}"
