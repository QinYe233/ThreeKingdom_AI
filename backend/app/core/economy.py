from ..models import Block, Country, GameState
from ..core.constants import GAME_CONSTANTS


class EconomySystem:
    def collect_tax(self, state: GameState, country_name: str) -> dict:
        country = state.countries.get(country_name)
        if not country:
            return {"error": "Country not found"}

        total_gold = 0
        block_details = []

        for block_name, block in state.blocks.items():
            if block.owner != country_name:
                continue

            if block.order < 20:
                block_details.append({"block": block_name, "gold": 0, "reason": "order_too_low"})
                continue

            dynamic_coeff = max(0.05, 0.1 - (self._count_controlled_blocks(state, country_name) / GAME_CONSTANTS["TAX_DENOMINATOR"] * 2))
            order_mod = 0.5 + min(country.order, block.order) / 400

            block_gold = int(block.base_manpower * dynamic_coeff * order_mod)

            if block.specialization == "trade":
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
        block = state.blocks.get(block_name)
        country = state.countries.get(country_name)

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

        block.specialization = spec

        bonus = {}
        if spec == "farming":
            extra = 100 if block.geographic_trait.value == "farming" else 0
            block.base_manpower += 300 + extra
            bonus = {"manpower_increase": 300 + extra}
        elif spec == "trade":
            bonus = {"trade_multiplier": 1.8 if block.geographic_trait.value == "trade" else 1.5}
        elif spec == "fortress":
            bonus = {"defense_floor": 1.08 if block.geographic_trait.value == "fortress" else 1.05}

        return {
            "specialization": spec,
            "geographic_synergy": block.geographic_trait.value == spec,
            "bonus": bonus,
        }

    def recruit(self, state: GameState, country_name: str, block_name: str) -> dict:
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

        order_mod = block.order / 100
        if block.region_type.value == "frontier":
            order_mod *= 0.8

        base_recruit = min(
            int(block.base_manpower * 0.3),
            int(block.manpower_pool * 0.5)
        )
        actual_recruit = max(1, int(base_recruit * order_mod))

        country.gold -= 200
        block.garrison += actual_recruit
        block.manpower_pool = max(0, block.manpower_pool - actual_recruit)
        block.last_recruit_round = state.round

        manpower_depletion = int(actual_recruit * 0.1)
        block.base_manpower = max(0, block.base_manpower - manpower_depletion)

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
        return sum(1 for b in state.blocks.values() if b.owner == country_name)
