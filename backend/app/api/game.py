"""
游戏核心API模块

处理游戏初始化、状态查询、行动执行等核心逻辑。
本模块是前后端交互的主要入口，提供以下功能：
- 游戏初始化与状态查询
- 各种行动的执行（调兵、进攻、骚扰、征兵、发展、征税、解散、迁都、称帝）
- 回合推进与AI回合执行
- 战争迷雾、编年史叙事、武将列表等查询接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from ..core import EventsSystem
from ..core.constants import GAME_CONSTANTS, ACTION_COSTS, HISTORICAL_CAPITALS, PLAYABLE_COUNTRIES, SPECIAL_NEUTRAL_FORCE_NAMES, get_config
from ..models import ActionType, Country, RegionType
from ..ai import AIDecisionEngine
from .game_state_holder import get_engine, get_combat, get_economy, get_fog, get_chronicler

router = APIRouter(prefix="/game", tags=["game"])
logger = logging.getLogger(__name__)

# 获取全局单例的系统组件
engine = get_engine()
combat = get_combat()
economy = get_economy()
fog = get_fog()
chronicler = get_chronicler()


class InitRequest(BaseModel):
    """初始化游戏请求模型

    Attributes:
        geojson_path: 可选的GeoJSON地图文件路径，为空则使用默认地图
    """
    geojson_path: Optional[str] = None


class ActionRequest(BaseModel):
    """执行行动请求模型

    Attributes:
        country: 执行行动的国家名称
        action_type: 行动类型（进攻、调兵、征兵等）
        parameters: 行动参数字典，不同行动类型需要不同的参数
    """
    country: str
    action_type: ActionType
    parameters: dict = {}


@router.post("/init")
def init_game(req: InitRequest = InitRequest()):
    """
    初始化新游戏

    加载地图数据，创建国家、区块、武将等初始状态。
    每次调用会重置游戏状态。

    Args:
        req: 初始化请求，可指定自定义地图路径

    Returns:
        dict: 包含初始回合数、国家列表、区块数量、武将数量
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

    返回回合数、时间线、国家信息（含黄金/秩序/士气/首都等）、
    外交关系（信任/仇怨/同盟/交战）、最近20条行动日志等核心数据。

    Returns:
        dict: 游戏状态概览，包含回合、时间线、国家、外交关系、行动日志

    Raises:
        HTTPException: 游戏未初始化时返回400
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

    可选按国家筛选，返回区块的所有属性（守军、秩序、士气、人力池、
    邻居、区域类型、补给连通性、地理特性、专精、发展次数等）。

    Args:
        country: 可选的国家名称，指定后只返回该国家拥有的区块

    Returns:
        dict: 包含区块字典和总数

    Raises:
        HTTPException: 游戏未初始化时返回400
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
    """
    获取单个区块详情

    Args:
        block_name: 区块名称

    Returns:
        dict: 区块的完整数据

    Raises:
        HTTPException: 游戏未初始化(400)或区块不存在(404)
    """
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

    包含国家基础属性和统计信息（区块数、总兵力）。

    Args:
        country_name: 国家名称

    Returns:
        dict: 国家完整数据，附加区块数和总兵力统计

    Raises:
        HTTPException: 游戏未初始化(400)或国家不存在(404)
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

    在己方相邻区块间调动兵力。源区块和目标区块必须都属于该国家且相邻。

    Args:
        state: 当前游戏状态
        req: 行动请求，parameters需包含 from(源区块)、to(目标区块)、troops(兵力数)
        country: 执行行动的国家对象

    Returns:
        dict: 包含调动兵力数、源区块和目标区块名称

    Raises:
        HTTPException: 区块不存在(404)、非己方区块(400)、不相邻(400)、兵力不足(400)等
    """
    params = req.parameters
    from_block = state.blocks.get(params.get("from"))
    to_block = state.blocks.get(params.get("to"))
    troops = params.get("troops", 0)

    # 参数校验
    if not from_block or not to_block:
        raise HTTPException(status_code=404, detail="Block not found")
    if from_block.owner != req.country:
        raise HTTPException(status_code=400, detail="Source block not owned")
    if to_block.owner != req.country:
        raise HTTPException(status_code=400, detail="Target block not owned (use attack)")
    if to_block.name not in from_block.neighbors:
        raise HTTPException(status_code=400, detail="Blocks are not adjacent")
    if troops > from_block.garrison:
        raise HTTPException(status_code=400, detail="Not enough troops")
    if troops <= 0:
        raise HTTPException(status_code=400, detail="Must move at least 1 troop")

    # 执行调动：从源区块减兵，目标区块加兵
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

    攻击相邻敌方或中立区块。根据双方战力比决定战斗结果，
    攻占成功则占领区块，失败则残兵撤回。攻占核心区块或特殊中立势力领地
    会获得额外奖励。战斗损失比例过高会降低国家士气。

    Args:
        state: 当前游戏状态
        req: 行动请求，parameters需包含 from(出发区块)、to(目标区块)、troops(出兵数)
        country: 执行行动的国家对象

    Returns:
        dict: 包含战斗结果详情（BattleResult的字典形式）

    Raises:
        HTTPException: 区块不存在(404)、非己方区块(400)、攻击己方(400)、
                       不相邻(400)、出兵不足(400)等
    """
    params = req.parameters
    from_block = state.blocks.get(params.get("from"))
    to_block = state.blocks.get(params.get("to"))
    troops = params.get("troops", 0)

    # 参数校验
    if not from_block or not to_block:
        raise HTTPException(status_code=404, detail="Block not found")
    if from_block.owner != req.country:
        raise HTTPException(status_code=400, detail="Source block not owned")
    if to_block.owner == req.country:
        raise HTTPException(status_code=400, detail="Cannot attack own block")
    if to_block.name not in from_block.neighbors:
        raise HTTPException(status_code=400, detail="Blocks are not adjacent")

    # 最小出兵数量限制：取守军比例和绝对下限中的较大值
    min_troops = max(int(from_block.garrison * GAME_CONSTANTS["MIN_TROOP_RATIO"]), GAME_CONSTANTS["MIN_TROOP_ABSOLUTE"])
    if troops < min_troops:
        raise HTTPException(status_code=400, detail=f"Need at least {min_troops} troops")
    if troops > from_block.garrison:
        raise HTTPException(status_code=400, detail="Not enough troops")

    # 先从源区块扣除出兵数，战斗结束后根据结果决定去向
    from_block.garrison -= troops

    # 获取防守方国家对象，若不存在则使用中立或创建临时国家
    defender_country = state.countries.get(to_block.owner)
    if not defender_country:
        defender_country = state.countries.get("neutral")

    if not defender_country:
        defender_country = Country(name=to_block.owner, order=50, morale=50)

    # 调用战斗系统解析战斗
    result = combat.resolve_attack(
        country, defender_country, from_block, to_block,
        troops, state.generals, current_round=state.round,
    )

    # 处理战斗结果
    if result.block_captured:
        previous_owner = to_block.owner
        # 攻占成功：更新区块所有权和属性
        to_block.owner = req.country
        surviving_troops = max(troops - result.attacker_loss, 1)
        to_block.garrison = surviving_troops
        to_block.recently_conquered = True
        to_block.order = country.order
        to_block.morale = country.morale

        # 核心区块攻占奖励：提升国家秩序和士气
        if to_block.region_type == RegionType.CORE:
            country.order = min(100, country.order + GAME_CONSTANTS["CORE_BONUS_GARRISON"])
            country.morale = min(100, country.morale + GAME_CONSTANTS["CORE_BONUS_ORDER"])

        # 攻占特殊中立势力领地奖励：获得黄金、士气、秩序提升
        if previous_owner in SPECIAL_NEUTRAL_FORCE_NAMES:
            country.gold += GAME_CONSTANTS["SPECIAL_FORCE_GOLD"]
            country.morale = min(100, country.morale + GAME_CONSTANTS["SPECIAL_FORCE_MORALE"])
            country.order = min(100, country.order + GAME_CONSTANTS["SPECIAL_FORCE_ORDER"])

        state.action_log.append({
            "round": state.round,
            "country": req.country,
            "action": "attack_success",
            "detail": f"出动{troops}兵攻占{to_block.name}，敌军损失{result.defender_loss}",
        })
        logger.info(f"{req.country} captured {to_block.name} from {from_block.name}")
    else:
        # 攻占失败：残兵撤回源区块
        from_block.garrison += troops - result.attacker_loss
        state.action_log.append({
            "round": state.round,
            "country": req.country,
            "action": "attack_failed",
            "detail": f"出动{troops}兵进攻{to_block.name}受挫，损兵{result.attacker_loss}",
        })
        logger.info(f"{req.country} failed to capture {to_block.name}, lost {result.attacker_loss} troops")

    # 根据损失比例降低士气：损失越大士气下降越多
    loss_ratio = result.attacker_loss / troops if troops > 0 else 0
    if loss_ratio >= 0.5:
        country.morale = max(0, country.morale - 5)
    elif loss_ratio >= 0.4:
        country.morale = max(0, country.morale - 4)
    elif loss_ratio >= 0.3:
        country.morale = max(0, country.morale - 3)
    elif loss_ratio >= 0.2:
        country.morale = max(0, country.morale - 2)

    # 记录本回合战斗结果，供编年史系统使用
    state.battle_results_this_round.append(result)

    return {
        "battle_result": result.model_dump(),
    }


