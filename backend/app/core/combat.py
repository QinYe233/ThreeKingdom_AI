"""
战斗系统模块

实现三国博弈中的战斗计算逻辑，包括攻防战力计算、武将特性加成、
四种战斗结果判定、崩溃机制和武将阵亡判定。

战斗流程：
1. 计算攻方和守方的原始战力
2. 应用武将特性对攻防战力的修正
3. 根据战力比判定四种战斗结果之一
4. 检查守方是否崩溃
5. 检查武将是否阵亡

战力比判定规则：
- 攻方战力 >= 守方1.5倍 → 攻方决定性胜利
- 攻方战力 <= 守方1/1.5倍 → 守方决定性胜利
- 攻方战力 >= 守方 → 攻方勉强胜利
- 攻方战力 < 守方 → 守方勉强胜利
"""
import random

from ..models import (
    Block, Country, BattleResult, General, GeneralTrait,
    BlockSpecialization,
)
from ..core.constants import GAME_CONSTANTS


class CombatSystem:
    """战斗系统，负责处理所有战斗相关的计算逻辑。

    包括战力计算、武将特性加成、战斗结果判定、崩溃检查和武将阵亡判定。
    战斗结果受士气、补给线、武将特性、专精类型等多种因素影响。
    """

    def resolve_attack(
        self,
        attacker_country: Country,
        defender_country: Country,
        attacker_block: Block,
        defender_block: Block,
        troops: int,
        generals: list[General],
        is_harass: bool = False,
        current_round: int = 0,
    ) -> BattleResult:
        """解析一次攻击行动，计算战斗结果。

        完整的战斗解析流程：
        1. 计算攻守双方原始战力
        2. 应用武将特性修正
        3. 根据战力比判定战斗结果
        4. 处理骚扰特殊逻辑（骚扰不占领区块）
        5. 增加守方战争压力
        6. 检查守方是否崩溃
        7. 检查武将是否阵亡

        Args:
            attacker_country: 攻方国家对象
            defender_country: 守方国家对象
            attacker_block: 攻方出发区块
            defender_block: 守方防守区块
            troops: 攻方出兵数量
            generals: 全局武将列表
            is_harass: 是否为骚扰行动（骚扰不占领区块、不触发崩溃）
            current_round: 当前回合数（用于记录武将阵亡时间）

        Returns:
            BattleResult: 战斗结果对象，包含双方损失、胜负、是否占领、是否崩溃等信息

        Side Effects:
            - 修改defender_country.war_pressure（增加战争压力）
            - 可能修改generals中武将的alive和death_round属性（阵亡判定）
        """
        # 第一步：计算攻守双方原始战力
        attacker_power = self._calc_attacker_power(
            attacker_country, attacker_block, troops, defender_block
        )
        defender_power = self._calc_defender_power(
            defender_country, defender_block, attacker_block
        )

        # 第二步：应用武将特性修正攻防战力
        attacker_power = self._apply_general_attack_modifiers(
            attacker_power, attacker_country.name, defender_block, generals
        )
        defender_power = self._apply_general_defense_modifiers(
            defender_power, defender_country.name, defender_block, attacker_block, generals
        )

        # 计算战力比，用于判定战斗结果类型
        power_ratio = attacker_power / defender_power if defender_power > 0 else 999

        collapse = False
        war_pressure_change = 0

        # 第三步：根据战力比判定四种战斗结果
        if power_ratio >= 1.5:
            # 攻方战力 >= 守方1.5倍：攻方决定性胜利
            result = self._attacker_decisive_victory(
                troops, defender_block, attacker_country, defender_country
            )
            war_pressure_change = 25
        elif power_ratio <= 1 / 1.5:
            # 攻方战力 <= 守方1/1.5倍：守方决定性胜利
            result = self._defender_decisive_victory(
                troops, defender_block, attacker_country, defender_country
            )
            war_pressure_change = 15
        elif power_ratio >= 1.0:
            # 攻方战力 >= 守方但不足1.5倍：攻方勉强胜利
            result = self._attacker_marginal_victory(
                troops, defender_block, attacker_country, defender_country
            )
            war_pressure_change = 15
        else:
            # 攻方战力 < 守方：守方勉强胜利
            result = self._defender_marginal_victory(
                troops, defender_block, attacker_country, defender_country
            )
            war_pressure_change = 15

        # 第四步：骚扰行动特殊处理——不占领区块、不算胜利
        if is_harass:
            result["block_captured"] = False
            result["attacker_won"] = False

        # 增加守方战争压力
        defender_country.war_pressure += war_pressure_change

        # 骚扰行动不触发崩溃（小规模袭扰不足以导致国家崩溃）
        if not is_harass and self._check_collapse(defender_country, defender_country.war_pressure):
            collapse = True
            # 崩溃时守军全灭，区块被占领
            result["defender_loss"] = defender_block.garrison
            result["block_captured"] = True
            result["attacker_won"] = True

        battle_result = BattleResult(
            attacker=attacker_country.name,
            defender=defender_country.name,
            attacker_block=attacker_block.name,
            defender_block=defender_block.name,
            attacker_troops=troops,
            defender_troops=defender_block.garrison,
            attacker_loss=result["attacker_loss"],
            defender_loss=result["defender_loss"],
            attacker_won=result["attacker_won"],
            block_captured=result["block_captured"],
            collapse=collapse,
            war_pressure_change=war_pressure_change,
        )

        # 第五步：检查武将阵亡（先检查守方，再检查攻方）
        self._check_general_death(defender_block, defender_country.name, generals, battle_result, current_round, is_attacker=False)
        self._check_general_death(attacker_block, attacker_country.name, generals, battle_result, current_round, is_attacker=True)

        return battle_result

    def _calc_attacker_power(
        self, country: Country, from_block: Block, troops: int, target_block: Block
    ) -> float:
        """计算攻方原始战力。

        攻方战力 = 出兵数 × 士气修正 × 补给修正 × 兵力比修正

        各修正因子说明：
        - 士气修正: 1 + 士气/600，士气100时修正为1.167
        - 补给修正: 与首都断连时降为0.85，否则为1.0
        - 兵力比修正: 出兵超过守军3倍时为1.1（碾压优势），否则为1.0

        Args:
            country: 攻方国家
            from_block: 出发区块
            troops: 出兵数量
            target_block: 目标区块

        Returns:
            攻方战力值（浮点数）
        """
        morale_mod = 1 + country.morale / 600
        supply_mod = 0.85 if not from_block.supply_connected else 1.0
        defender_garrison = target_block.garrison
        # 兵力碾压优势：出兵超过守军3倍时获得10%加成
        troop_ratio_mod = 1.1 if troops > defender_garrison * 3 else 1.0
        return troops * morale_mod * supply_mod * troop_ratio_mod

    def _calc_defender_power(
        self, country: Country, block: Block, attacker_block: Block
    ) -> float:
        """计算守方原始战力。

        守方战力 = 守军数 × 士气修正 × 防御随机系数 × 补给修正 × 专精修正

        各修正因子说明：
        - 士气修正: 1 + 士气/600，与攻方相同
        - 防御随机系数: 0.95~1.15的随机值，模拟防守方的不确定性
        - 补给修正: 与首都断连时降为0.9（比攻方惩罚更重），否则为1.0
        - 专精修正: 堡垒专精区块获得5%~8%防御加成

        Args:
            country: 守方国家
            block: 防守区块
            attacker_block: 攻方出发区块（此方法中未使用）

        Returns:
            守方战力值（浮点数）
        """
        morale_mod = 1 + country.morale / 600
        # 防御随机系数，模拟地形、天气等不确定因素
        defense_coeff = random.uniform(0.95, 1.15)
        supply_mod = 0.9 if not block.supply_connected else 1.0

        # 堡垒专精加成：地理特性匹配时加成更高
        if block.specialization == BlockSpecialization.FORTRESS:
            spec_mod = 1.08 if block.geographic_trait.value == "fortress" else 1.05
        else:
            spec_mod = 1.0

        return block.garrison * morale_mod * defense_coeff * supply_mod * spec_mod

    def _apply_general_attack_modifiers(
        self, power: float, country_name: str, target_block: Block, generals: list[General]
    ) -> float:
        """应用武将特性对攻方战力的修正。

        仅当武将存活且属于攻方国家时生效。攻击方特性：
        - 威震华夏(wei_zhen_huaxia): 全局攻击+12%（关羽）
        - 万人敌(wan_ren_di): 目标有守军时攻击+10%（张飞）
        - 锦帆突袭(jin_fan_tu_ji): 全局攻击+8%（甘宁）

        Args:
            power: 原始攻方战力
            country_name: 攻方国家名
            target_block: 攻击目标区块
            generals: 全局武将列表

        Returns:
            修正后的攻方战力
        """
        for g in generals:
            if not g.alive or g.country != country_name:
                continue
            if g.trait == GeneralTrait.WEI_ZHEN_HUAXIA:
                power *= 1.12
            elif g.trait == GeneralTrait.WAN_REN_DI:
                if target_block.garrison > 0:
                    power *= 1.1
            elif g.trait == GeneralTrait.JIN_FAN_TU_JI:
                power *= 1.08
        return power

    def _apply_general_defense_modifiers(
        self,
        power: float,
        country_name: str,
        defender_block: Block,
        attacker_block: Block,
        generals: list[General],
    ) -> float:
        """应用武将特性对守方战力的修正。

        仅当武将存活、属于守方国家且驻守在防守区块时生效。防御方特性：
        - 威震逍遥津(wei_zhen_xiaoyaojin): 守军>=500时防御+15%（张辽）
        - 铁壁(tie_bi): 无额外效果（预留特性）
        - 火烧赤壁(huo_shao_chibi): 全局防御+10%（周瑜）
        - 火烧连营(huo_shao_lianying): 攻方兵力>守方1.5倍时防御+20%（陆逊，以少胜多）

        Args:
            power: 原始守方战力
            country_name: 守方国家名
            defender_block: 防守区块
            attacker_block: 攻方出发区块（用于火烧连营的兵力对比）
            generals: 全局武将列表

        Returns:
            修正后的守方战力
        """
        for g in generals:
            if not g.alive or g.country != country_name or g.block != defender_block.name:
                continue
            if g.trait == GeneralTrait.WEI_ZHEN_XIAOYAOJIN:
                if defender_block.garrison >= 500:
                    power *= 1.15
            elif g.trait == GeneralTrait.TIE_BI:
                pass
            elif g.trait == GeneralTrait.HUO_SHAO_CHIBI:
                power *= 1.1
            elif g.trait == GeneralTrait.HUO_SHAO_LIANYING:
                # 以少胜多：攻方兵力远超守方时触发，模拟陆逊火烧连营的以弱胜强
                if attacker_block.garrison > defender_block.garrison * 1.5:
                    power *= 1.2
        return power

    def _attacker_decisive_victory(
        self, troops: int, defender_block: Block, _attacker: Country, _defender: Country
    ) -> dict:
        """攻方决定性胜利（战力比 >= 1.5）。

        守军全灭，攻方损失20%~40%兵力。
        如果攻方全军覆没（极端情况），则不算胜利。

        Args:
            troops: 攻方出兵数
            defender_block: 守方区块
            _attacker: 攻方国家（未使用）
            _defender: 守方国家（未使用）

        Returns:
            包含attacker_loss/defender_loss/attacker_won/block_captured的字典
        """
        defender_loss = defender_block.garrison
        attacker_loss = int(troops * random.uniform(0.2, 0.4))
        attacker_loss = min(attacker_loss, troops)
        # 如果攻方全军覆没，这不算胜利
        attacker_won = attacker_loss < troops
        return {
            "attacker_loss": attacker_loss,
            "defender_loss": defender_loss,
            "attacker_won": attacker_won,
            "block_captured": attacker_won,
        }

    def _defender_decisive_victory(
        self, troops: int, defender_block: Block, _attacker: Country, _defender: Country
    ) -> dict:
        """守方决定性胜利（战力比 <= 1/1.5）。

        攻方损失80%~100%兵力，守方无损失。

        Args:
            troops: 攻方出兵数
            defender_block: 守方区块
            _attacker: 攻方国家（未使用）
            _defender: 守方国家（未使用）

        Returns:
            包含attacker_loss/defender_loss/attacker_won/block_captured的字典
        """
        attacker_loss = int(troops * random.uniform(0.8, 1.0))
        defender_loss = 0
        return {
            "attacker_loss": attacker_loss,
            "defender_loss": defender_loss,
            "attacker_won": False,
            "block_captured": False,
        }

    def _attacker_marginal_victory(
        self, troops: int, defender_block: Block, _attacker: Country, _defender: Country
    ) -> dict:
        """攻方勉强胜利（1.0 <= 战力比 < 1.5）。

        守军全灭，攻方损失50%~80%兵力（代价惨重）。
        如果攻方全军覆没，则不算胜利。

        Args:
            troops: 攻方出兵数
            defender_block: 守方区块
            _attacker: 攻方国家（未使用）
            _defender: 守方国家（未使用）

        Returns:
            包含attacker_loss/defender_loss/attacker_won/block_captured的字典
        """
        defender_loss = defender_block.garrison
        attacker_loss = int(troops * random.uniform(0.5, 0.8))
        attacker_loss = min(attacker_loss, troops)
        # 如果攻方全军覆没，这不算胜利
        attacker_won = attacker_loss < troops
        return {
            "attacker_loss": attacker_loss,
            "defender_loss": defender_loss,
            "attacker_won": attacker_won,
            "block_captured": attacker_won,
        }

    def _defender_marginal_victory(
        self, troops: int, defender_block: Block, _attacker: Country, _defender: Country
    ) -> dict:
        """守方勉强胜利（1/1.5 < 战力比 < 1.0）。

        攻方损失70%~100%兵力，守方损失攻方出兵数的20%（上限为守军数）。

        Args:
            troops: 攻方出兵数
            defender_block: 守方区块
            _attacker: 攻方国家（未使用）
            _defender: 守方国家（未使用）

        Returns:
            包含attacker_loss/defender_loss/attacker_won/block_captured的字典
        """
        attacker_loss = int(troops * random.uniform(0.7, 1.0))
        defender_loss = int(troops * 0.2)
        defender_loss = min(defender_loss, defender_block.garrison)
        return {
            "attacker_loss": attacker_loss,
            "defender_loss": defender_loss,
            "attacker_won": False,
            "block_captured": False,
        }

    def _check_collapse(self, country: Country, war_pressure: int) -> bool:
        """检查守方是否因战争压力崩溃。

        崩溃判定规则：
        - 战争压力 >= 80: 必定崩溃
        - 战争压力 >= 60: 士气<40时必定崩溃，否则30%概率崩溃
        - 战争压力 >= 40: 士气<25时必定崩溃，否则10%概率崩溃
        - 战争压力 < 40: 不会崩溃

        崩溃意味着守军瓦解、区块自动被攻方占领。

        Args:
            country: 守方国家
            war_pressure: 当前战争压力值

        Returns:
            True表示发生崩溃，False表示未崩溃
        """
        if war_pressure >= 80:
            return True
        if war_pressure >= 60:
            if country.morale < 40:
                return True
            return random.random() < 0.3
        if war_pressure >= 40:
            if country.morale < 25:
                return True
            return random.random() < 0.1
        return False

    def _check_general_death(
        self, block: Block, country_name: str, generals: list[General], result: BattleResult, current_round: int = 0, is_attacker: bool = False
    ) -> None:
        """检查武将是否在战斗中阵亡。

        阵亡条件：
        - 攻方武将：出兵损失 >= 80%时有阵亡风险
        - 守方武将：守军被全歼时有阵亡风险

        阵亡概率为GAME_CONSTANTS中的GENERAL_DEATH_PROBABILITY（默认25%），
        但"拔矢啖睛"特性(ba_shi_dan_yan，夏侯惇)的武将阵亡概率减半。

        Args:
            block: 战斗发生区块
            country_name: 武将所属国家
            generals: 全局武将列表
            result: 战斗结果
            current_round: 当前回合数
            is_attacker: 是否检查攻方武将

        Side Effects:
            - 可能将武将的alive设为False
            - 可能设置武将的death_round
        """
        for g in generals:
            if not g.alive or g.country != country_name or g.block != block.name:
                continue
            # 攻击方武将：出兵损失超过80%时有阵亡风险；防守方武将：守军被全歼时有阵亡风险
            should_check = False
            if is_attacker:
                should_check = result.attacker_loss >= result.attacker_troops * 0.8
            else:
                should_check = result.defender_loss >= block.garrison

            if should_check:
                death_prob = GAME_CONSTANTS["GENERAL_DEATH_PROBABILITY"]
                # 夏侯惇"拔矢啖睛"特性：阵亡概率减半，体现其悍不畏死
                if g.trait == GeneralTrait.BA_SHI_DAN_YAN:
                    death_prob /= 2
                if random.random() < death_prob:
                    g.alive = False
                    g.death_round = current_round
