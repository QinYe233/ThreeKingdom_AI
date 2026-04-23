import json
from typing import Optional

from ..models import GameState, BattleResult
from ..core.constants import ORDER_MORALE_DESCRIPTIONS


class ChroniclerSystem:
    def generate_narrative(self, state: GameState, battle_results: list[BattleResult], round_number: Optional[int] = None) -> dict:
        if round_number is None:
            round_number = state.round

        events = self._generate_events_from_log(state, round_number)

        trend = self._generate_trend(state)

        ai_narrative = self._generate_ai_narrative(state, events, trend, round_number)

        return {
            "round": round_number,
            "date": state.timeline.to_string(),
            "events": events,
            "trend": trend,
            "narrative": ai_narrative,
        }

    def _generate_events_from_log(self, state: GameState, round_number: int) -> list[dict]:
        events = []

        round_actions = [log for log in state.action_log if log.get("round") == round_number]

        for action in round_actions:
            country = action.get("country", "")
            action_type = action.get("action", "")
            detail = action.get("detail", "")

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
        trends = {}
        for name, country in state.countries.items():
            if country.is_defeated or name in ["公孙度", "士燮", "南中", "山越", "凉州"]:
                continue

            blocks_count = sum(1 for b in state.blocks.values() if b.owner == name)
            total_garrison = sum(b.garrison for b in state.blocks.values() if b.owner == name)

            order_desc, morale_desc = self._describe_order_morale(country.order, country.morale)

            military_trend = "扩张中" if blocks_count > 15 else "守势"
            if country.morale < 40:
                military_trend = "军心不稳"
            if country.order < 30:
                military_trend = "内乱"

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
        try:
            from ..ai import get_ai_client, SYSTEM_PROMPTS

            chronicler_client = get_ai_client("chronicler")
            if not chronicler_client or not chronicler_client.config.is_valid():
                return self._fallback_narrative(events, trend, round_number)

            events_text = ""
            for e in events:
                events_text += f"- {e['message']}\n"

            trend_text = ""
            for name, t in trend.items():
                trend_text += f"- {name}：{t['military_trend']}，{t['economy_trend']}，{t['order_desc']}，{t['morale_desc']}，领地{t['blocks']}处，兵力{t['garrison']}\n"

            context = f"""当前回合：第{round_number}回
时间：{state.timeline.to_string()}

本回合事件：
{events_text if events_text else "（无重大事件）"}

各势力态势：
{trend_text if trend_text else "（无势力信息）"}"""

            import asyncio
            system_prompt = SYSTEM_PROMPTS.get("chronicler", "").format(context=context)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(chronicler_client.generate("chronicler", context))
                return result if result else self._fallback_narrative(events, trend, round_number)
            finally:
                loop.close()

        except Exception as e:
            return self._fallback_narrative(events, trend, round_number)

    def _fallback_narrative(self, events: list[dict], trend: dict, round_number: int) -> str:
        if not events:
            return "是岁无事，天下太平。"

        lines = []
        for e in events:
            lines.append(e["message"])

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
        order_desc = "民不聊生"
        morale_desc = "军心涣散"

        for (low, high), (o_desc, m_desc) in ORDER_MORALE_DESCRIPTIONS.items():
            if low <= order <= high:
                order_desc = o_desc
            if low <= morale <= high:
                morale_desc = m_desc

        return order_desc, morale_desc