def execute_harass(state, req: ActionRequest, country) -> dict:
    """
    执行骚扰行动

    小规模袭击敌方区块，不占领但造成损失。骚扰后残兵撤回源区块，
    敌方守军直接扣除损失。出兵数限制在50~500之间。

    Args:
        state: 当前游戏状态
        req: 行动请求，parameters需包含 from(出发区块)、to(目标区块)、troops(兵力数)
        country: 执行行动的国家对象

    Returns:
        dict: 包含骚扰结果详情

    Raises:
        HTTPException: 区块不存在(404)、非己方区块(400)、攻击己方(400)、
                       不相邻(400)、出兵超限(400)等
    """
    params = req.parameters
    from_block = state.blocks.get(params.get("from"))
    to_block = state.blocks.get(params.get("to"))
    troops = params.get("troops", 0)

    # 参数校验
    if not from_block or not to_block:
        raise HTTPException(status_code=404, detail="Block not found")
    if from_block.owner != req.country:
        raise HTTPException(status_code=400, detail="Source block not owned")
    if to_block.owner == req.country:
        raise HTTPException(status_code=400, detail="Cannot harass own block")
    if to_block.name not in from_block.neighbors:
        raise HTTPException(status_code=400, detail="Target block is not adjacent to source block")
    if troops > GAME_CONSTANTS["HARASS_MAX_TROOPS"]:
        raise HTTPException(status_code=400, detail="Harass troops cannot exceed 500")
    if troops < GAME_CONSTANTS["HARASS_MIN_TROOPS"]:
        raise HTTPException(status_code=400, detail="Harass troops must be at least 50")
    if troops > from_block.garrison:
        raise HTTPException(status_code=400, detail="Not enough troops")

    from_block.garrison -= troops

    # 获取防守方国家对象
    defender_country = state.countries.get(to_block.owner)
    if not defender_country:
        defender_country = state.countries.get("neutral")

    if not defender_country:
        defender_country = Country(name=to_block.owner, order=50, morale=50)

    # 调用战斗系统，标记为骚扰模式（不会占领区块）
    result = combat.resolve_attack(
        country, defender_country, from_block, to_block,
        troops, state.generals, is_harass=True, current_round=state.round,
    )

    # 骚扰后撤回残兵，敌方直接扣除损失
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

    消耗200黄金和人力池在指定区块征召士兵。征兵受区块秩序影响，
    边境区块征兵效率降低20%。人力池过低时征兵会降低国家秩序和士气。

    Args:
        state: 当前游戏状态
        req: 行动请求，parameters需包含 block(征兵区块名)、troops(可选征兵数)
        country: 执行行动的国家对象

    Returns:
        dict: 征兵结果，包含实际征兵数、花费黄金、剩余人力池等

    Raises:
        HTTPException: 未指定区块(400)
    """
    block_name = req.parameters.get("block")
    troops = req.parameters.get("troops")
    if not block_name:
        raise HTTPException(status_code=400, detail="Must specify block")
    result = economy.recruit(state, req.country, block_name, troops=troops)
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

    消耗400黄金提升区块人力池上限（+200基础人力），同时增加区块秩序。
    每个区块最多发展3次。飞地（补给不连通）无法发展。

    Args:
        state: 当前游戏状态
        req: 行动请求，parameters需包含 block(发展区块名)
        country: 执行行动的国家对象

    Returns:
        dict: 发展结果，包含花费黄金、人力增加量、发展次数

    Raises:
        HTTPException: 未指定区块(400)
    """
    block_name = req.parameters.get("block")
    if not block_name:
        raise HTTPException(status_code=400, detail="Must specify block")
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

    根据控制区块的基数人力和秩序计算税收。控制区块越多，单块税率越低
    （模拟管理成本递增）。贸易专精区块有额外税收加成。

    Args:
        state: 当前游戏状态
        req: 行动请求（无需额外参数）
        country: 执行行动的国家对象

    Returns:
        dict: 征税结果，包含获得黄金数、各区块税收明细
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

    解散指定区块的士兵，返还一半人力到人力池。
    守军低于100时不可解散。

    Args:
        state: 当前游戏状态
        req: 行动请求，parameters需包含 block(区块名)、troops(解散兵力数)
        country: 执行行动的国家对象

    Returns:
        dict: 包含解散兵力数和返还人力数

    Raises:
        HTTPException: 区块不存在(404)、非己方区块(400)、守军过低(400)、
                       兵力不足(400)、解散数<=0(400)
    """
    block_name = req.parameters.get("block")
    troops = req.parameters.get("troops", 0)
    block = state.blocks.get(block_name)

    # 参数校验
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    if block.owner != req.country:
        raise HTTPException(status_code=400, detail="Block not owned")
    if block.garrison < GAME_CONSTANTS["DISBAND_MIN_GARRISON"]:
        raise HTTPException(status_code=400, detail="Garrison too low to disband")
    if troops > block.garrison:
        raise HTTPException(status_code=400, detail="Not enough troops")
    if troops <= 0:
        raise HTTPException(status_code=400, detail="Must disband at least 1 troop")

    # 解散士兵，返还一半人力到人力池（不超过基础人力上限）
    block.garrison -= troops
    manpower_returned = troops // 2
    block.manpower_pool = min(block.base_manpower, block.manpower_pool + manpower_returned)

    state.action_log.append({
        "round": state.round,
        "country": req.country,
        "action": "disband",
        "detail": f"于{block_name}解散{troops}兵，返还人力{manpower_returned}",
    })
    logger.debug(f"{req.country} disbanded {troops} at {block_name}")
    return {"disbanded": troops, "manpower_returned": manpower_returned}


def execute_move_capital(state, req: ActionRequest, country) -> dict:
    """
    执行迁都行动

    将首都迁至其他己方区块。新首都必须满足：非新占领、补给连通、
    秩序>=60、守军>=500。迁都有36回合冷却时间，且会降低国家秩序
    和旧首都的秩序/士气。

    Args:
        state: 当前游戏状态
        req: 行动请求，parameters需包含 new_capital(新首都区块名)
        country: 执行行动的国家对象

    Returns:
        dict: 包含旧首都和新首都名称

    Raises:
        HTTPException: 区块不存在(404)、非己方区块(400)、新占领区块(400)、
                       飞地(400)、秩序不足(400)、守军不足(400)、冷却中(400)
    """
    new_capital = req.parameters.get("new_capital")
    block = state.blocks.get(new_capital)

    # 参数校验
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    if block.owner != req.country:
        raise HTTPException(status_code=400, detail="Block not owned")
    if block.recently_conquered:
        raise HTTPException(status_code=400, detail="Cannot move capital to newly conquered block")
    if not block.supply_connected:
        raise HTTPException(status_code=400, detail="Cannot move capital to enclave")
    if block.order < 60:
        raise HTTPException(status_code=400, detail="Block order must be >= 60")
    if block.garrison < GAME_CONSTANTS["MOVE_CAPITAL_MIN_GARRISON"]:
        raise HTTPException(status_code=400, detail="Block garrison must be >= 500")

    # 检查冷却时间（36回合内不可再次迁都）
    if state.round - country.last_move_capital_round < GAME_CONSTANTS["MOVE_CAPITAL_COOLDOWN"]:
        raise HTTPException(status_code=400, detail="Move capital cooldown not expired")

    # 执行迁都：国家秩序下降
    old_capital = country.capital
    country.capital = new_capital
    country.order = max(0, country.order - GAME_CONSTANTS["MOVE_CAPITAL_ORDER_PENALTY"])

    # 旧首都属性下降
    old_block = state.blocks.get(old_capital)
    if old_block:
        old_block.order = max(0, old_block.order - GAME_CONSTANTS["OLD_CAPITAL_ORDER_PENALTY"])
        old_block.morale = max(0, old_block.morale - GAME_CONSTANTS["OLD_CAPITAL_MORALE_PENALTY"])

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

    需要满足两个条件：1) 控制45个以上区块；2) 控制本国历史首都。
    称帝后国家秩序+5、士气+10，但其他国家对该国信任度下降。
    每个国家只能称帝一次。

    Args:
        state: 当前游戏状态
        req: 行动请求（无需额外参数）
        country: 执行行动的国家对象

    Returns:
        dict: 包含称帝成功标志和国家名称

    Raises:
        HTTPException: 区块数不足(400)、未控制历史首都(400)、已称帝(400)
    """
    blocks_count = sum(1 for b in state.blocks.values() if b.owner == req.country)
    if blocks_count < GAME_CONSTANTS["EMPEROR_REQUIRED_BLOCKS"]:
        raise HTTPException(status_code=400, detail=f"Need {GAME_CONSTANTS['EMPEROR_REQUIRED_BLOCKS']} blocks, have {blocks_count}")

    # 检查是否控制本国历史首都
    required = HISTORICAL_CAPITALS.get(req.country, [])
    has_capital = any(state.blocks.get(c) and state.blocks[c].owner == req.country for c in required)
    if not has_capital:
        raise HTTPException(status_code=400, detail="Must control a historical capital")

    if country.has_declared_emperor:
        raise HTTPException(status_code=400, detail="Already declared emperor")

    # 执行称帝：提升秩序和士气
    country.has_declared_emperor = True
    country.order = min(100, country.order + 5)
    country.morale = min(100, country.morale + 10)

    # 其他国家对称帝的反应：信任度下降
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


