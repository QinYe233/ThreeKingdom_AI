"""
经济系统模块

实现三国博弈中的经济运作逻辑，包括税收征收、区块发展、专精设置和征兵。
经济是国家运转的基础，直接影响金铢收入、人力储备和军事实力。

主要功能：
- 税收：根据区块人力、秩序和专精计算金铢收入
- 发展：消耗金铢提升区块人力和秩序
- 专精：满发展区块可选择农垦/商贸/堡垒专精
- 征兵：消耗金铢将人力转化为守军
"""
from typing import Optional
from ..models import Block, Country, GameState, BlockSpecialization
from ..core.constants import GAME_CONSTANTS


class EconomySystem:
    """经济系统，管理税收、发展、专精和征兵等经济行为。

    所有经济行为都涉及金铢的消耗或收入，以及人力、秩序等属性的变化。
    经济决策需要权衡短期收益（征税）和长期发展（发展/专精）。
    """

    def collect_tax(self, state: GameState, country_name: str) -> dict:
        """征收税收，从所有己方区块获取金铢。

        税收计算公式：区块税收 = 基础人力 × 动态系数 × 秩序修正

        动态系数随控制区块数量递减（扩张成本），最低为0.05：
        dynamic_coeff = max(0.05, 0.1 - (控制区块数 / 1400 × 2))

        秩序修正取国家秩序和区块秩序的较小值：
        order_mod = 0.5 + min(国家秩序, 区块秩序) / 400

        商贸专精区块获得1.3~1.5倍税收加成（地理特性匹配时更高）。
        秩序低于20的区块无法征税（民不聊生）。

        Args:
            state: 游戏状态
            country_name: 征税国家名

        Returns:
            包含gold_earned（总收入）、country_gold（国库余额）、
            block_details（各区块征税详情）的字典

        Side Effects:
            - 增加country.gold
        """
        country = state.countries.get(country_name)
        if not country:
            return {"error": "Country not found"}

        total_gold = 0
        block_details = []

        for block_name, block in state.blocks.items():
            if block.owner != country_name:
                continue

            # 秩序低于20的区块无法征税
            if block.order < 20:
                block_details.append({"block": block_name, "gold": 0, "reason": "order_too_low"})
                continue

            # 动态系数：控制区块越多，边际税收递减，模拟扩张管理成本
            dynamic_coeff = max(0.05, 0.1 - (self._count_controlled_blocks(state, country_name) / GAME_CONSTANTS["TAX_DENOMINATOR"] * 2))
            # 秩序修正：取国家秩序和区块秩序的较小值，木桶效应
            order_mod = 0.5 + min(country.order, block.order) / 400

            block_gold = int(block.base_manpower * dynamic_coeff * order_mod)

            # 商贸专精加成：地理特性匹配时1.5倍，否则1.3倍
            if block.specialization == BlockSpecialization.TRADE:
                trade_mult = 1.5 if block.geographic_trait.value == "trade" else 1.3
                block_gold = int(block_gold * trade_mult)

            total_gold += block_gold
            block_details.append({"block": block_name, "gold": block_gold})

        country.gold += total_gold

        return {
            "gold_earned": total_gold,
            "country_gold": country.gold,
            "block_details": block_details,
        }

    def develop_block(self, state: GameState, country_name: str, block_name: str) -> dict:
        """发展区块，提升人力和秩序。

        消耗400金铢，效果：
        - 基础人力+200
        - 人力池+100（不超过基础人力上限）
        - 区块秩序+3
        - 国家秩序+1
        - 发展次数+1

        前置条件：
        - 区块属于本国
        - 金铢>=400
        - 发展次数<3（最多发展3次）
        - 区块与首都补给连通（非飞地）

        Args:
            state: 游戏状态
            country_name: 发展国家名
            block_name: 目标区块名

        Returns:
            包含gold_spent（消耗金铢）、remaining_gold（剩余金铢）、
            manpower_increase（人力增量）、develop_count（当前发展次数）的字典

        Side Effects:
            - 减少country.gold 400
            - 增加block.base_manpower 200
            - 增加block.manpower_pool 100
            - 增加block.order 3
            - 增加country.order 1
            - 增加block.develop_count 1
        """
        country = state.countries.get(country_name)
        block = state.blocks.get(block_name)

        if not country or not block:
            return {"error": "Country or block not found"}
        if block.owner != country_name:
            return {"error": "Block not owned by country"}
        if country.gold < 400:
            return {"error": "Not enough gold (need 400)"}
        if block.develop_count >= 3:
            return {"error": "Block already fully developed (max 3)"}
        if not block.supply_connected:
            return {"error": "Block is an enclave, cannot develop"}

        country.gold -= 400
        block.base_manpower += 200
        block.manpower_pool = min(block.manpower_pool + 100, block.base_manpower)
        block.order = min(100, block.order + 3)
        country.order = min(100, country.order + 1)
        block.develop_count += 1

        return {
            "gold_spent": 400,
            "remaining_gold": country.gold,
            "manpower_increase": 200,
            "develop_count": block.develop_count,
        }

    def set_specialization(self, state: GameState, country_name: str, block_name: str, spec: str) -> dict:
        """设置区块专精，获得特定方向加成。

        前置条件：区块必须已满发展（3级）且无已有专精。

        三种专精及其效果：
        - farming(农垦): 基础人力+300，地理特性匹配时额外+100
        - trade(商贸): 税收倍率1.5~1.8（地理特性匹配时更高）
        - fortress(堡垒): 防御下限1.05~1.08（地理特性匹配时更高）

        地理特性匹配（synergy）是指区块的geographic_trait与专精类型一致，
        例如"武阳"的地理特性为farming，选择农垦专精时获得额外加成。

        Args:
            state: 游戏状态
            country_name: 设置国家名
            block_name: 目标区块名
            spec: 专精类型，"farming"/"trade"/"fortress"之一

        Returns:
            包含specialization（专精类型）、geographic_synergy（是否地理匹配）、
            bonus（专精加成详情）的字典
        """
        block = state.blocks.get(block_name)
        country = state.blocks.get(block_name)

        if not block or not country:
            return {"error": "Block or country not found"}
        if block.owner != country_name:
            return {"error": "Block not owned by country"}
        if block.develop_count < 3:
            return {"error": "Block must be fully developed (3 levels) first"}
        if block.specialization is not None:
            return {"error": "Block already has a specialization"}

        valid_specs = ["farming", "trade", "fortress"]
        if spec not in valid_specs:
            return {"error": f"Invalid specialization. Must be one of: {valid_specs}"}

        block.specialization = BlockSpecialization(spec)

        bonus = {}
        if spec == "farming":
            # 农垦专精：地理特性匹配时额外+100人力
            extra = 100 if block.geographic_trait.value == "farming" else 0
            block.base_manpower += 300 + extra
            bonus = {"manpower_increase": 300 + extra}
        elif spec == "trade":
            # 商贸专精：地理特性匹配时税收倍率更高
            bonus = {"trade_multiplier": 1.8 if block.geographic_trait.value == "trade" else 1.5}
        elif spec == "fortress":
            # 堡垒专精：地理特性匹配时防御加成更高
            bonus = {"defense_floor": 1.08 if block.geographic_trait.value == "fortress" else 1.05}

        return {
            "specialization": spec,
            "geographic_synergy": block.geographic_trait.value == spec,
            "bonus": bonus,
        }

    def recruit(self, state: GameState, country_name: str, block_name: str, troops: Optional[int] = None) -> dict:
        """在区块征兵，将人力转化为守军。

        消耗200金铢，从人力池中征召士兵加入守军。
        实际征兵数 = min(基础人力×30%, 人力池×50%) × 秩序修正

        秩序修正：order/100，边境区块再乘0.8。
        如果指定了troops参数，实际征兵数不超过请求数。

        征兵副作用：
        - 基础人力减少（征兵消耗的10%），模拟人口损耗
        - 人力池/基础人力比低于30%时，国家秩序-2、士气-2（过度征兵民怨）

        前置条件：
        - 区块属于本国
        - 金铢>=200
        - 区块非新占领
        - 距上次征兵至少2回合
        - 人力池>=10

        Args:
            state: 游戏状态
            country_name: 征兵国家名
            block_name: 征兵区块名
            troops: 指定征兵数量（可选），不指定时按公式计算

        Returns:
            包含troops_recruited（实际征兵数）、gold_spent（消耗金铢）、
            remaining_gold（剩余金铢）、manpool_remaining（剩余人力池）、
            manpower_depletion（基础人力损耗）的字典

        Side Effects:
            - 减少country.gold 200
            - 增加block.garrison
            - 减少block.manpower_pool
            - 减少block.base_manpower（征兵损耗的10%）
            - 可能减少country.order和country.morale（过度征兵惩罚）
            - 更新block.last_recruit_round
        """
        country = state.countries.get(country_name)
        block = state.blocks.get(block_name)

        if not country or not block:
            return {"error": "Country or block not found"}
        if block.owner != country_name:
            return {"error": "Block not owned by country"}
        if country.gold < 200:
            return {"error": "Not enough gold (need 200)"}
        if block.recently_conquered:
            return {"error": "Cannot recruit from newly conquered block"}
        if state.round - block.last_recruit_round < 2:
            return {"error": "Must wait 2 rounds between recruitments"}
        if block.manpower_pool < 10:
            return {"error": "Not enough manpower"}

        # 秩序修正：边境区块征兵效率降低20%
        order_mod = block.order / 100
        if block.region_type.value == "frontier":
            order_mod *= 0.8

        # 基础征兵量：取基础人力30%和人力池50%的较小值
        base_recruit = min(
            int(block.base_manpower * 0.3),
            int(block.manpower_pool * 0.5)
        )
        actual_recruit = max(1, int(base_recruit * order_mod))

        # 如果指定了征兵数量，不超过请求数和人力池
        if troops is not None and troops > 0:
            actual_recruit = min(actual_recruit, troops, block.manpower_pool)

        country.gold -= 200
        block.garrison += actual_recruit
        block.manpower_pool = max(0, block.manpower_pool - actual_recruit)
        block.last_recruit_round = state.round

        # 征兵导致人口损耗：实际征兵数的10%
        manpower_depletion = int(actual_recruit * 0.1)
        block.base_manpower = max(0, block.base_manpower - manpower_depletion)

        # 过度征兵惩罚：人力池不足基础人力30%时，降低国家秩序和士气
        if block.manpower_pool / max(1, block.base_manpower) < 0.3:
            country.order = max(0, country.order - 2)
            country.morale = max(0, country.morale - 2)

        return {
            "troops_recruited": actual_recruit,
            "gold_spent": 200,
            "remaining_gold": country.gold,
            "manpool_remaining": block.manpower_pool,
            "manpower_depletion": manpower_depletion,
        }

    def _count_controlled_blocks(self, state: GameState, country_name: str) -> int:
        """统计国家控制的区块数量。

        Args:
            state: 游戏状态
            country_name: 国家名

        Returns:
            控制的区块数量
        """
        return sum(1 for b in state.blocks.values() if b.owner == country_name)
