"""
战争迷雾系统模块

实现三国博弈中的信息可见性机制，模拟战争中情报不对称的现实。
不同位置的区块对观察者有不同的可见程度，影响AI决策和玩家体验。

迷雾分为三个阶段，随游戏进程逐步消散：
- 第一阶段（回合1-120）：最浓迷雾，仅可见己方和相邻区块
- 第二阶段（回合121-240）：中等迷雾，可见同盟区块和所有区块所有者
- 第三阶段（回合241+）：稀薄迷雾，可见所有区块的基本信息

可见性层级（从高到低）：
1. 己方区块：完全可见（精确守军、秩序、士气、人力）
2. 相邻区块：部分可见（估算守军、秩序/士气范围、胜率标签）
3. 同盟区块：部分可见（估算守军、秩序/士气范围）
4. 第三阶段非相邻：部分可见（估算守军、秩序/士气范围）
5. 第二阶段非相邻：仅可见所有者
6. 第一阶段非相邻：不可见
"""
import random
from typing import Optional

from ..models import (
    GameState, Block, BlockVisibility, WinRateLabel,
)
from ..core.constants import GAME_CONSTANTS


class FogSystem:
    """战争迷雾系统，管理区块的可见性和信息精度。

    根据区块与观察者的关系（己方/相邻/同盟/远距离）和迷雾阶段，
    计算每个区块对观察者的可见程度和信息精度。
    """

    def get_visible_state(self, state: GameState, country_name: str) -> dict:
        """获取指定国家视角下的可见区块状态。

        遍历所有区块，根据区块与观察者的关系和迷雾阶段，
        计算每个区块的可见性和信息精度。

        Args:
            state: 游戏状态
            country_name: 观察者国家名

        Returns:
            包含以下字段的字典：
            - country: 观察者国家名
            - fog_phase: 当前迷雾阶段（1/2/3）
            - visible_blocks: 区块名到BlockVisibility的映射
        """
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
        """根据回合数确定当前迷雾阶段。

        三个阶段：
        - 阶段1（回合1-120）：最浓迷雾
        - 阶段2（回合121-240）：中等迷雾
        - 阶段3（回合241+）：稀薄迷雾

        Args:
            round_num: 当前回合数

        Returns:
            迷雾阶段编号（1/2/3）
        """
        if round_num <= GAME_CONSTANTS["FOG_PHASE_1_END"]:
            return 1
        elif round_num <= GAME_CONSTANTS["FOG_PHASE_2_END"]:
            return 2
        else:
            return 3

    def _get_owned_blocks(self, state: GameState, country_name: str) -> set[str]:
        """获取国家拥有的所有区块名称集合。

        Args:
            state: 游戏状态
            country_name: 国家名

        Returns:
            己方区块名称集合
        """
        return {name for name, b in state.blocks.items() if b.owner == country_name}

    def _get_adjacent_blocks(self, state: GameState, owned: set[str]) -> set[str]:
        """获取与己方区块相邻的非己方区块名称集合。

        Args:
            state: 游戏状态
            owned: 己方区块名称集合

        Returns:
            相邻非己方区块名称集合
        """
        adjacent = set()
        for name in owned:
            block = state.blocks.get(name)
            if block:
                for neighbor in block.neighbors:
                    if neighbor not in owned:
                        adjacent.add(neighbor)
        return adjacent

    def _get_allied_blocks(self, state: GameState, country_name: str) -> set[str]:
        """获取同盟国拥有的所有区块名称集合。

        通过检查外交关系中的is_allied标记确定同盟国，
        然后收集同盟国拥有的所有区块。

        Args:
            state: 游戏状态
            country_name: 国家名

        Returns:
            同盟国区块名称集合
        """
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
        """计算单个区块对观察者的可见性和信息精度。

        可见性优先级（从高到低）：
        1. 己方区块：完全可见，精确数据
        2. 相邻区块：可见，敌方数据为估算值，附带胜率标签
        3. 同盟区块：可见，数据为估算值
        4. 第三阶段远距离：可见，数据为估算值
        5. 第二阶段远距离：仅可见所有者
        6. 第一阶段远距离：不可见

        信息精度说明：
        - 精确值：守军、秩序、士气为实际值
        - 估算值：守军约为实际的80%±10%噪声，秩序/士气为范围区间
        - 范围区间：将0-100的值映射为4个区间之一

        Args:
            state: 游戏状态
            block_name: 区块名
            block: 区块对象
            country_name: 观察者国家名
            owned: 己方区块集合
            adjacent: 相邻区块集合
            allied_blocks: 同盟区块集合
            fog_phase: 迷雾阶段

        Returns:
            BlockVisibility对象，包含可见性和信息精度
        """
        vis = BlockVisibility(name=block_name)

        # 优先级1：己方区块——完全可见，精确数据
        if block_name in owned:
            vis.visible = True
            vis.owner = block.owner
            vis.garrison_estimate = block.garrison
            vis.order_range = (block.order, block.order)
            vis.morale_range = (block.morale, block.morale)
            vis.base_manpower = block.base_manpower
            return vis

        # 优先级2：相邻区块——可见，敌方数据为估算值，附带胜率标签
        if block_name in adjacent:
            vis.visible = True
            vis.owner = block.owner
            if block.owner == "neutral":
                # 中立区块：完全可见（中立势力无隐藏动机）
                vis.garrison_estimate = block.garrison
                vis.order_range = (block.order, block.order)
                vis.morale_range = (block.morale, block.morale)
            elif block_name in allied_blocks:
                # 同盟相邻区块：完全可见（盟友共享情报）
                vis.garrison_estimate = block.garrison
                vis.order_range = (block.order, block.order)
                vis.morale_range = (block.morale, block.morale)
                vis.base_manpower = block.base_manpower
            else:
                # 敌方相邻区块：估算值（侦察情报有误差）
                vis.garrison_estimate = self._estimate_garrison(block.garrison)
                vis.order_range = self._value_to_range(block.order)
                vis.morale_range = self._value_to_range(block.morale)
            # 相邻敌方区块附带胜率标签，辅助决策
            vis.win_rate_label = self._calculate_win_rate(state, country_name, block)
            return vis

        # 优先级3：同盟区块（非相邻）——可见，数据为估算值
        if block_name in allied_blocks:
            vis.visible = True
            vis.owner = block.owner
            if fog_phase >= 2:
                # 第二阶段起：同盟提供更精确的守军估算
                vis.garrison_estimate = self._estimate_garrison(block.garrison)
            else:
                # 第一阶段：同盟守军估算精度较低
                vis.garrison_estimate = self._estimate_garrison_range(block.garrison)
            vis.order_range = self._value_to_range(block.order)
            vis.morale_range = self._value_to_range(block.morale)
            if fog_phase >= 2:
                # 第二阶段起：同盟共享人力信息
                vis.base_manpower = block.base_manpower
            return vis

        # 优先级4：第三阶段远距离——可见，估算值
        if fog_phase >= 3:
            vis.visible = True
            vis.owner = block.owner
            vis.garrison_estimate = self._estimate_garrison(block.garrison)
            vis.order_range = self._value_to_range(block.order)
            vis.morale_range = self._value_to_range(block.morale)
            return vis

        # 优先级5：第二阶段远距离——仅可见所有者
        if fog_phase >= 2:
            vis.visible = True
            vis.owner = block.owner
            return vis

        # 优先级6：第一阶段远距离——不可见
        vis.visible = False
        return vis

    def _estimate_garrison(self, actual: int) -> int:
        """估算守军数量（较高精度）。

        估算值约为实际值的80%，加上±10%的随机噪声，
        模拟侦察情报的不精确性。

        Args:
            actual: 实际守军数量

        Returns:
            估算的守军数量（非负整数）
        """
        estimate = int(actual * 0.8)
        noise = int(estimate * random.uniform(-0.1, 0.1))
        return max(0, estimate + noise)

    def _estimate_garrison_range(self, actual: int) -> int:
        """估算守军数量（较低精度，用于第一阶段同盟区块）。

        当前实现与_estimate_garrison相同，预留接口以便未来
        实现更粗粒度的估算（如返回范围而非单值）。

        Args:
            actual: 实际守军数量

        Returns:
            估算的守军数量
        """
        return self._estimate_garrison(actual)

    def _value_to_range(self, value: int) -> tuple[int, int]:
        """将0-100的数值映射为描述性区间。

        区间划分：
        - 80-100: 高水平
        - 50-79: 中等水平
        - 30-49: 较低水平
        - 0-29: 危险水平

        这种粗粒度的区间表示模拟了情报的不精确性，
        观察者只能知道大致范围而非精确数值。

        Args:
            value: 0-100的数值

        Returns:
            (下限, 上限) 的区间元组
        """
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
        """计算进攻相邻敌方区块的胜率标签。

        使用己方相邻区块中守军最多的区块作为假想出兵点，
        简化计算攻防战力比：
        - 攻方战力 = 最大守军 × (1 + 士气/600)
        - 守方战力 = 目标守军 × (1 + 50/600) × 1.05（假设平均士气50+防御加成）

        胜率标签：
        - HIGH: 战力比 >= 1.5
        - MEDIUM: 1.0 <= 战力比 < 1.5
        - LOW: 战力比 < 1.0
        - UNKNOWN: 无相邻己方区块

        Args:
            state: 游戏状态
            country_name: 观察者国家名
            target_block: 目标区块

        Returns:
            WinRateLabel胜率标签
        """
        country = state.countries.get(country_name)
        if not country:
            return WinRateLabel.UNKNOWN

        # 找到与目标区块相邻的己方区块
        adjacent_owned = [
            n for n in target_block.neighbors
            if n in state.blocks and state.blocks[n].owner == country_name
        ]
        if not adjacent_owned:
            return WinRateLabel.UNKNOWN

        # 选择守军最多的相邻己方区块作为假想出兵点
        best_block = max(adjacent_owned, key=lambda n: state.blocks[n].garrison)
        attacker_troops = state.blocks[best_block].garrison

        # 简化战力计算（不考虑补给线、武将特性等复杂因素）
        attacker_power = attacker_troops * (1 + country.morale / 600)
        # 守方假设平均士气50，加上5%防御加成
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