# 行动类型到处理函数的映射表
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

    根据行动类型调用对应的处理函数。执行前会检查游戏状态、
    国家是否存在/已灭亡、行动点数是否充足。

    Args:
        req: 行动请求，包含国家、行动类型、参数

    Returns:
        dict: 行动执行结果，具体内容取决于行动类型

    Raises:
        HTTPException: 游戏未初始化(400)、国家不存在(404)、
                       国家已灭亡(400)、行动点不足(400)、未知行动(400)
    """
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    state = engine.state

    country = state.countries.get(req.country)
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")
    if country.is_defeated:
        raise HTTPException(status_code=400, detail="Country is defeated")

    # 行动点数检查：ACTION_COSTS以毫点为单位（1000毫点=1行动点）
    cost = ACTION_COSTS.get(req.action_type.value, 0)
    if cost > 0:
        if country.action_points * 1000 < cost:
            raise HTTPException(status_code=400, detail=f"行动点数不足：需要 {cost/1000:.1f}，剩余 {country.action_points:.1f}")

    handler = ACTION_HANDLERS.get(req.action_type)
    if handler:
        result = handler(state, req, country)
        # 仅在行动成功时扣除行动点数（返回结果不含 error 字段）
        if cost > 0:
            has_error = isinstance(result, dict) and "error" in result
            if not has_error:
                country.action_points -= cost / 1000
        return result

    raise HTTPException(status_code=400, detail="Unknown action type")




@router.post("/next-round")
def next_round():
    """
    推进回合

    按顺序执行以下操作：
    1. 检查是否需要生成编年史叙事（每5回合或第1回合）
    2. 处理回合逻辑（人力恢复、秩序恢复、补给线更新等）
    3. 检查边境事件和历史事件
    4. 自动存档（每5回合）

    Returns:
        dict: 包含回合处理结果、编年史叙事、编年史间隔配置

    Raises:
        HTTPException: 游戏未初始化(400)
    """
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    state = engine.state

    current_round = state.round

    # 检查是否需要生成编年史叙事
    chronicler_interval = get_config("game_settings.chronicler_interval", 5)
    should_generate_narrative = current_round % chronicler_interval == 0 or current_round == 1

    narrative = None
    if should_generate_narrative:
        narrative = chronicler.generate_narrative(state, state.battle_results_this_round, current_round)
        if narrative:
            state.narratives.append(narrative)
    # 清空本回合战斗结果，为下一回合做准备
    state.battle_results_this_round = []

    # 处理回合（人力恢复、秩序恢复、补给线更新、战略目标更新等）
    round_result = engine.process_round()

    # 检查随机事件
    events_obj = EventsSystem(state)
    borderland_events = events_obj.check_borderland_events()
    historical_events = events_obj.check_historical_events()
    round_result["borderland_events"] = borderland_events
    round_result["historical_events"] = historical_events

    # 自动存档（每5回合自动存档一次）
    autosave_interval = get_config("game_settings.autosave_interval", 5)
    if current_round % autosave_interval == 0 and current_round > 0:
        try:
            from .save_api import create_autosave_sync
            create_autosave_sync()
            logger.info(f"Autosave created for round {current_round}")
        except Exception as e:
            logger.error(f"Failed to create autosave: {e}")

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

    AI决策引擎根据当前局势生成一系列行动，然后逐个执行。
    行动点数不足时跳过该行动。

    Args:
        country_name: AI国家名称

    Returns:
        dict: 包含国家名称、战略目标、执行行动数、各行动结果

    Raises:
        HTTPException: 游戏未初始化(400)、国家不存在(404)
    """
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    state = engine.state

    country = state.countries.get(country_name)
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")
    if country.is_defeated:
        return {"actions": [], "message": "Country is defeated"}

    # AI决策：根据当前局势生成行动列表
    ai = AIDecisionEngine(state)
    actions = ai.decide_actions(country_name, country.action_points)

    results = []
    for action in actions:
        cost = ACTION_COSTS.get(action["action_type"], 0)
        if cost > 0 and country.action_points < cost / 1000:
            continue

        req = ActionRequest(
            country=country_name,
            action_type=action["action_type"],
            parameters=action["parameters"],
        )
        try:
            result = execute_action(req)
        except HTTPException as e:
            result = {"error": e.detail}
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

    可选排除某个国家（如玩家控制的国家），对剩余国家逐一执行AI决策。

    Args:
        exclude_country: 要排除的国家名称（通常是玩家控制的国家）

    Returns:
        dict: 包含各AI国家的决策结果

    Raises:
        HTTPException: 游戏未初始化(400)
    """
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    state = engine.state

    # 获取所有可玩国家列表，排除指定国家
    ai_countries = list(PLAYABLE_COUNTRIES)
    if exclude_country and exclude_country in ai_countries:
        ai_countries.remove(exclude_country)

    all_results = {}
    for country_name in ai_countries:
        country = state.countries.get(country_name)
        if country and not country.is_defeated:
            ai = AIDecisionEngine(state)
            actions = ai.decide_actions(country_name, country.action_points)

            results = []
            for action in actions:
                cost = ACTION_COSTS.get(action["action_type"], 0)
                if cost > 0 and country.action_points < cost / 1000:
                    continue

                req = ActionRequest(
                    country=country_name,
                    action_type=action["action_type"],
                    parameters=action["parameters"],
                )
                try:
                    result = execute_action(req)
                except HTTPException as e:
                    result = {"error": e.detail}
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
    """
    获取战争迷雾状态

    返回指定国家可见的区块信息，包括可见性、守军估算、
    秩序/士气范围、胜率标签等。

    Args:
        country_name: 查看迷雾状态的国家名称

    Returns:
        dict: 各区块的可见性信息

    Raises:
        HTTPException: 游戏未初始化(400)
    """
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    return fog.get_visible_state(engine.state, country_name)


@router.get("/narrative")
def get_narrative():
    """
    生成编年史叙事

    根据当前游戏状态生成本回合的编年史叙事文本，
    包括事件列表、各势力态势、AI/回退叙事。

    Returns:
        dict: 编年史叙事内容

    Raises:
        HTTPException: 游戏未初始化(400)
    """
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    return chronicler.generate_narrative(engine.state, [])


@router.get("/generals")
def get_generals(alive_only: bool = True):
    """
    获取武将列表

    Args:
        alive_only: 是否只返回存活武将，默认为True

    Returns:
        dict: 包含武将列表，每个武将含姓名、国家、所在区块、特性、存活状态等

    Raises:
        HTTPException: 游戏未初始化(400)
    """
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    generals = engine.state.generals
    if alive_only:
        generals = [g for g in generals if g.alive]
    return {"generals": [g.model_dump() for g in generals]}


@router.get("/relations")
def get_relations():
    """
    获取所有外交关系

    Returns:
        dict: 所有国家间外交关系的完整数据

    Raises:
        HTTPException: 游戏未初始化(400)
    """
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    return {
        key: r.model_dump()
        for key, r in engine.state.relations.items()
    }


@router.get("/memories/{country_name}")
def get_memories(country_name: str):
    """
    获取国家记忆（外交事件记录）

    返回指定国家的历史外交事件记忆，包括事件内容、影响程度、
    情感倾向、衰减值等。记忆会随时间衰减，低于阈值后自动移除。

    Args:
        country_name: 国家名称

    Returns:
        dict: 包含记忆列表

    Raises:
        HTTPException: 游戏未初始化(400)
    """
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    cm = engine.state.country_memories.get(country_name)
    if not cm:
        return {"memories": []}
    return {"memories": [m.model_dump() for m in cm.memories]}


@router.get("/history")
def get_history(limit: int = 50):
    """
    获取历史记录

    返回最近的历史事件记录，如首都沦陷、国家灭亡等重大事件。

    Args:
        limit: 返回记录的最大数量，默认50

    Returns:
        dict: 包含历史记录列表

    Raises:
        HTTPException: 游戏未初始化(400)
    """
    if not engine.state:
        raise HTTPException(status_code=400, detail="Game not initialized")
    history = engine.state.history[-limit:]
    return {"history": history}
