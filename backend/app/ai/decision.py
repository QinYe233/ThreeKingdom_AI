"""
AI决策引擎模块

实现AI国家的自动决策逻辑，包括：
- 纯规则引擎决策（基于战略目标和局势评估）
- LLM输出解析（从自然语言文本中提取行动指令）
- 混合决策（结合LLM输出和规则引擎，互相补充）
- 行动点数管理和行动过滤
- 各战略目标（扩张/防御/稳定/复仇）的具体行动生成策略
"""
import re
import logging
from typing import Optional
from ..models import GameState, Country, Block, StrategicGoal
from ..core.constants import GAME_CONSTANTS, ACTION_COSTS, HISTORICAL_CAPITALS, SPECIAL_NEUTRAL_FORCE_NAMES

logger = logging.getLogger(__name__)

# 每回合最大进攻次数限制
MAX_ATTACKS_PER_TURN = 2
SPECIAL_NEUTRAL_FORCES = SPECIAL_NEUTRAL_FORCE_NAMES


class AIDecisionEngine:
    """
    AI决策引擎

    负责为AI国家生成行动决策。支持三种决策模式：
    1. 纯规则引擎（decide_actions）：基于战略目标和局势评估
    2. LLM输出解析（parse_llm_actions）：从自然语言中提取行动
    3. 混合决策（hybrid_decide）：结合LLM和规则引擎，互相补充
    """

    def __init__(self, state: GameState):
        """
        初始化AI决策引擎

        Args:
            state: 当前游戏状态
        """
        self.state = state

    def _fuzzy_find_block(self, name: str, owner: str = None) -> Optional[Block]:
        """
        模糊查找区块

        支持三种匹配方式（按优先级）：
        1. 精确匹配区块名称
        2. 子串包含匹配（如"洛阳"匹配"洛阳郡"）
        3. 去除行政区划后缀后的子串匹配（去除"郡""县""城""州"）

        Args:
            name: 区块名称（可能不精确）
            owner: 可选的所属国家过滤条件

        Returns:
            Optional[Block]: 匹配到的区块对象，未找到返回None
        """
        # 优先精确匹配
        block = self.state.blocks.get(name)
        if block and (owner is None or block.owner == owner):
            return block

        # 子串包含匹配（至少2个字符）
        if len(name) >= 2:
            for bname, b in self.state.blocks.items():
                if name in bname or bname in name:
                    if owner is None or b.owner == owner:
                        return b

        # 去除行政区划后缀后再匹配
        if len(name) >= 2:
            for bname, b in self.state.blocks.items():
                cleaned = name.replace("郡", "").replace("县", "").replace("城", "").replace("州", "")
                bcleaned = bname.replace("郡", "").replace("县", "").replace("城", "").replace("州", "")
                if cleaned and bcleaned and (cleaned in bcleaned or bcleaned in cleaned):
                    if owner is None or b.owner == owner:
                        return b

        return None

    def decide_actions(self, country_name: str, action_points: float = 6.0) -> list[dict]:
        """
        纯规则引擎决策

        根据当前局势评估战略目标，然后生成对应的行动列表。
        战略目标优先级：稳定 > 防御 > 复仇 > 扩张。

        Args:
            country_name: 国家名称
            action_points: 可用行动点数

        Returns:
            list[dict]: 行动列表，每个行动包含 action_type、country、parameters、priority
        """
        country = self.state.countries.get(country_name)
        if not country or country.is_defeated:
            return []

        # 评估并设置战略目标
        goal = self._evaluate_goal(country, country_name)
        country.goal = goal

        actions = []

        # 黄金不足或平均秩序过低时优先征税
        if country.gold < 800 or self._avg_order(country_name) < 40:
            actions.append({
                "action_type": "tax",
                "country": country_name,
                "parameters": {},
                "priority": 10,
            })

        # 根据战略目标生成行动
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
        """
        解析LLM输出为行动列表

        从LLM生成的自然语言文本中，使用正则表达式提取各种行动指令。
        支持解析的行动类型：征税、进攻、征兵、发展、调兵、骚扰。

        Args:
            country_name: 国家名称
            content: LLM生成的文本内容
            action_points: 可用行动点数

        Returns:
            list[dict]: 解析出的行动列表
        """
        country = self.state.countries.get(country_name)
        if not country or country.is_defeated:
            return []

        actions = []
        attack_count = 0
        seen_blocks = set()

        # 解析征税指令
        if re.search(r'征税', content):
            actions.append({
                "action_type": "tax",
                "country": country_name,
                "parameters": {},
                "priority": 10,
            })

        # 解析进攻指令（限制每回合最多2次进攻）
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

        # 解析征兵指令（同一区块不重复征兵）
        for block_name, troops in self._parse_recruits(content, country_name):
            if block_name not in seen_blocks:
                actions.append({
                    "action_type": "recruit",
                    "country": country_name,
                    "parameters": {"block": block_name, "troops": troops},
                    "priority": 6,
                })
                seen_blocks.add(block_name)

        # 解析发展指令（同一区块不重复发展）
        for block_name in self._parse_develops(content, country_name):
            if block_name not in seen_blocks:
                actions.append({
                    "action_type": "develop",
                    "country": country_name,
                    "parameters": {"block": block_name},
                    "priority": 5,
                })
                seen_blocks.add(block_name)

        # 解析调兵指令
        for from_b, to_b, troops in self._parse_moves(content, country_name):
            actions.append({
                "action_type": "move",
                "country": country_name,
                "parameters": {"from": from_b, "to": to_b, "troops": troops},
                "priority": 4,
            })

        # 解析骚扰指令
        for to_b, troops in self._parse_harass(content, country_name):
            actions.append({
                "action_type": "harass",
                "country": country_name,
                "parameters": {"to": to_b, "troops": troops},
                "priority": 3,
            })

        logger.info(f"[AI] {country_name} parse_llm_actions: raw actions={len(actions)}, types={set(a['action_type'] for a in actions)}")
        return self._filter_by_ap(actions, action_points)

    def hybrid_decide(self, country_name: str, llm_content: str, action_points: float = 6.0) -> list[dict]:
        """
        混合决策：结合LLM输出和规则引擎

        策略：
        1. 解析LLM输出，验证进攻和调兵目标的邻接关系
        2. 如果LLM行动类型多样性足够（>=2种）且数量>=2，直接使用LLM行动
        3. 否则，用规则引擎的行动补充LLM缺少的行动类型
        4. 如果LLM行动为空，完全使用规则引擎

        Args:
            country_name: 国家名称
            llm_content: LLM生成的文本内容
            action_points: 可用行动点数

        Returns:
            list[dict]: 最终行动列表
        """
        country = self.state.countries.get(country_name)
        if not country or country.is_defeated:
            return []

        llm_actions = self.parse_llm_actions(country_name, llm_content, action_points)

        # 验证LLM行动：检查进攻和调兵目标是否确实相邻
        validated_actions = []
        for action in llm_actions:
            atype = action["action_type"]
            params = action.get("parameters", {})

            if atype == "attack":
                from_name = params.get("from", "")
                to_name = params.get("to", "")
                from_block = self._fuzzy_find_block(from_name, country_name)
                to_block = self._fuzzy_find_block(to_name)
                if from_block and to_block and to_block.name in from_block.neighbors:
                    validated_actions.append(action)
                else:
                    logger.info(f"[AI] {country_name} hybrid_decide: removing invalid attack {from_name}->{to_name} (not neighbors)")

            elif atype == "move":
                from_name = params.get("from", "")
                to_name = params.get("to", "")
                from_block = self._fuzzy_find_block(from_name, country_name)
                to_block = self._fuzzy_find_block(to_name, country_name)
                if from_block and to_block and to_block.name in from_block.neighbors:
                    validated_actions.append(action)
                else:
                    logger.info(f"[AI] {country_name} hybrid_decide: removing invalid move {from_name}->{to_name} (not neighbors)")

            else:
                validated_actions.append(action)

        llm_actions = validated_actions

        # 统计LLM行动类型多样性
        llm_action_types = set()
        for a in llm_actions:
            llm_action_types.add(a["action_type"])

        rule_actions = self.decide_actions(country_name, action_points)

        logger.info(f"[AI] {country_name} hybrid_decide: LLM parsed {len(llm_actions)} actions, types={llm_action_types}")
        logger.info(f"[AI] {country_name} rule_actions: {len(rule_actions)} actions, types={set(a['action_type'] for a in rule_actions)}")

        # 如果LLM行动多样性足够，直接使用LLM结果
        MIN_ACTION_DIVERSITY = 2
        if len(llm_action_types) >= MIN_ACTION_DIVERSITY and len(llm_actions) >= 2:
            logger.info(f"[AI] {country_name} final: using LLM actions (sufficient diversity), {len(llm_actions)} actions, AP={action_points}")
            for a in llm_actions:
                logger.debug(f"[AI] {country_name} action: {a['action_type']} {a.get('parameters', {})} cost={ACTION_COSTS.get(a['action_type'], 0)/1000}")
            return llm_actions

        # LLM行动多样性不足，用规则引擎补充缺少的行动类型
        supplemented = list(llm_actions)
        supplemented_types = set(llm_action_types)

        for action in rule_actions:
            atype = action["action_type"]
            if atype in supplemented_types:
                continue

            # 检查补充后是否超出行动点数
            ap_used = sum(ACTION_COSTS.get(a["action_type"], 0) / 1000 for a in supplemented)
            cost = ACTION_COSTS.get(atype, 0) / 1000
            if ap_used + cost <= action_points:
                supplemented.append(action)
                supplemented_types.add(atype)

        if not supplemented:
            return rule_actions

        logger.info(f"[AI] {country_name} final: {len(supplemented)} actions, AP={action_points}")
        for a in supplemented:
            logger.debug(f"[AI] {country_name} action: {a['action_type']} {a.get('parameters', {})} cost={ACTION_COSTS.get(a['action_type'], 0)/1000}")

        return supplemented

    def _parse_attacks(self, content: str, country_name: str) -> list[tuple[str, str, int]]:
        """
        从文本中解析进攻指令

        支持多种中文表达格式，如：
        - 进攻：从「XX」出击至「YY」，出兵N
        - 攻打XX，从YY出兵N
        - 从XX出兵攻YY，N

        使用多组正则表达式覆盖不同的语序组合。

        Args:
            content: LLM生成的文本
            country_name: 国家名称

        Returns:
            list[tuple[str, str, int]]: (出发区块, 目标区块, 出兵数) 的列表
        """
        results = []
        my_blocks = {b.name: b for b in self.state.blocks.values() if b.owner == country_name}

        # 多组正则表达式，覆盖不同的语序组合
        # 格式：从XX出击至YY，出兵N
        pat_from_attack_to_troops = re.compile(r'进攻[：:]*\s*从[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[出发攻][击打]?\s*[至到→]\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[，,]?\s*(?:出兵|派|领|率|带)?\s*(\d+)', re.IGNORECASE)
        # 格式：进攻XX→YY，出兵N
        pat_attack_to_troops = re.compile(r'进攻[：:]*\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[→至到]\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[，,]?\s*(?:出兵|派|领|率|带)?\s*(\d+)', re.IGNORECASE)
        # 格式：进攻XX，从YY出兵N（目标在前）
        pat_target_from_troops = re.compile(r'(?:进攻|攻打|攻击|出兵)[：:]*\s*(.+?)\s*[，,]\s*(?:从|自)\s*(.+?)\s*(?:出兵|派|领|率|带)?\s*(\d+)', re.IGNORECASE)
        # 格式：从XX出兵攻YY，N
        pat_from_attack_target_troops = re.compile(r'从[「【\[(]?\s*(.+?)\s*[」】\])]??\s*(?:出兵|进攻|攻打|攻击)\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[，,]?\s*(?:出兵|派|领|率|带)?\s*(\d+)', re.IGNORECASE)
        # 格式：进攻XX，N兵，从YY（兵力在中间）
        pat_target_troops_from = re.compile(r'(?:进攻|攻打|攻击|出兵)[：:]*\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[，,]?\s*(?:出兵|派|领|率|带)?\s*(\d+)\s*(?:兵|人)?\s*[，,]?\s*(?:从|自)\s*(.+)', re.IGNORECASE)
        # 格式：进攻XX，从YY，N（简化版）
        pat_target_from_troops2 = re.compile(r'(?:进攻|攻打|攻击)[：:]*\s*(.+?)\s*[，,]\s*从\s*(.+?)\s*[，,]?\s*(\d+)', re.IGNORECASE)
        # 格式：从XX进攻YY，N（简化版）
        pat_from_attack_target_troops2 = re.compile(r'从\s*(.+?)\s*(?:进攻|攻打|攻击|出兵)\s*(.+?)\s*[，,]?\s*(\d+)', re.IGNORECASE)

        # 按捕获组顺序分类：目标在前 vs 出发在前 vs 兵力在中间
        target_first_patterns = {pat_target_from_troops, pat_target_from_troops2}
        troops_middle_pattern = pat_target_troops_from
        from_first_patterns = {pat_from_attack_to_troops, pat_attack_to_troops, pat_from_attack_target_troops, pat_from_attack_target_troops2}

        all_patterns = [
            pat_from_attack_to_troops, pat_attack_to_troops,
            pat_target_from_troops, pat_from_attack_target_troops,
            pat_target_troops_from, pat_target_from_troops2,
            pat_from_attack_target_troops2,
        ]

        for pattern in all_patterns:
            for match in pattern.finditer(content):
                groups = [g.strip() if g else "" for g in match.groups()]
                if len(groups) < 3:
                    continue

                # 根据正则类型确定捕获组含义
                if pattern in target_first_patterns:
                    to_name, from_name, troops_str = groups[0], groups[1], groups[2]
                elif pattern == troops_middle_pattern:
                    to_name, troops_str, from_name = groups[0], groups[1], groups[2]
                else:
                    from_name, to_name, troops_str = groups[0], groups[1], groups[2]

                from_block = self._fuzzy_find_block(from_name, country_name)
                to_block = self._fuzzy_find_block(to_name)
                troops = int(troops_str) if troops_str.isdigit() else 0

                # 验证：出发区块属己方、目标属敌方、二者相邻
                if not from_block or not to_block:
                    continue
                if from_block.owner != country_name:
                    continue
                if to_block.owner == country_name:
                    continue
                if to_block.name not in from_block.neighbors:
                    continue
                # 未指定兵力时默认出35%守军
                if troops <= 0:
                    troops = max(int(from_block.garrison * 0.35), 80)
                troops = min(troops, from_block.garrison)
                if troops < 50:
                    continue

                results.append((from_block.name, to_block.name, troops))

        # 如果复杂模式未匹配到，尝试简单模式（仅提取目标名）
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

                    # 自动选择守军最多的相邻己方区块作为出发地
                    best_from = None
                    best_garrison = 0
                    for bname, block in my_blocks.items():
                        if to_block.name in block.neighbors and block.garrison > best_garrison:
                            best_from = bname
                            best_garrison = block.garrison

                    if best_from and best_garrison >= 80:
                        troops = max(int(best_garrison * 0.35), 80)
                        results.append((best_from, to_block.name, troops))

        return results

    def _parse_recruits(self, content: str, country_name: str) -> list[tuple[str, int]]:
        """
        从文本中解析征兵指令

        支持格式如：征兵：在「XX」，征N / 在XX征兵N / 招募XX N

        Args:
            content: LLM生成的文本
            country_name: 国家名称

        Returns:
            list[tuple[str, int]]: (区块名, 征兵数) 的列表
        """
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

                # 未指定征兵数时默认取人力池和200的较小值
                troops_str = match.group(2).strip() if match.lastindex and match.lastindex >= 2 and match.group(2) else ""
                troops = int(troops_str) if troops_str and troops_str.isdigit() else min(block.manpower_pool, 200)
                troops = min(troops, block.manpower_pool)
                if troops <= 0:
                    continue

                results.append((block.name, troops))
                seen.add(block.name)

        # 如果未匹配到具体征兵指令但文本中包含"征兵"，自动选择人力池最高的区块
        if not results and re.search(r'征兵', content):
            my_blocks = [b for b in self.state.blocks.values() if b.owner == country_name and b.manpower_pool >= 10]
            if my_blocks:
                target = max(my_blocks, key=lambda b: b.manpower_pool)
                troops = min(target.manpower_pool, 200)
                results.append((target.name, troops))

        return results

    def _parse_develops(self, content: str, country_name: str) -> list[str]:
        """
        从文本中解析发展指令

        支持格式如：发展：在「XX」 / 在XX发展 / 建设XX

        Args:
            content: LLM生成的文本
            country_name: 国家名称

        Returns:
            list[str]: 区块名列表
        """
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
                # 已发展3次的区块不可再发展
                if block.develop_count >= 3:
                    continue
                results.append(block.name)
                seen.add(block.name)

        return results

    def _parse_moves(self, content: str, country_name: str) -> list[tuple[str, str, int]]:
        """
        从文本中解析调兵指令

        支持格式如：调兵：从「XX」至「YY」，N / 从XX调兵至YY，N

        Args:
            content: LLM生成的文本
            country_name: 国家名称

        Returns:
            list[tuple[str, str, int]]: (源区块, 目标区块, 兵力数) 的列表
        """
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
                # 未指定兵力时默认调30%守军
                if troops <= 0:
                    troops = max(int(from_block.garrison * 0.3), 50)
                # 确保源区块至少保留50守军
                troops = min(troops, from_block.garrison - 50)
                if troops <= 0:
                    continue
                results.append((from_block.name, to_block.name, troops))

        return results

    def _parse_harass(self, content: str, country_name: str) -> list[tuple[str, int]]:
        """
        从文本中解析骚扰指令

        支持格式如：骚扰「XX」，N / 袭扰XX N
        排除包含进攻关键词的匹配（防止将进攻意图误判为骚扰）。

        Args:
            content: LLM生成的文本
            country_name: 国家名称

        Returns:
            list[tuple[str, int]]: (目标区块, 兵力数) 的列表
        """
        results = []
        patterns = [
            re.compile(r'骚扰[：:]*\s*[「【\[(]?\s*(.+?)\s*[」】\])]??\s*[，,]?\s*(\d+)?', re.IGNORECASE),
            re.compile(r'(?:袭扰|偷袭|劫掠|骚扰)[：:]*\s*(.+?)\s*[，,]?\s*(\d+)?', re.IGNORECASE),
        ]

        for pattern in patterns:
            for match in pattern.finditer(content):
                # 排除包含进攻关键词的匹配（防止将进攻意图误判为骚扰）
                if re.search(r'进攻|攻打|攻击|出兵|伐', match.group(0)):
                    continue

                to_name = match.group(1).strip().rstrip('，,。.！?')
                to_block = self._fuzzy_find_block(to_name)
                if not to_block or to_block.owner == country_name:
                    continue

                # 查找与目标相邻的己方边境区块
                my_border = [b for b in self.state.blocks.values()
                             if b.owner == country_name and to_block.name in b.neighbors]
                if not my_border:
                    continue

                # 选择守军最多的边境区块作为出发地
                best = max(my_border, key=lambda b: b.garrison)
                troops_str = match.group(2).strip() if match.lastindex and match.lastindex >= 2 and match.group(2) else ""
                troops = int(troops_str) if troops_str and troops_str.isdigit() else min(best.garrison // 3, 300)
                # 骚扰兵力限制在50~500之间，且源区块至少保留50守军
                troops = max(50, min(troops, 500, best.garrison - 50))
                if troops >= 50:
                    results.append((to_block.name, troops))

        return results

    def _filter_by_ap(self, actions: list[dict], total_ap: float) -> list[dict]:
        """
        根据行动点数过滤行动列表

        按优先级排序行动，优先执行高优先级行动。
        低行动点时（<2）只执行征税+征兵+进攻；
        高行动点时（>=4）额外执行发展和调兵。
        每回合进攻次数限制为2次，最终行动数上限12个。

        Args:
            actions: 待过滤的行动列表
            total_ap: 总行动点数

        Returns:
            list[dict]: 过滤后的行动列表
        """
        filtered = []
        remaining = total_ap
        attack_count = 0

        input_count = len(actions)

        # 按行动类型分组
        tax_actions = [a for a in actions if a["action_type"] == "tax"]
        attack_actions = [a for a in actions if a["action_type"] == "attack"]
        recruit_actions = [a for a in actions if a["action_type"] == "recruit"]
        develop_actions = [a for a in actions if a["action_type"] == "develop"]
        move_actions = [a for a in actions if a["action_type"] == "move"]
        harass_actions = [a for a in actions if a["action_type"] == "harass"]
        other_actions = [a for a in actions if a["action_type"] not in ("tax", "attack", "recruit", "develop", "move", "harass")]

        if total_ap < 2:
            # 低行动点模式：优先征税+征兵+进攻
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

            for action in attack_actions:
                if attack_count >= MAX_ATTACKS_PER_TURN:
                    break
                cost = ACTION_COSTS.get(action["action_type"], 0) / 1000
                if remaining >= cost:
                    filtered.append(action)
                    remaining -= cost
                    attack_count += 1

            for action in other_actions:
                cost = ACTION_COSTS.get(action["action_type"], 0) / 1000
                if remaining >= cost:
                    filtered.append(action)
                    remaining -= cost
        else:
            # 正常/高行动点模式：按优先级执行所有类型
            # 优先级顺序：征税 > 征兵 > 进攻 > 发展 > 调兵 > 骚扰
            for action in tax_actions:
                cost = ACTION_COSTS.get(action["action_type"], 0) / 1000
                if remaining >= cost:
                    filtered.append(action)
                    remaining -= cost

            for action in recruit_actions[:3]:
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

            if total_ap >= 4:
                # 高行动点时额外执行发展和调兵
                for action in develop_actions[:3]:
                    cost = ACTION_COSTS.get(action["action_type"], 0) / 1000
                    if remaining >= cost:
                        filtered.append(action)
                        remaining -= cost

                for action in move_actions[:3]:
                    cost = ACTION_COSTS.get(action["action_type"], 0) / 1000
                    if remaining >= cost:
                        filtered.append(action)
                        remaining -= cost

            for action in harass_actions[:2]:
                cost = ACTION_COSTS.get(action["action_type"], 0) / 1000
                if remaining >= cost:
                    filtered.append(action)
                    remaining -= cost

            for action in other_actions:
                cost = ACTION_COSTS.get(action["action_type"], 0) / 1000
                if remaining >= cost:
                    filtered.append(action)
                    remaining -= cost

        logger.info(f"[AI] _filter_by_ap: input={input_count} actions, total_ap={total_ap}, output={len(filtered)} actions, remaining_ap={remaining:.1f}")
        return filtered[:12]

    def _avg_order(self, country_name: str) -> float:
        """
        计算国家所有区块的平均秩序

        Args:
            country_name: 国家名称

        Returns:
            float: 平均秩序值，无区块时返回50
        """
        blocks = [b for b in self.state.blocks.values() if b.owner == country_name]
        if not blocks:
            return 50
        return sum(b.order for b in blocks) / len(blocks)

    def _evaluate_goal(self, country: Country, country_name: str) -> StrategicGoal:
        """
        评估国家的战略目标

        优先级：
        1. 秩序<40或低秩序区块>2 → 稳定
        2. 区块数>=45且控制历史首都 → 称帝
        3. 士气<30 → 防御
        4. 默认 → 扩张

        Args:
            country: 国家对象
            country_name: 国家名称

        Returns:
            StrategicGoal: 评估出的战略目标
        """
        blocks = [b for b in self.state.blocks.values() if b.owner == country_name]
        blocks_count = len(blocks)
        low_order_count = sum(1 for b in blocks if b.order < 30)

        if country.order < 40 or low_order_count > 2:
            return StrategicGoal.STABILIZE
        if blocks_count >= GAME_CONSTANTS.get("EMPEROR_REQUIRED_BLOCKS", 45):
            if self._controls_historical_capital(country_name):
                return StrategicGoal.DECLARE_EMPEROR
        if country.morale < 30:
            return StrategicGoal.DEFEND
        return StrategicGoal.EXPAND

    def _controls_historical_capital(self, country_name: str) -> bool:
        """
        检查国家是否控制本国历史首都

        Args:
            country_name: 国家名称

        Returns:
            bool: 控制历史首都返回True
        """
        historical = HISTORICAL_CAPITALS
        for cap in historical.get(country_name, []):
            block = self.state.blocks.get(cap)
            if block and block.owner == country_name:
                return True
        return False

    def _get_border_blocks(self, country_name: str) -> list[Block]:
        """
        获取国家的边境区块列表

        边境区块定义为：拥有至少一个非己方邻居的己方区块。

        Args:
            country_name: 国家名称

        Returns:
            list[Block]: 边境区块列表
        """
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
        """
        查找可攻击的目标

        返回所有(己方边境区块, 相邻敌方区块)对，按敌方守军数升序排列
        （优先攻击守军少的目标）。

        Args:
            country_name: 国家名称
            target_owner: 可选的目标所有者过滤

        Returns:
            list[tuple[Block, Block]]: (攻击方区块, 目标区块) 对的列表
        """
        border_blocks = self._get_border_blocks(country_name)
        targets = []
        for block in border_blocks:
            for neighbor_name in block.neighbors:
                neighbor = self.state.blocks.get(neighbor_name)
                if not neighbor or neighbor.owner == country_name:
                    continue
                if target_owner and neighbor.owner != target_owner:
                    continue
                if neighbor.owner == country_name:
                    continue
                targets.append((block, neighbor))
        # 按目标守军数升序排列，优先攻击弱目标
        targets.sort(key=lambda x: x[1].garrison)
        return targets

    def _stabilize_actions(self, country_name: str) -> list[dict]:
        """
        生成稳定战略的行动列表

        优先发展低秩序区块和高秩序区块，然后征兵恢复军力，
        最后选择弱目标进攻。

        Args:
            country_name: 国家名称

        Returns:
            list[dict]: 行动列表
        """
        actions = []
        country = self.state.countries[country_name]

        # 发展低秩序区块（优先秩序最低的）
        if country.gold >= 300:
            low_order_blocks = [
                b for b in self.state.blocks.values()
                if b.owner == country_name and b.order < 60 and b.develop_count < 3 and b.supply_connected
            ]
            if low_order_blocks:
                target = max(low_order_blocks, key=lambda b: 60 - b.order)
                actions.append({"action_type": "develop", "country": country_name, "parameters": {"block": target.name}, "priority": 9})

        # 发展高秩序区块以提升经济
        if country.gold >= 300:
            high_order_blocks = [
                b for b in self.state.blocks.values()
                if b.owner == country_name and b.order > 60 and b.develop_count < 3 and b.supply_connected and not b.recently_conquered
            ]
            if high_order_blocks:
                target = max(high_order_blocks, key=lambda b: b.base_manpower)
                actions.append({"action_type": "develop", "country": country_name, "parameters": {"block": target.name}, "priority": 8})

        # 征兵恢复军力
        if country.gold >= 150:
            for block in self.state.blocks.values():
                if block.owner == country_name and block.manpower_pool >= 10 and not block.recently_conquered:
                    if self.state.round - block.last_recruit_round >= 2:
                        actions.append({"action_type": "recruit", "country": country_name, "parameters": {"block": block.name}, "priority": 7})
                        break

        # 在高人力池区块征兵
        if country.gold >= 150:
            high_manpower_blocks = [
                b for b in self.state.blocks.values()
                if b.owner == country_name and b.manpower_pool > 200 and not b.recently_conquered
                and self.state.round - b.last_recruit_round >= 2
            ]
            for block in high_manpower_blocks[:2]:
                already = any(a["parameters"].get("block") == block.name for a in actions if a["action_type"] == "recruit")
                if not already:
                    actions.append({"action_type": "recruit", "country": country_name, "parameters": {"block": block.name}, "priority": 7})

        # 进攻中立目标
        neutral_targets = self._find_attack_targets(country_name, "neutral")
        if neutral_targets:
            attacker, target = neutral_targets[0]
            if attacker.garrison >= 150:
                troops = max(int(attacker.garrison * 0.35), 80)
                actions.append({"action_type": "attack", "country": country_name, "parameters": {"from": attacker.name, "to": target.name, "troops": troops}, "priority": 5})

        # 进攻特殊中立势力
        special_targets = [(a, t) for a, t in self._find_attack_targets(country_name) if t.owner in SPECIAL_NEUTRAL_FORCES]
        if special_targets:
            attacker, target = special_targets[0]
            if attacker.garrison >= 80:
                troops = max(int(attacker.garrison * 0.35), 80)
                actions.append({"action_type": "attack", "country": country_name, "parameters": {"from": attacker.name, "to": target.name, "troops": troops}, "priority": 5})

        # 如果兵力充足，也进攻势力目标
        faction_targets = [(a, t) for a, t in self._find_attack_targets(country_name) if t.owner not in ["neutral"] and t.owner not in SPECIAL_NEUTRAL_FORCES]
        if faction_targets:
            attacker, target = faction_targets[0]
            if attacker.garrison >= 120:
                troops = max(int(attacker.garrison * 0.35), 80)
                actions.append({"action_type": "attack", "country": country_name, "parameters": {"from": attacker.name, "to": target.name, "troops": troops}, "priority": 4})

        return actions

    def _defend_actions(self, country_name: str) -> list[dict]:
        """
        生成防御战略的行动列表

        优先从内地调兵增援边境薄弱区块，然后征兵和选择性进攻。

        Args:
            country_name: 国家名称

        Returns:
            list[dict]: 行动列表
        """
        actions = []
        country = self.state.countries[country_name]

        border_blocks = self._get_border_blocks(country_name)
        border_names = {b.name for b in border_blocks}
        # 内地区块：非边境且守军>300
        interior_blocks = [b for b in self.state.blocks.values()
                           if b.owner == country_name and b.name not in border_names and b.garrison > 300]

        # 从内地调兵增援守军不足的边境区块（仅相邻时才调兵）
        for block in border_blocks:
            if block.garrison < 200 and interior_blocks:
                for interior in list(interior_blocks):
                    if block.name in interior.neighbors:
                        troops = min(int(interior.garrison * 0.3), interior.garrison - 100)
                        if troops > 0:
                            actions.append({"action_type": "move", "country": country_name, "parameters": {"from": interior.name, "to": block.name, "troops": troops}, "priority": 9})
                            interior_blocks.remove(interior)
                            break

        # 征兵
        if country.gold >= 150:
            recruit_blocks = [b for b in self.state.blocks.values() if b.owner == country_name and b.manpower_pool >= 20 and not b.recently_conquered]
            if recruit_blocks:
                target = max(recruit_blocks, key=lambda b: b.manpower_pool)
                actions.append({"action_type": "recruit", "country": country_name, "parameters": {"block": target.name}, "priority": 6})

        # 进攻中立目标
        neutral_targets = self._find_attack_targets(country_name, "neutral")
        if neutral_targets:
            attacker, target = neutral_targets[0]
            if attacker.garrison >= 150:
                troops = max(int(attacker.garrison * 0.35), 80)
                actions.append({"action_type": "attack", "country": country_name, "parameters": {"from": attacker.name, "to": target.name, "troops": troops}, "priority": 5})

        # 进攻特殊中立势力
        special_targets = [(a, t) for a, t in self._find_attack_targets(country_name) if t.owner in SPECIAL_NEUTRAL_FORCES]
        if special_targets:
            attacker, target = special_targets[0]
            if attacker.garrison >= 80:
                troops = max(int(attacker.garrison * 0.35), 80)
                actions.append({"action_type": "attack", "country": country_name, "parameters": {"from": attacker.name, "to": target.name, "troops": troops}, "priority": 5})

        # 如果兵力充足，也进攻势力目标
        faction_targets = [(a, t) for a, t in self._find_attack_targets(country_name) if t.owner not in ["neutral"] and t.owner not in SPECIAL_NEUTRAL_FORCES]
        if faction_targets:
            attacker, target = faction_targets[0]
            if attacker.garrison >= 120:
                troops = max(int(attacker.garrison * 0.35), 80)
                actions.append({"action_type": "attack", "country": country_name, "parameters": {"from": attacker.name, "to": target.name, "troops": troops}, "priority": 4})

        return actions

    def _revenge_actions(self, country_name: str) -> list[dict]:
        """
        生成复仇战略的行动列表

        复仇战略与扩张战略相同，以进攻为主。

        Args:
            country_name: 国家名称

        Returns:
            list[dict]: 行动列表
        """
        return self._expand_actions(country_name)

    def _expand_actions(self, country_name: str) -> list[dict]:
        """
        生成扩张战略的行动列表

        优先征兵和发展，然后按优先级进攻：中立 > 特殊中立势力 > 势力目标。
        进攻后从内地调兵增援前线。

        Args:
            country_name: 国家名称

        Returns:
            list[dict]: 行动列表
        """
        actions = []
        country = self.state.countries[country_name]
        my_blocks = [b for b in self.state.blocks.values() if b.owner == country_name]
        border_blocks = self._get_border_blocks(country_name)
        border_names = {b.name for b in border_blocks}

        # 征兵：优先人力池高的区块
        if country.gold >= 150:
            recruit_blocks = [b for b in my_blocks if b.manpower_pool >= 20 and not b.recently_conquered and self.state.round - b.last_recruit_round >= 2]
            recruit_blocks.sort(key=lambda b: b.manpower_pool, reverse=True)
            for target in recruit_blocks[:3]:
                actions.append({"action_type": "recruit", "country": country_name, "parameters": {"block": target.name}, "priority": 7})

        # 发展：优先基础人力高的区块
        if country.gold >= 300:
            develop_blocks = [b for b in my_blocks if b.develop_count < 3 and b.supply_connected and not b.recently_conquered and b.order > 50]
            develop_blocks.sort(key=lambda b: b.base_manpower, reverse=True)
            for target in develop_blocks[:2]:
                actions.append({"action_type": "develop", "country": country_name, "parameters": {"block": target.name}, "priority": 6})

        # 进攻中立目标（最多2次）
        neutral_targets = self._find_attack_targets(country_name, "neutral")
        if neutral_targets:
            for attacker, target in neutral_targets[:MAX_ATTACKS_PER_TURN]:
                if attacker.garrison >= 120:
                    troops = max(int(attacker.garrison * 0.35), 80)
                    actions.append({"action_type": "attack", "country": country_name, "parameters": {"from": attacker.name, "to": target.name, "troops": troops}, "priority": 8})

        # 进攻特殊中立势力
        special_targets = [(a, t) for a, t in self._find_attack_targets(country_name) if t.owner in SPECIAL_NEUTRAL_FORCES]
        if special_targets:
            for attacker, target in special_targets[:1]:
                if attacker.garrison >= 80:
                    troops = max(int(attacker.garrison * 0.35), 80)
                    actions.append({"action_type": "attack", "country": country_name, "parameters": {"from": attacker.name, "to": target.name, "troops": troops}, "priority": 8})

        # 进攻势力目标
        faction_targets = [(a, t) for a, t in self._find_attack_targets(country_name) if t.owner not in ["neutral"] and t.owner not in SPECIAL_NEUTRAL_FORCES]
        if faction_targets:
            for attacker, target in faction_targets[:1]:
                if attacker.garrison >= 100:
                    troops = max(int(attacker.garrison * 0.35), 80)
                    actions.append({"action_type": "attack", "country": country_name, "parameters": {"from": attacker.name, "to": target.name, "troops": troops}, "priority": 7})

        # 兜底：如果没有势力目标且守军>=60，尝试任意边境目标
        if not any(a["action_type"] == "attack" for a in actions if a.get("parameters", {}).get("to") and self.state.blocks.get(a["parameters"]["to"]) and self.state.blocks[a["parameters"]["to"]].owner not in ["neutral", country_name]):
            all_targets = self._find_attack_targets(country_name)
            fallback_targets = [(a, t) for a, t in all_targets if a.garrison >= 60]
            if fallback_targets:
                attacker, target = fallback_targets[0]
                troops = max(int(attacker.garrison * 0.35), 60)
                actions.append({"action_type": "attack", "country": country_name, "parameters": {"from": attacker.name, "to": target.name, "troops": troops}, "priority": 6})

        # 进攻后从内地调兵增援前线
        interior_blocks = [b for b in my_blocks if b.name not in border_names and b.garrison > 300]
        for border in border_blocks:
            if border.garrison < 200 and interior_blocks:
                for interior in list(interior_blocks):
                    if border.name in interior.neighbors:
                        troops = min(int(interior.garrison * 0.3), interior.garrison - 100)
                        if troops > 0:
                            actions.append({"action_type": "move", "country": country_name, "parameters": {"from": interior.name, "to": border.name, "troops": troops}, "priority": 5})
                            interior_blocks.remove(interior)
                            break

        return actions
