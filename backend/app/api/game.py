"""
游戏核心API模块
处理游戏初始化、状态查询、行动执行等核心逻辑
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from ..core import GameEngine, CombatSystem, EconomySystem, DiplomacySystem, FogSystem, ChroniclerSystem, EventsSystem
from ..models import ActionType
from ..ai import AIDecisionEngine

router = APIRouter(prefix="/game", tags=["game"])
logger = logging.getLogger(__name__)

# 全局游戏实例 - 单例模式
engine = GameEngine()
combat = CombatSystem()
economy = EconomySystem()
diplomacy = DiplomacySystem()
fog = FogSystem()
chronicler = ChroniclerSystem()
events = EventsSystem(engine.state) if engine.state else None


class InitRequest(BaseModel):
    """初始化游戏请求"""
    geojson_path: Optional[str] = None


class ActionRequest(BaseModel):
    """执行行动请求"""
    country: str
    action_type: ActionType
    parameters: dict = {}


class MessageRequest(BaseModel):
    """发送外交消息请求"""
    from_country: str
    to_country: str
    content: str
    visibility: str = "private"


@router.post("/init")
def init_game(req: InitRequest = InitRequest()):
    """
    初始化新游戏
    加载地图数据，创建国家、区块、武将等初始状态
    """
    state = engine.initialize_game(req.geojson_path)
    logger.info(f"Game initialized: round={state.round}, countries={list(state.countries.keys())}")
    return {
        "round": state.round,
        "countries": list(state.countries.keys()),
        "blocks_count": len(state.blocks),
        "generals": len(state.generals),
    }


@router.get("/state")
def get_state():
    """
    获取当前游戏状态
    返回回合数、国家信息、外交关系等核心数据
    """
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    state = engine.state
    return {
        "round": state.round,
        "timeline": {"year": state.timeline.year, "month": state.timeline.month},
        "countries": {
            name: {
                "name": name,
                "gold": c.gold,
                "order": c.order,
                "morale": c.morale,
                "capital": c.capital,
                "goal": c.goal.value,
                "in_exile": c.in_exile,
                "is_defeated": c.is_defeated,
                "has_declared_emperor": c.has_declared_emperor,
                "action_points": c.action_points,
            }
            for name, c in state.countries.items()
        },
        "blocks_count": len(state.blocks),
        "relations": {
            key: {
                "trust": r.trust,
                "grudge": r.grudge,
                "is_allied": r.is_allied,
                "at_war": r.at_war,
            }
            for key, r in state.relations.items()
        },
        "action_log": state.action_log[-20:] if state.action_log else [],
    }


@router.get("/blocks")
def get_blocks(country: Optional[str] = None):
    """
    获取区块列表
    可选按国家筛选，返回区块的所有属性
    """
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    state = engine.state
    blocks = {}
    for name, block in state.blocks.items():
        # 如果指定了国家，只返回该国家的区块
        if country and block.owner != country:
            continue
        blocks[name] = {
            "name": block.name,
            "owner": block.owner,
            "garrison": block.garrison,
            "order": block.order,
            "morale": block.morale,
            "base_manpower": block.base_manpower,
            "manpower_pool": block.manpower_pool,
            "neighbors": block.neighbors,
            "region_type": block.region_type.value,
            "supply_connected": block.supply_connected,
            "geographic_trait": block.geographic_trait.value,
            "specialization": block.specialization.value if block.specialization else None,
            "develop_count": block.develop_count,
            "recently_conquered": block.recently_conquered,
        }
    return {"blocks": blocks, "total": len(blocks)}


@router.get("/blocks/{block_name}")
def get_block(block_name: str):
    """获取单个区块详情"""
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    block = engine.state.blocks.get(block_name)
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    return block.model_dump()


@router.get("/countries/{country_name}")
def get_country(country_name: str):
    """
    获取国家详情
    包含国家属性和统计信息（区块数、总兵力）
    """
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    country = engine.state.countries.get(country_name)
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    # 统计该国家的区块数和总兵力
    blocks_count = sum(1 for b in engine.state.blocks.values() if b.owner == country_name)
    total_garrison = sum(b.garrison for b in engine.state.blocks.values() if b.owner == country_name)

    return {
        **country.model_dump(),
        "blocks_count": blocks_count,
        "total_garrison": total_garrison,
    }


def execute_move(state, req: ActionRequest, country) -> dict:
    """
    执行调兵行动
    在己方相邻区块间调动兵力
    """
    params = req.parameters
    from_block = state.blocks.get(params.get("from"))
    to_block = state.blocks.get(params.get("to"))
    troops = params.get("troops", 0)

    # 参数校验
    if not from_block or not to_block:
        return {"error": "Block not found"}
    if from_block.owner != req.country:
        return {"error": "Source block not owned"}
    if to_block.owner != req.country:
        return {"error": "Target block not owned (use attack)"}
    if to_block.name not in from_block.neighbors:
        return {"error": "Blocks are not adjacent"}
    if troops > from_block.garrison:
        return {"error": "Not enough troops"}
    if troops <= 0:
        return {"error": "Must move at least 1 troop"}

    # 执行调动
    from_block.garrison -= troops
    to_block.garrison += troops
    
    state.action_log.append({
        "round": state.round,
        "country": req.country,
        "action": "move",
        "detail": f"从{from_block.name}调动{troops}兵至{to_block.name}",
    })
    
    logger.debug(f"{req.country} moved {troops} troops from {from_block.name} to {to_block.name}")
    return {"moved": troops, "from": from_block.name, "to": to_block.name}


def execute_attack(state, req: ActionRequest, country) -> dict:
    """
    执行进攻行动
    攻击相邻敌方或中立区块，可能触发背叛
    """
    params = req.parameters
    from_block = state.blocks.get(params.get("from"))
    to_block = state.blocks.get(params.get("to"))
    troops = params.get("troops", 0)

    # 参数校验
    if not from_block or not to_block:
        return {"error": "Block not found"}
    if from_block.owner != req.country:
        return {"error": "Source block not owned"}
    if to_block.owner == req.country:
        return {"error": "Cannot attack own block"}
    if to_block.name not in from_block.neighbors:
        return {"error": "Blocks are not adjacent"}

    # 最小出兵数量限制
    min_troops = max(int(from_block.garrison * 0.1), 50)
    if troops < min_troops:
        return {"error": f"Need at least {min_troops} troops"}
    if troops > from_block.garrison:
        return {"error": "Not enough troops"}

    from_block.garrison -= troops

    # 获取防守方国家
    defender_country = state.countries.get(to_block.owner)
    if not defender_country:
        defender_country = state.countries.get("neutral")

    from ..models import Country
    if not defender_country:
        defender_country = Country(name=to_block.owner, order=50, morale=50)

    # 检查是否为背叛攻击（攻击盟友）
    is_betrayal = False
    rel_key = diplomacy._get_relation_key(req.country, to_block.owner)
    relation = state.relations.get(rel_key)
    if relation and relation.is_allied:
        is_betrayal = True
        diplomacy.process_betrayal(state, req.country, to_block.owner)
    else:
        diplomacy.process_attack_declaration(state, req.country, to_block.owner)

    # 执行战斗
    result = combat.resolve_attack(
        country, defender_country, from_block, to_block,
        troops, state.generals,
    )

    # 处理战斗结果
    if result.block_captured:
        # 攻占成功
        to_block.owner = req.country
        to_block.garrison = troops - result.attacker_loss
        to_block.recently_conquered = True
        to_block.order = country.order
        to_block.morale = country.morale

        # 核心区块攻占奖励
        if to_block.region_type.value == "core":
            country.order = min(100, country.order + 8) if not is_betrayal else country.order
            country.morale = min(100, country.morale + 5) if not is_betrayal else country.morale
            
        state.action_log.append({
            "round": state.round,
            "country": req.country,
            "action": "attack_success",
            "detail": f"出动{troops}兵攻占{to_block.name}，敌军损失{result.defender_loss}",
        })
        logger.info(f"{req.country} captured {to_block.name} from {from_block.name}")
    else:
        # 攻占失败，残兵撤回
        from_block.garrison += troops - result.attacker_loss
        state.action_log.append({
            "round": state.round,
            "country": req.country,
            "action": "attack_failed",
            "detail": f"出动{troops}兵进攻{to_block.name}受挫，损兵{result.attacker_loss}",
        })
        logger.info(f"{req.country} failed to capture {to_block.name}, lost {result.attacker_loss} troops")

    # 根据损失比例降低士气
    loss_ratio = result.attacker_loss / troops if troops > 0 else 0
    if loss_ratio >= 0.5:
        country.morale = max(0, country.morale - 5)
    elif loss_ratio >= 0.4:
        country.morale = max(0, country.morale - 4)
    elif loss_ratio >= 0.3:
        country.morale = max(0, country.morale - 3)
    elif loss_ratio >= 0.2:
        country.morale = max(0, country.morale - 2)

    state.battle_results_this_round.append(result)

    return {
        "battle_result": result.model_dump(),
        "is_betrayal": is_betrayal,
    }


def execute_harass(state, req: ActionRequest, country) -> dict:
    """
    执行骚扰行动
    小规模袭击敌方区块，不占领但造成损失
    """
    params = req.parameters
    from_block = state.blocks.get(params.get("from"))
    to_block = state.blocks.get(params.get("to"))
    troops = params.get("troops", 0)

    # 参数校验
    if not from_block or not to_block:
        return {"error": "Block not found"}
    if from_block.owner != req.country:
        return {"error": "Source block not owned"}
    if to_block.owner == req.country:
        return {"error": "Cannot harass own block"}
    if troops > 500:
        return {"error": "Harass troops cannot exceed 500"}
    if troops < 50:
        return {"error": "Harass troops must be at least 50"}
    if troops > from_block.garrison:
        return {"error": "Not enough troops"}

    from_block.garrison -= troops

    # 执行骚扰战斗
    from ..models import Country
    defender_country = Country(name=to_block.owner, order=50, morale=50)
    result = combat.resolve_attack(
        country, defender_country, from_block, to_block,
        troops, state.generals, is_harass=True,
    )

    # 骚扰后撤回残兵
    from_block.garrison += troops - result.attacker_loss
    to_block.garrison = max(0, to_block.garrison - result.defender_loss)
    
    state.action_log.append({
        "round": state.round,
        "country": req.country,
        "action": "harass",
        "detail": f"遣{troops}兵骚扰{to_block.name}，敌损{result.defender_loss}，我损{result.attacker_loss}",
    })
    logger.debug(f"{req.country} harassed {to_block.name}")

    return {"harass_result": result.model_dump()}


def execute_recruit(state, req: ActionRequest, country) -> dict:
    """
    执行征兵行动
    消耗人力池和黄金征召士兵
    """
    block_name = req.parameters.get("block")
    if not block_name:
        return {"error": "Must specify block"}
    result = economy.recruit(state, req.country, block_name)
    if "troops_recruited" in result:
        state.action_log.append({
            "round": state.round,
            "country": req.country,
            "action": "recruit",
            "detail": f"于{block_name}招募{result['troops_recruited']}兵",
        })
        logger.debug(f"{req.country} recruited {result['troops_recruited']} at {block_name}")
    return result


def execute_develop(state, req: ActionRequest, country) -> dict:
    """
    执行发展行动
    消耗黄金提升区块人力池上限
    """
    block_name = req.parameters.get("block")
    if not block_name:
        return {"error": "Must specify block"}
    result = economy.develop_block(state, req.country, block_name)
    if "manpower_increase" in result:
        state.action_log.append({
            "round": state.round,
            "country": req.country,
            "action": "develop",
            "detail": f"发展{block_name}，人力+{result['manpower_increase']}",
        })
        logger.debug(f"{req.country} developed {block_name}")
    return result


def execute_tax(state, req: ActionRequest, country) -> dict:
    """
    执行征税行动
    根据控制区块数量获得黄金
    """
    result = economy.collect_tax(state, req.country)
    if "gold_earned" in result:
        state.action_log.append({
            "round": state.round,
            "country": req.country,
            "action": "tax",
            "detail": f"征税得金{result['gold_earned']}",
        })
        logger.debug(f"{req.country} collected tax: {result['gold_earned']} gold")
    return result


def execute_disband(state, req: ActionRequest, country) -> dict:
    """
    执行解散行动
    解散士兵，部分人力返还到人力池
    """
    block_name = req.parameters.get("block")
    troops = req.parameters.get("troops", 0)
    block = state.blocks.get(block_name)
    
    # 参数校验
    if not block:
        return {"error": "Block not found"}
    if block.owner != req.country:
        return {"error": "Block not owned"}
    if block.garrison < 100:
        return {"error": "Garrison too low to disband"}
    if troops > block.garrison:
        return {"error": "Not enough troops"}
    if troops <= 0:
        return {"error": "Must disband at least 1 troop"}

    # 解散士兵，返还一半人力
    block.garrison -= troops
    manpower_returned = troops // 2
    block.manpower_pool = min(block.base_manpower, block.manpower_pool + manpower_returned)
    logger.debug(f"{req.country} disbanded {troops} at {block_name}")
    return {"disbanded": troops, "manpower_returned": manpower_returned}


def execute_move_capital(state, req: ActionRequest, country) -> dict:
    """
    执行迁都行动
    将首都迁至其他己方区块，有冷却时间限制
    """
    new_capital = req.parameters.get("new_capital")
    block = state.blocks.get(new_capital)
    
    # 参数校验
    if not block:
        return {"error": "Block not found"}
    if block.owner != req.country:
        return {"error": "Block not owned"}
    if block.recently_conquered:
        return {"error": "Cannot move capital to newly conquered block"}
    if not block.supply_connected:
        return {"error": "Cannot move capital to enclave"}
    if block.order < 60:
        return {"error": "Block order must be >= 60"}
    if block.garrison < 500:
        return {"error": "Block garrison must be >= 500"}

    # 检查冷却时间
    from ..core.constants import GAME_CONSTANTS
    if state.round - country.last_betrayal_round < GAME_CONSTANTS["MOVE_CAPITAL_COOLDOWN"]:
        if hasattr(country, 'last_move_capital_round'):
            if state.round - country.last_move_capital_round < GAME_CONSTANTS["MOVE_CAPITAL_COOLDOWN"]:
                return {"error": "Move capital cooldown not expired"}

    # 执行迁都
    old_capital = country.capital
    country.capital = new_capital
    country.order = max(0, country.order - 8)

    # 旧首都属性下降
    old_block = state.blocks.get(old_capital)
    if old_block:
        old_block.order = max(0, old_block.order - 15)
        old_block.morale = max(0, old_block.morale - 10)

    if not hasattr(country, 'last_move_capital_round'):
        country.last_move_capital_round = state.round
    else:
        country.last_move_capital_round = state.round

    state.action_log.append({
        "round": state.round,
        "country": req.country,
        "action": "move_capital",
        "detail": f"迁都至{new_capital}",
    })
    logger.info(f"{req.country} moved capital from {old_capital} to {new_capital}")

    return {"old_capital": old_capital, "new_capital": new_capital}


def execute_declare_emperor(state, req: ActionRequest, country) -> dict:
    """
    执行称帝行动
    需要满足区块数量和历史首都控制条件
    """
    blocks_count = sum(1 for b in state.blocks.values() if b.owner == req.country)
    if blocks_count < 45:
        return {"error": f"Need 45 blocks, have {blocks_count}"}

    # 检查是否控制历史首都
    historical_capitals = {
        "魏": ["许昌", "洛阳"],
        "蜀": ["成都", "长安"],
        "吴": ["建业", "武昌"],
    }
    required = historical_capitals.get(req.country, [])
    has_capital = any(state.blocks.get(c) and state.blocks[c].owner == req.country for c in required)
    if not has_capital:
        return {"error": "Must control a historical capital"}

    if country.has_declared_emperor:
        return {"error": "Already declared emperor"}

    # 执行称帝
    country.has_declared_emperor = True
    country.order = min(100, country.order + 5)
    country.morale = min(100, country.morale + 10)

    # 其他国家对称帝的反应
    for key, relation in state.relations.items():
        if req.country in (relation.country_a, relation.country_b):
            relation.trust = max(0, relation.trust - 0.2)
    
    state.action_log.append({
        "round": state.round,
        "country": req.country,
        "action": "declare_emperor",
        "detail": f"{req.country}称帝，天下震动",
    })
    logger.info(f"{req.country} declared emperor!")

    return {"declared_emperor": True, "country": req.country}


# 行动类型到处理函数的映射
ACTION_HANDLERS = {
    ActionType.MOVE: execute_move,
    ActionType.ATTACK: execute_attack,
    ActionType.HARASS: execute_harass,
    ActionType.RECRUIT: execute_recruit,
    ActionType.DEVELOP: execute_develop,
    ActionType.TAX: execute_tax,
    ActionType.DISBAND: execute_disband,
    ActionType.MOVE_CAPITAL: execute_move_capital,
    ActionType.DECLARE_EMPEROR: execute_declare_emperor,
}


@router.post("/action")
def execute_action(req: ActionRequest):
    """
    执行单个行动
    根据行动类型调用对应的处理函数
    """
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    state = engine.state

    country = state.countries.get(req.country)
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")
    if country.is_defeated:
        raise HTTPException(status_code=400, detail="Country is defeated")

    # 行动点数检查（暂时跳过，由AI层控制）
    from ..core.constants import ACTION_COSTS
    cost = ACTION_COSTS.get(req.action_type.value, 0)
    if cost > 0 and not req.parameters.get("_skip_ap_check"):
        pass

    handler = ACTION_HANDLERS.get(req.action_type)
    if handler:
        return handler(state, req, country)
    
    return {"error": "Unknown action type"}


@router.post("/message")
def send_message(req: MessageRequest):
    """发送外交消息"""
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    result = diplomacy.send_message(engine.state, req.from_country, req.to_country, req.content, req.visibility)
    return result


@router.post("/next-round")
def next_round():
    """
    推进回合
    处理人力恢复、秩序恢复、补给线更新、战略目标更新等
    定期生成编年史叙事
    """
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    state = engine.state

    current_round = state.round

    # 外交关系衰减
    diplomacy.decay_relations(state)
    diplomacy.decay_memories(state)

    # 检查是否需要生成编年史叙事
    from ..core.constants import get_config
    chronicler_interval = get_config("game_settings.chronicler_interval", 5)
    should_generate_narrative = current_round % chronicler_interval == 0 or current_round == 1

    narrative = None
    if should_generate_narrative:
        narrative = chronicler.generate_narrative(state, state.battle_results_this_round, current_round)
    state.battle_results_this_round = []

    # 处理回合
    round_result = engine.process_round()

    # 检查随机事件
    events_obj = EventsSystem(state)
    borderland_events = events_obj.check_borderland_events()
    historical_events = events_obj.check_historical_events()
    round_result["borderland_events"] = borderland_events
    round_result["historical_events"] = historical_events

    logger.info(f"Round {current_round} processed, now at round {state.round}")
    return {
        "round_result": round_result,
        "narrative": narrative,
        "chronicler_interval": chronicler_interval,
    }


@router.post("/ai-turn/{country_name}")
def execute_ai_turn(country_name: str):
    """
    执行单个国家的AI回合
    AI决策并执行一系列行动
    """
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    state = engine.state

    country = state.countries.get(country_name)
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")
    if country.is_defeated:
        return {"actions": [], "message": "Country is defeated"}

    # AI决策
    ai = AIDecisionEngine(state)
    actions = ai.decide_actions(country_name, country.action_points)

    results = []
    for action in actions:
        # 检查行动点数
        from ..core.constants import ACTION_COSTS
        cost = ACTION_COSTS.get(action["action_type"], 0)
        if cost > 0 and country.action_points * 1000 < cost:
            continue

        req = ActionRequest(
            country=country_name,
            action_type=action["action_type"],
            parameters=action["parameters"],
        )
        result = execute_action(req)
        if "error" not in result:
            country.action_points = max(0, country.action_points - cost / 1000)
        results.append({
            "action": action["action_type"],
            "parameters": action["parameters"],
            "result": result,
        })

    logger.info(f"AI turn for {country_name}: {len(results)} actions executed")
    return {
        "country": country_name,
        "goal": country.goal.value,
        "actions_executed": len(results),
        "results": results,
    }


@router.post("/ai-round")
def execute_ai_round(exclude_country: Optional[str] = None):
    """
    执行所有AI国家的回合
    可选排除某个国家（如玩家控制的国家）
    """
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    state = engine.state

    ai_countries = ["魏", "蜀", "吴"]
    if exclude_country and exclude_country in ai_countries:
        ai_countries.remove(exclude_country)

    all_results = {}
    for country_name in ai_countries:
        country = state.countries.get(country_name)
        if country and not country.is_defeated:
            ai = AIDecisionEngine(state)
            actions = ai.decide_actions(country_name)

            results = []
            for action in actions:
                req = ActionRequest(
                    country=country_name,
                    action_type=action["action_type"],
                    parameters=action["parameters"],
                )
                result = execute_action(req)
                results.append({
                    "action": action["action_type"],
                    "parameters": action["parameters"],
                    "result": result,
                })

            all_results[country_name] = {
                "goal": country.goal.value,
                "actions_executed": len(results),
                "results": results,
            }

    return {"ai_results": all_results}


@router.get("/fog/{country_name}")
def get_fog_state(country_name: str):
    """获取战争迷雾状态（可见区块）"""
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    return fog.get_visible_state(engine.state, country_name)


@router.get("/narrative")
def get_narrative():
    """生成编年史叙事"""
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    return chronicler.generate_narrative(engine.state, [])


@router.get("/generals")
def get_generals(alive_only: bool = True):
    """获取武将列表"""
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    generals = engine.state.generals
    if alive_only:
        generals = [g for g in generals if g.alive]
    return {"generals": [g.model_dump() for g in generals]}


@router.get("/relations")
def get_relations():
    """获取所有外交关系"""
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    return {
        key: r.model_dump()
        for key, r in engine.state.relations.items()
    }


@router.get("/memories/{country_name}")
def get_memories(country_name: str):
    """获取国家记忆（外交事件记录）"""
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    cm = engine.state.country_memories.get(country_name)
    if not cm:
        return {"memories": []}
    return {"memories": [m.model_dump() for m in cm.memories]}


@router.get("/history")
def get_history(limit: int = 50):
    """获取历史记录"""
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    history = engine.state.history[-limit:]
    return {"history": history}
