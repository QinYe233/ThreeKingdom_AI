"""
编年史系统模块

实现三国博弈中的叙事生成逻辑，将游戏事件转化为史官风格的叙事文本。
编年史系统负责收集回合事件、分析各国态势、生成叙事文本。

叙事生成支持两种模式：
- AI叙事：通过注入的AI叙事生成器，使用LLM生成文言风格的叙事
- 回退叙事：当AI不可用时，使用模板化的简单叙事

主要功能：
- 从行动日志和历史记录中提取回合事件
- 分析各国军事和经济态势
- 生成AI叙事或回退叙事
"""
from typing import Callable, Optional

from ..models import GameState, BattleResult
from ..core.constants import ORDER_MORALE_DESCRIPTIONS, EXCLUDED_CHRONICLER_COUNTRIES


class ChroniclerSystem:
    """编年史系统，负责记录和叙述游戏事件。

    将游戏中的行动、战斗、外交等事件分类整理，
    分析各国态势趋势，并生成史官风格的叙事文本。
    支持注入AI叙事生成器以获得更生动的叙事效果。

    Attributes:
        _ai_narrative_generator: AI叙事生成器回调函数，可选。
            签名为 (GameState, list[dict], dict, int) -> str
    """

    def __init__(self):
        """初始化编年史系统。"""
        self._ai_narrative_generator: Optional[Callable[[GameState, list[dict], dict, int], str]] = None

    def set_ai_narrative_generator(self, generator: Callable[[GameState, list[dict], dict, int], str]) -> None:
        """设置AI叙事生成器回调。

        通过注入外部AI生成器，使编年史系统能够使用LLM生成更生动的叙事文本。
        生成器接收游戏状态、事件列表、态势趋势和回合数，返回叙事文本。

        Args:
            generator: AI叙事生成器回调函数
        """
        self._ai_narrative_generator = generator

    def generate_narrative(self, state: GameState, battle_results: list[BattleResult], round_number: Optional[int] = None) -> dict:
        """生成本回合的编年史叙事。

        完整流程：
        1. 从行动日志和历史记录中提取回合事件
        2. 分析各国军事和经济态势
        3. 尝试AI叙事，失败时使用回退叙事

        Args:
            state: 游戏状态
            battle_results: 本回合战斗结果列表
            round_number: 回合数，默认使用state.round

        Returns:
            包含以下字段的字典：
            - round: 回合数
            - date: 时间线字符串（如"200年1月"）
            - events: 事件列表
            - trend: 各国态势趋势
            - narrative: 叙事文本
        """
        if round_number is None:
            round_number = state.round

        # 第一步：从行动日志和历史记录中提取事件
        events = self._generate_events_from_log(state, round_number)

        # 第二步：分析各国态势
        trend = self._generate_trend(state)

        # 第三步：生成叙事文本（优先AI，回退到模板）
        ai_narrative = self._generate_ai_narrative(state, events, trend, round_number)

        return {
            "round": round_number,
            "date": state.timeline.to_string(),
            "events": events,
            "trend": trend,
            "narrative": ai_narrative,
        }

    def _generate_events_from_log(self, state: GameState, round_number: int) -> list[dict]:
        """从行动日志和历史记录中提取回合事件。

        事件分类规则：
        - attack+success → capture（攻占）
        - attack/harass → battle（战斗）
        - develop/recruit → development（发展）
        - tax → economy（经济）
        - move → military（军事调动）
        - move_capital/declare_emperor → political（政治）
        - diplomacy → diplomacy（外交）

        同时从state.history中提取特殊事件：
        - capital_fallen → 首都沦陷
        - nation_defeated → 国家灭亡

        Args:
            state: 游戏状态
            round_number: 目标回合数

        Returns:
            事件字典列表，每个包含type、country（可选）、message字段
        """
        events = []

        # 从行动日志中提取本回合事件
        round_actions = [log for log in state.action_log if log.get("round") == round_number]

        for action in round_actions:
            country = action.get("country", "")
            action_type = action.get("action", "")
            detail = action.get("detail", "")

            # 根据行动类型分类事件
            event_type = "info"
            if "attack" in action_type:
                if "success" in action_type:
                    event_type = "capture"
                else:
                    event_type = "battle"
            elif "harass" in action_type:
                event_type = "battle"
            elif "develop" in action_type:
                event_type = "development"
            elif "recruit" in action_type:
                event_type = "development"
            elif "tax" in action_type:
                event_type = "economy"
            elif "move" in action_type and "capital" not in action_type:
                event_type = "military"
            elif "move_capital" in action_type:
                event_type = "political"
            elif "declare_emperor" in action_type:
                event_type = "political"
            elif "diplomacy" in action_type:
                event_type = "diplomacy"

            events.append({
                "type": event_type,
                "country": country,
                "message": f"【{country}】{detail}",
            })

        # 从历史记录中提取特殊事件
        for entry in state.history:
            if entry.get("round") == round_number:
                event_type = entry.get("event")
                if event_type == "capital_fallen":
                    events.append({
                        "type": "capital_fallen",
                        "message": f"{entry.get('country')}都城陷落！朝廷仓皇南迁，天下震动。",
                    })
                elif event_type == "nation_defeated":
                    events.append({
                        "type": "nation_defeated",
                        "message": f"{entry.get('country')}疆土尽丧，社稷覆亡。",
                    })

        return events

    def _generate_trend(self, state: GameState) -> dict:
        """分析各国军事和经济态势。

        对每个存活的主要国家（排除中立势力），计算：
        - blocks: 控制区块数
        - garrison: 总守军数
        - order_desc: 秩序描述（如"政通人和"/"民不聊生"）
        - morale_desc: 士气描述（如"士气如虹"/"军心涣散"）
        - military_trend: 军事趋势（扩张中/守势/军心不稳/内乱）
        - economy_trend: 经济趋势（富足/平稳/拮据）

        Args:
            state: 游戏状态

        Returns:
            国家名到态势信息的字典
        """
        trends = {}
        for name, country in state.countries.items():
            # 跳过已灭亡国家和中立势力
            if country.is_defeated or name in EXCLUDED_CHRONICLER_COUNTRIES:
                continue

            blocks_count = sum(1 for b in state.blocks.values() if b.owner == name)
            total_garrison = sum(b.garrison for b in state.blocks.values() if b.owner == name)

            order_desc, morale_desc = self._describe_order_morale(country.order, country.morale)

            # 军事趋势判定：优先级 内乱 > 军心不稳 > 扩张中 > 守势
            military_trend = "扩张中" if blocks_count > 15 else "守势"
            if country.morale < 40:
                military_trend = "军心不稳"
            if country.order < 30:
                military_trend = "内乱"

            # 经济趋势判定：基于金铢储备
            economy_trend = "富足" if country.gold > 2000 else "拮据" if country.gold < 500 else "平稳"

            trends[name] = {
                "blocks": blocks_count,
                "garrison": total_garrison,
                "order_desc": order_desc,
                "morale_desc": morale_desc,
                "military_trend": military_trend,
                "economy_trend": economy_trend,
            }

        return trends

    def _generate_ai_narrative(self, state: GameState, events: list[dict], trend: dict, round_number: int) -> str:
        """生成AI叙事文本。

        优先使用注入的AI叙事生成器，如果生成器不可用或抛出异常，
        回退到模板化的简单叙事。

        Args:
            state: 游戏状态
            events: 事件列表
            trend: 态势趋势
            round_number: 回合数

        Returns:
            叙事文本字符串
        """
        try:
            if self._ai_narrative_generator:
                result = self._ai_narrative_generator(state, events, trend, round_number)
                return result if result else self._fallback_narrative(events, trend, round_number)
        except Exception:
            pass
        return self._fallback_narrative(events, trend, round_number)

    def _fallback_narrative(self, events: list[dict], trend: dict, round_number: int) -> str:
        """生成回退叙事文本（当AI不可用时使用）。

        使用简单的模板拼接方式生成叙事：
        - 无事件时返回"是岁无事，天下太平。"
        - 有事件时列出事件消息
        - 根据军事趋势添加态势描述

        Args:
            events: 事件列表
            trend: 态势趋势
            round_number: 回合数

        Returns:
            模板化的叙事文本
        """
        if not events:
            return "是岁无事，天下太平。"

        lines = []
        for e in events:
            lines.append(e["message"])

        # 根据军事趋势添加态势描述
        if trend:
            for name, t in trend.items():
                if t["military_trend"] == "扩张中":
                    lines.append(f"{name}势方张，锐意进取。")
                elif t["military_trend"] == "内乱":
                    lines.append(f"{name}内乱频仍，朝野不安。")
                elif t["military_trend"] == "军心不稳":
                    lines.append(f"{name}军心浮动，士气低迷。")

        return "\n".join(lines)

    def _describe_order_morale(self, order: int, morale: int) -> tuple[str, str]:
        """将秩序和士气数值转换为描述性文字。

        使用ORDER_MORALE_DESCRIPTIONS常量中的映射：
        - 80-100: "政通人家"/"士气如虹"
        - 50-79: "局势稳定"/"军心可用"
        - 30-49: "暗流涌动"/"士气低迷"
        - 0-29: "民不聊生"/"军心涣散"

        Args:
            order: 秩序值（0-100）
            morale: 士气值（0-100）

        Returns:
            (秩序描述, 士气描述) 的元组
        """
        order_desc = "民不聊生"
        morale_desc = "军心涣散"

        for (low, high), (o_desc, m_desc) in ORDER_MORALE_DESCRIPTIONS.items():
            if low <= order <= high:
                order_desc = o_desc
            if low <= morale <= high:
                morale_desc = m_desc

        return order_desc, morale_desc
