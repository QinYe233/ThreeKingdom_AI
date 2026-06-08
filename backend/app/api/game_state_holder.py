"""
游戏状态持有者模块

管理游戏引擎和各子系统的全局单例实例，提供统一的访问入口。
同时管理AI处理锁，防止多个AI同时执行导致状态冲突。
本模块提供以下功能：
- 游戏引擎、战斗系统、经济系统、外交系统、迷雾系统、编年史系统的单例管理
- AI处理锁的获取与释放（防止并发AI执行）
- AI编年史叙事生成器的创建（处理异步调用兼容性）
"""
from typing import Optional
import asyncio
from ..core import GameEngine, CombatSystem, EconomySystem, DiplomacySystem, FogSystem, ChroniclerSystem


# AI处理锁：确保同一时间只有一个AI在执行行动
_ai_lock = asyncio.Lock()


def is_ai_processing() -> bool:
    """
    检查AI是否正在处理中

    Returns:
        bool: AI正在处理返回True，否则返回False
    """
    return _ai_lock.locked()


async def acquire_ai_lock() -> bool:
    """
    尝试获取AI处理锁

    使用极短超时（0.01秒）实现非阻塞式锁获取，
    避免在锁已被占用时长时间等待。这是原子操作，无竞态条件。

    Returns:
        bool: 成功获取锁返回True，锁已被占用返回False
    """
    try:
        await asyncio.wait_for(_ai_lock.acquire(), timeout=0.01)
        return True
    except asyncio.TimeoutError:
        return False


def release_ai_lock() -> None:
    """
    释放AI处理锁

    安全释放锁，如果锁未被持有（如异常情况下）则忽略RuntimeError。
    """
    try:
        _ai_lock.release()
    except RuntimeError:
        pass


def _create_ai_narrative_generator():
    """
    创建AI编年史叙事生成器

    返回一个闭包函数，该函数在编年史系统需要AI生成叙事时被调用。
    处理了异步/同步环境兼容性问题：
    - 如果在已有事件循环中运行（如FastAPI请求处理中），使用线程池执行
    - 如果没有事件循环，创建新的事件循环执行

    Returns:
        function: 叙事生成器函数，签名为 (state, events, trend, round_number) -> str
    """
    def generate_ai_narrative(state, events, trend, round_number):
        from ..ai import get_ai_client

        # 获取史官角色的AI客户端
        chronicler_client = get_ai_client("chronicler")
        if not chronicler_client or not chronicler_client.config.is_valid():
            return None

        # 格式化事件文本
        events_text = ""
        for e in events:
            events_text += f"- {e['message']}\n"

        # 格式化各势力态势文本
        trend_text = ""
        for name, t in trend.items():
            trend_text += f"- {name}：{t['military_trend']}，{t['economy_trend']}，{t['order_desc']}，{t['morale_desc']}，领地{t['blocks']}处，兵力{t['garrison']}\n"

        # 构建上下文
        context = f"""当前回合：第{round_number}回
时间：{state.timeline.to_string()}

本回合事件：
{events_text if events_text else "（无重大事件）"}

各势力态势：
{trend_text if trend_text else "（无势力信息）"}"""

        # 处理异步/同步环境兼容性
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # 在已有事件循环中（如FastAPI请求中），使用线程池避免阻塞
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(_sync_generate, chronicler_client, context)
                return future.result(timeout=30)
        else:
            # 没有事件循环，创建新的事件循环执行
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(chronicler_client.generate("chronicler", context))
                return result
            finally:
                loop.close()

    return generate_ai_narrative


def _sync_generate(client, context: str) -> str:
    """
    在新事件循环中同步执行AI生成

    用于在线程池中运行异步AI调用。

    Args:
        client: AI客户端实例
        context: 上下文文本

    Returns:
        str: AI生成的叙事文本
    """
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(client.generate("chronicler", context))
        return result
    finally:
        loop.close()


class _GameContextHolder:
    """
    游戏状态持有者（单例模式）

    集中管理游戏引擎和各子系统的唯一实例，
    确保整个应用共享同一套游戏状态和系统组件。
    """
    _instance: Optional["_GameContextHolder"] = None

    def __init__(self):
        """初始化所有游戏子系统实例"""
        self.engine = GameEngine()
        self.combat = CombatSystem()
        self.economy = EconomySystem()
        self.diplomacy = DiplomacySystem()
        self.fog = FogSystem()
        self.chronicler = ChroniclerSystem()
        # 为编年史系统注入AI叙事生成器
        self.chronicler.set_ai_narrative_generator(_create_ai_narrative_generator())

    @classmethod
    def get(cls) -> "_GameContextHolder":
        """
        获取单例实例

        首次调用时创建实例，后续调用返回同一实例。

        Returns:
            _GameContextHolder: 全局唯一的持有者实例
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def get_engine() -> GameEngine:
    """
    获取游戏引擎单例

    Returns:
        GameEngine: 游戏引擎实例
    """
    return _GameContextHolder.get().engine


def get_combat() -> CombatSystem:
    """
    获取战斗系统单例

    Returns:
        CombatSystem: 战斗系统实例
    """
    return _GameContextHolder.get().combat


def get_economy() -> EconomySystem:
    """
    获取经济系统单例

    Returns:
        EconomySystem: 经济系统实例
    """
    return _GameContextHolder.get().economy


def get_diplomacy() -> DiplomacySystem:
    """
    获取外交系统单例

    Returns:
        DiplomacySystem: 外交系统实例
    """
    return _GameContextHolder.get().diplomacy


def get_fog() -> FogSystem:
    """
    获取迷雾系统单例

    Returns:
        FogSystem: 迷雾系统实例
    """
    return _GameContextHolder.get().fog


def get_chronicler() -> ChroniclerSystem:
    """
    获取编年史系统单例

    Returns:
        ChroniclerSystem: 编年史系统实例
    """
    return _GameContextHolder.get().chronicler
