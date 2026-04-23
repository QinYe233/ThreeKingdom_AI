import random
from typing import Optional

from ..models import (
    Block, Country, BattleResult, General, GeneralTrait,
    MemoryImpact, MemoryEmotion, Memory,
)
from ..core.constants import GAME_CONSTANTS


class CombatSystem:
    def resolve_attack(
        self,
        attacker_country: Country,
        defender_country: Country,
        attacker_block: Block,
        defender_block: Block,
        troops: int,
        generals: list[General],
        is_harass: bool = False,
    ) -> BattleResult:
        attacker_power = self._calc_attacker_power(
            attacker_country, attacker_block, troops, defender_block
        )
        defender_power = self._calc_defender_power(
            defender_country, defender_block, attacker_block
        )

        attacker_power = self._apply_general_attack_modifiers(
            attacker_power, attacker_country.name, defender_block, generals
        )
        defender_power = self._apply_general_defense_modifiers(
            defender_power, defender_country.name, defender_block, attacker_block, generals
        )

        power_ratio = attacker_power / defender_power if defender_power > 0 else 999

        collapse = False
        war_pressure_change = 0

        if power_ratio >= 1.5:
            result = self._attacker_decisive_victory(
                troops, defender_block, attacker_country, defender_country
            )
            war_pressure_change = 25
        elif power_ratio <= 1 / 1.5:
            result = self._defender_decisive_victory(
                troops, defender_block, attacker_country, defender_country
            )
            war_pressure_change = 15
        elif power_ratio >= 1.0:
            result = self._attacker_marginal_victory(
                troops, defender_block, attacker_country, defender_country
            )
            war_pressure_change = 15
        else:
            result = self._defender_marginal_victory(
                troops, defender_block, attacker_country, defender_country
            )
            war_pressure_change = 15

        if is_harass:
            result["block_captured"] = False
            result["attacker_won"] = False

        if self._check_collapse(defender_country, war_pressure_change):
            collapse = True
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

        self._check_general_death(defender_block, defender_country.name, generals, battle_result)
        self._check_general_death(attacker_block, attacker_country.name, generals, battle_result)

        return battle_result

    def _calc_attacker_power(
        self, country: Country, from_block: Block, troops: int, target_block: Block
    ) -> float:
        morale_mod = 1 + country.morale / 600
        supply_mod = 0.85 if not from_block.supply_connected else 1.0
        defender_garrison = target_block.garrison
        troop_ratio_mod = 1.1 if troops > defender_garrison * 3 else 1.0
        return troops * morale_mod * supply_mod * troop_ratio_mod

    def _calc_defender_power(
        self, country: Country, block: Block, attacker_block: Block
    ) -> float:
        morale_mod = 1 + country.morale / 600
        defense_coeff = random.uniform(0.95, 1.15)
        supply_mod = 0.9 if not block.supply_connected else 1.0

        if block.specialization == "fortress":
            spec_mod = 1.08 if block.geographic_trait.value == "fortress" else 1.05
        else:
            spec_mod = 1.0

        return block.garrison * morale_mod * defense_coeff * supply_mod * spec_mod

    def _apply_general_attack_modifiers(
        self, power: float, country_name: str, target_block: Block, generals: list[General]
    ) -> float:
        for g in generals:
            if not g.alive or g.country != country_name:
                continue
            if g.trait == GeneralTrait.WEI_ZHEN_HUAXIA:
                country = None
                if target_block.owner != "neutral":
                    from ..models import GameState
                    pass
                power *= 1.0
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
                if attacker_block.garrison > defender_block.garrison * 1.5:
                    power *= 1.2
        return power

    def _attacker_decisive_victory(
        self, troops: int, defender_block: Block, attacker: Country, defender: Country
    ) -> dict:
        defender_loss = defender_block.garrison
        attacker_loss = int(defender_block.garrison * random.uniform(0.8, 1.2))
        attacker_loss = min(attacker_loss, troops)
        return {
            "attacker_loss": attacker_loss,
            "defender_loss": defender_loss,
            "attacker_won": True,
            "block_captured": True,
        }

    def _defender_decisive_victory(
        self, troops: int, defender_block: Block, attacker: Country, defender: Country
    ) -> dict:
        attacker_loss = int(troops * random.uniform(0.8, 1.0))
        defender_loss = 0
        return {
            "attacker_loss": attacker_loss,
            "defender_loss": defender_loss,
            "attacker_won": False,
            "block_captured": False,
        }

    def _attacker_marginal_victory(
        self, troops: int, defender_block: Block, attacker: Country, defender: Country
    ) -> dict:
        defender_loss = defender_block.garrison
        attacker_loss = int(defender_block.garrison * random.uniform(0.8, 1.2))
        attacker_loss = min(attacker_loss, troops)
        return {
            "attacker_loss": attacker_loss,
            "defender_loss": defender_loss,
            "attacker_won": True,
            "block_captured": True,
        }

    def _defender_marginal_victory(
        self, troops: int, defender_block: Block, attacker: Country, defender: Country
    ) -> dict:
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
        if war_pressure >= 80:
            return True
        if war_pressure >= 60:
            if country.morale < 40:
                return True
            return random.random() < 0.3
        return False

    def _check_general_death(
        self, block: Block, country_name: str, generals: list[General], result: BattleResult
    ) -> None:
        for g in generals:
            if not g.alive or g.country != country_name or g.block != block.name:
                continue
            if result.defender_loss >= block.garrison:
                death_prob = GAME_CONSTANTS["GENERAL_DEATH_PROBABILITY"]
                if g.trait == GeneralTrait.BA_SHI_DAN_YAN:
                    death_prob /= 2
                if random.random() < death_prob:
                    g.alive = False
                    g.death_round = result.round if hasattr(result, 'round') else 0
