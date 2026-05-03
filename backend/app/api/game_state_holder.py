from typing import Optional
from ..core import GameEngine, CombatSystem, EconomySystem, DiplomacySystem, FogSystem, ChroniclerSystem


def _create_ai_narrative_generator():
    def generate_ai_narrative(state, events, trend, round_number):
        from ..ai import get_ai_client

        chronicler_client = get_ai_client("chronicler")
        if not chronicler_client or not chronicler_client.config.is_valid():
            return None

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

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(_sync_generate, chronicler_client, context)
                return future.result(timeout=30)
        else:
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(chronicler_client.generate("chronicler", context))
                return result
            finally:
                loop.close()

    return generate_ai_narrative


def _sync_generate(client, context: str) -> str:
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(client.generate("chronicler", context))
        return result
    finally:
        loop.close()


class _GameContextHolder:
    _instance: Optional["_GameContextHolder"] = None

    def __init__(self):
        self.engine = GameEngine()
        self.combat = CombatSystem()
        self.economy = EconomySystem()
        self.diplomacy = DiplomacySystem()
        self.fog = FogSystem()
        self.chronicler = ChroniclerSystem()
        self.chronicler.set_ai_narrative_generator(_create_ai_narrative_generator())

    @classmethod
    def get(cls) -> "_GameContextHolder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def get_engine() -> GameEngine:
    return _GameContextHolder.get().engine


def get_combat() -> CombatSystem:
    return _GameContextHolder.get().combat


def get_economy() -> EconomySystem:
    return _GameContextHolder.get().economy


def get_diplomacy() -> DiplomacySystem:
    return _GameContextHolder.get().diplomacy


def get_fog() -> FogSystem:
    return _GameContextHolder.get().fog


def get_chronicler() -> ChroniclerSystem:
    return _GameContextHolder.get().chronicler
