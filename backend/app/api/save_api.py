"""
游戏存档API模块

处理手动存档、自动存档、加载、删除、列表查询等存档管理功能。
本模块提供以下功能：
- 手动存档创建（支持自定义名称和描述）
- 自动存档创建（每N回合自动触发）
- 存档列表查询和计数
- 存档加载（含版本兼容性检查）
- 存档删除
- 旧存档自动清理（保持总数不超过上限）
- 游戏状态的序列化与反序列化
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .game_state_holder import get_engine

logger = logging.getLogger(__name__)


# 存档目录：项目根目录下的 data/saves/
SAVE_DIR = Path(__file__).parent.parent.parent / "data" / "saves"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

SAVE_VERSION = "1.0.0"       # 当前存档版本号
MAX_TOTAL_SAVES = 20         # 总存档上限
KEEP_AUTO_SAVES = 5          # 自动存档保留数量


def _check_version_compatible(save_version: str) -> bool:
    """
    检查存档版本是否兼容

    仅比较主版本号和次版本号（前两位），补丁版本号差异视为兼容。

    Args:
        save_version: 存档中的版本号字符串

    Returns:
        bool: 版本兼容返回True，不兼容或格式错误返回False
    """
    try:
        save_parts = tuple(int(x) for x in save_version.split("."))
        current_parts = tuple(int(x) for x in SAVE_VERSION.split("."))
        # 比较主版本号和次版本号（前两位），补丁版本差异视为兼容
        return save_parts[:2] == current_parts[:2]
    except (ValueError, AttributeError):
        return False


class SaveRequest(BaseModel):
    """手动存档请求模型

    Attributes:
        name: 可选的存档名称
        description: 可选的存档描述
    """
    name: Optional[str] = None
    description: Optional[str] = None


class SaveInfo(BaseModel):
    """存档信息模型

    Attributes:
        save_id: 存档唯一标识
        timestamp: 存档时间戳
        round: 存档时的回合数
        metadata: 存档元数据（手动/自动、描述等）
        description: 可选的存档描述
    """
    save_id: str
    timestamp: str
    round: int
    metadata: dict
    description: Optional[str] = None


class LoadSaveRequest(BaseModel):
    """加载存档请求模型

    Attributes:
        save_id: 要加载的存档ID
    """
    save_id: str


def _cleanup_old_saves() -> None:
    """
    清理旧存档，保持总存档数不超过上限

    按时间排序存档文件，超出上限时删除最旧的存档。
    """
    all_saves = []

    for save_file in SAVE_DIR.glob("*.json"):
        try:
            with open(save_file, "r", encoding="utf-8") as f:
                save_data = json.load(f)
                metadata = save_data.get("metadata", {})
                timestamp = save_data.get("timestamp", "")
                all_saves.append((save_file, timestamp, metadata.get("autosave", False)))
        except Exception as e:
            logger.error(f"Error reading save file {save_file}: {e}")
            continue

    # 按时间排序，最新的在前
    all_saves.sort(key=lambda x: x[1], reverse=True)

    # 如果总存档数超过上限，删除最旧的
    while len(all_saves) > MAX_TOTAL_SAVES:
        save_file, _, _ = all_saves.pop()
        try:
            save_file.unlink()
            logger.info(f"Deleted old save: {save_file.name}")
        except Exception as e:
            logger.error(f"Error deleting save {save_file.name}: {e}")


def _generate_save_id(is_autosave: bool = False, custom_name: Optional[str] = None) -> str:
    """
    生成存档唯一ID

    自动存档以 auto_ 前缀，手动存档以 manual_ 前缀。
    可附加自定义名称（仅保留字母数字和部分符号）。

    Args:
        is_autosave: 是否为自动存档
        custom_name: 可选的自定义名称

    Returns:
        str: 格式为 auto_时间戳 或 manual_名称_时间戳
    """
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

    if is_autosave:
        save_id = f"auto_{timestamp}"
    elif custom_name:
        # 过滤自定义名称，仅保留安全字符
        safe_name = "".join(c for c in custom_name if c.isalnum() or c in ('-', '_', ' '))
        save_id = f"manual_{safe_name}_{timestamp}"
    else:
        save_id = f"manual_{timestamp}"

    return save_id


def _save_game_state(game_state) -> dict:
    """
    将游戏状态序列化为可保存的字典

    逐层序列化国家、区块、外交关系、国家记忆、武将、
    外交消息、编年史叙事、战斗结果等所有游戏数据。
    使用hasattr检查确保向后兼容（新增字段不会导致旧存档加载失败）。

    Args:
        game_state: GameState对象，为None时返回空字典

    Returns:
        dict: 完整的存档数据字典，包含版本号、时间戳、元数据和游戏状态
    """
    if game_state is None:
        return {}

    save_data = {
        "version": SAVE_VERSION,
        "save_id": "",
        "timestamp": datetime.now().isoformat(),
        "round": game_state.round,
        "metadata": {
            "manual": True,
            "autosave": False,
            "player_country": None,
        },
        "game_state": {
            "round": game_state.round,
            "timeline": {
                "year": game_state.timeline.year,
                "month": game_state.timeline.month,
            },
            "countries": {},
            "blocks": {},
            "relations": {},
            "country_memories": {},
            "generals": [],
            "defeated_nations": {},
            "historical_events_triggered": {},
            "action_log": game_state.action_log if game_state.action_log else [],
            "history": game_state.history if game_state.history else [],
            "last_round_actions": {},
            "diplomatic_messages": [],
            "narratives": [],
            "battle_results_this_round": [],
        },
    }

    # 序列化国家数据
    for country_name, country in game_state.countries.items():
        save_data["game_state"]["countries"][country_name] = {
            "name": country.name,
            "gold": country.gold,
            "order": country.order,
            "morale": country.morale,
            "capital": country.capital,
            "goal": country.goal.value if hasattr(country, "goal") else None,
            "in_exile": country.in_exile if hasattr(country, "in_exile") else False,
            "is_defeated": country.is_defeated if hasattr(country, "is_defeated") else False,
            "has_declared_emperor": country.has_declared_emperor if hasattr(country, "has_declared_emperor") else False,
            "action_points": country.action_points if hasattr(country, "action_points") else 6.0,
            "aggression": country.aggression if hasattr(country, "aggression") else 0.5,
            "loyalty": country.loyalty if hasattr(country, "loyalty") else 0.5,
            "risk_preference": country.risk_preference if hasattr(country, "risk_preference") else 0.5,
            "last_betrayal_round": country.last_betrayal_round if hasattr(country, "last_betrayal_round") else -10,
            "last_move_capital_round": country.last_move_capital_round if hasattr(country, "last_move_capital_round") else -100,
            "former_capital": country.former_capital if hasattr(country, "former_capital") else None,
            "exile_rounds": country.exile_rounds if hasattr(country, "exile_rounds") else 0,
            "war_pressure": country.war_pressure if hasattr(country, "war_pressure") else 0,
        }

    # 序列化区块数据
    for block_name, block in game_state.blocks.items():
        save_data["game_state"]["blocks"][block_name] = {
            "name": block.name,
            "owner": block.owner,
            "garrison": block.garrison,
            "order": block.order,
            "morale": block.morale,
            "base_manpower": block.base_manpower,
            "manpower_pool": block.manpower_pool,
            "neighbors": block.neighbors,
            "region_type": block.region_type.value if hasattr(block, "region_type") else None,
            "geographic_trait": block.geographic_trait.value if hasattr(block, "geographic_trait") else None,
            "specialization": block.specialization.value if hasattr(block, "specialization") and block.specialization else None,
            "develop_count": block.develop_count if hasattr(block, "develop_count") else 0,
            "recently_conquered": block.recently_conquered if hasattr(block, "recently_conquered") else False,
            "supply_connected": block.supply_connected if hasattr(block, "supply_connected") else False,
            "last_recruit_round": block.last_recruit_round if hasattr(block, "last_recruit_round") else -10,
        }

    # 序列化外交关系
    for rel_key, relation in game_state.relations.items():
        save_data["game_state"]["relations"][rel_key] = {
            "country_a": relation.country_a,
            "country_b": relation.country_b,
            "trust": relation.trust,
            "grudge": relation.grudge,
            "is_allied": relation.is_allied,
            "at_war": relation.at_war,
            "alliance_round": relation.alliance_round if hasattr(relation, "alliance_round") else -1,
        }

    # 序列化国家记忆
    for mem_key, memory in game_state.country_memories.items():
        save_data["game_state"]["country_memories"][mem_key] = {
            "country_name": memory.country_name if hasattr(memory, "country_name") else None,
            "memories": [
                {
                    "round": mem.round,
                    "event": mem.event if hasattr(mem, "event") else "",
                    "target": mem.target if hasattr(mem, "target") else None,
                    "impact": mem.impact.value if hasattr(mem, "impact") else None,
                    "emotion": mem.emotion.value if hasattr(mem, "emotion") else None,
                    "decay": mem.decay if hasattr(mem, "decay") else 0.1,
                    "current_value": mem.current_value if hasattr(mem, "current_value") else 1.0,
                }
                for mem in memory.memories
            ],
        }

    # 序列化武将数据
    for general in game_state.generals:
        save_data["game_state"]["generals"].append({
            "name": general.name,
            "country": general.country,
            "block": general.block,
            "trait": general.trait.value if hasattr(general, "trait") else None,
            "alive": general.alive if hasattr(general, "alive") else True,
            "death_round": general.death_round if hasattr(general, "death_round") else None,
        })

    # 序列化其他数据
    for k, v in game_state.defeated_nations.items():
        save_data["game_state"]["defeated_nations"][k] = v

    for k, v in game_state.historical_events_triggered.items():
        save_data["game_state"]["historical_events_triggered"][k] = v

    for country_name, actions in game_state.last_round_actions.items():
        save_data["game_state"]["last_round_actions"][country_name] = actions

    # 序列化外交消息（仅保留最近50条）
    for msg in game_state.diplomatic_messages[-50:]:
        save_data["game_state"]["diplomatic_messages"].append({
            "id": msg.id,
            "from_country": msg.from_country,
            "to_country": msg.to_country,
            "content": msg.content,
            "visibility": msg.visibility,
            "round": msg.round,
            "timestamp": msg.timestamp.isoformat() if hasattr(msg.timestamp, "isoformat") else str(msg.timestamp),
        })

    # 序列化编年史叙事
    for narrative in game_state.narratives:
        save_data["game_state"]["narratives"].append(narrative)

    # 序列化战斗结果
    for battle_result in game_state.battle_results_this_round:
        save_data["game_state"]["battle_results_this_round"].append(battle_result.model_dump())

    return save_data


def _restore_game_state(save_data: dict) -> None:
    """
    从存档数据恢复游戏状态

    反序列化存档数据，重建所有游戏对象（国家、区块、关系、记忆、武将等），
    并替换当前引擎的游戏状态。包含版本兼容性检查和枚举值容错处理。

    Args:
        save_data: 存档数据字典

    Raises:
        HTTPException: 存档版本不兼容时返回400
    """
    from ..models import (
        Block, Country, Relation, Memory, MemoryImpact, MemoryEmotion,
        General, GeneralTrait, CountryMemory, DiplomaticMessage,
        RegionType, GeographicTrait, BlockSpecialization, StrategicGoal,
        Timeline, GameState, BattleResult,
    )

    engine = get_engine()

    # 版本兼容性检查
    if not _check_version_compatible(save_data.get("version", "")):
        raise HTTPException(
            status_code=400,
            detail=f"存档版本不兼容：期望 {SAVE_VERSION}，实际 {save_data.get('version')}"
        )

    gs = save_data.get("game_state", {})

    # 重建游戏状态对象
    new_state = GameState()
    new_state.round = gs.get("round", 1)

    # 恢复时间线
    timeline_data = gs.get("timeline", {"year": 200, "month": 1})
    new_state.timeline = Timeline(year=timeline_data["year"], month=timeline_data["month"])

    # 恢复国家数据（含枚举值容错）
    for country_name, cd in gs.get("countries", {}).items():
        goal_str = cd.get("goal", "expand")
        try:
            goal = StrategicGoal(goal_str)
        except ValueError:
            goal = StrategicGoal.EXPAND

        country = Country(
            name=cd.get("name", country_name),
            gold=cd.get("gold", 0),
            order=cd.get("order", 50),
            morale=cd.get("morale", 50),
            capital=cd.get("capital", ""),
            goal=goal,
            in_exile=cd.get("in_exile", False),
            former_capital=cd.get("former_capital"),
            exile_rounds=cd.get("exile_rounds", 0),
            has_declared_emperor=cd.get("has_declared_emperor", False),
            aggression=cd.get("aggression", 0.5),
            loyalty=cd.get("loyalty", 0.5),
            risk_preference=cd.get("risk_preference", 0.5),
            is_defeated=cd.get("is_defeated", False),
            last_betrayal_round=cd.get("last_betrayal_round", -10),
            last_move_capital_round=cd.get("last_move_capital_round", -100),
            action_points=cd.get("action_points", 6.0),
            war_pressure=cd.get("war_pressure", 0),
        )
        new_state.countries[country_name] = country

    # 恢复区块数据（含枚举值容错）
    for block_name, bd in gs.get("blocks", {}).items():
        region_type_str = bd.get("region_type", "core")
        try:
            region_type = RegionType(region_type_str)
        except ValueError:
            region_type = RegionType.CORE

        geo_trait_str = bd.get("geographic_trait", "none")
        try:
            geographic_trait = GeographicTrait(geo_trait_str)
        except ValueError:
            geographic_trait = GeographicTrait.NONE

        spec_str = bd.get("specialization")
        specialization = None
        if spec_str:
            try:
                specialization = BlockSpecialization(spec_str)
            except ValueError:
                specialization = None

        block = Block(
            name=bd.get("name", block_name),
            neighbors=bd.get("neighbors", []),
            base_manpower=bd.get("base_manpower", 0),
            manpower_pool=bd.get("manpower_pool", 0),
            owner=bd.get("owner", "neutral"),
            garrison=bd.get("garrison", 0),
            order=bd.get("order", 50),
            morale=bd.get("morale", 50),
            last_recruit_round=bd.get("last_recruit_round", -10),
            develop_count=bd.get("develop_count", 0),
            recently_conquered=bd.get("recently_conquered", False),
            region_type=region_type,
            supply_connected=bd.get("supply_connected", True),
            geographic_trait=geographic_trait,
            specialization=specialization,
        )
        new_state.blocks[block_name] = block

    # 恢复外交关系
    for rel_key, rd in gs.get("relations", {}).items():
        relation = Relation(
            country_a=rd.get("country_a", ""),
            country_b=rd.get("country_b", ""),
            trust=rd.get("trust", 0.5),
            grudge=rd.get("grudge", 0.0),
            is_allied=rd.get("is_allied", False),
            at_war=rd.get("at_war", False),
            alliance_round=rd.get("alliance_round", -1),
        )
        new_state.relations[rel_key] = relation

    # 恢复国家记忆（含枚举值容错）
    for mem_key, md in gs.get("country_memories", {}).items():
        memories = []
        for m in md.get("memories", []):
            try:
                impact = MemoryImpact(m.get("impact", "medium"))
            except ValueError:
                impact = MemoryImpact.MEDIUM
            try:
                emotion = MemoryEmotion(m.get("emotion", "anger"))
            except ValueError:
                emotion = MemoryEmotion.ANGER

            memories.append(Memory(
                round=m.get("round", 1),
                event=m.get("event", ""),
                impact=impact,
                emotion=emotion,
                target=m.get("target", ""),
                decay=m.get("decay", 0.1),
                current_value=m.get("current_value", 1.0),
            ))

        cm = CountryMemory(
            country_name=md.get("country_name", mem_key),
            memories=memories,
        )
        new_state.country_memories[mem_key] = cm

    # 恢复武将数据（含枚举值容错）
    for gd in gs.get("generals", []):
        trait_str = gd.get("trait")
        try:
            trait = GeneralTrait(trait_str) if trait_str else GeneralTrait.YI_SHEN_SHI_DAN
        except ValueError:
            trait = GeneralTrait.YI_SHEN_SHI_DAN

        general = General(
            name=gd.get("name", ""),
            country=gd.get("country", ""),
            block=gd.get("block", ""),
            trait=trait,
            alive=gd.get("alive", True),
            death_round=gd.get("death_round"),
        )
        new_state.generals.append(general)

    # 恢复其他数据
    new_state.defeated_nations = gs.get("defeated_nations", {})
    new_state.historical_events_triggered = gs.get("historical_events_triggered", {})
    new_state.action_log = gs.get("action_log", [])
    new_state.history = gs.get("history", [])
    new_state.last_round_actions = gs.get("last_round_actions", {})

    # 恢复外交消息（含时间戳反序列化）
    for msg_data in gs.get("diplomatic_messages", []):
        timestamp = msg_data.get("timestamp")
        if timestamp:
            try:
                from datetime import datetime as _dt
                timestamp = _dt.fromisoformat(timestamp)
            except (ValueError, TypeError):
                timestamp = None
        msg = DiplomaticMessage(
            id=msg_data.get("id", ""),
            from_country=msg_data.get("from_country", ""),
            to_country=msg_data.get("to_country", ""),
            content=msg_data.get("content", ""),
            visibility=msg_data.get("visibility", "private"),
            round=msg_data.get("round", 1),
            timestamp=timestamp,
        )
        new_state.diplomatic_messages.append(msg)

    new_state.narratives = gs.get("narratives", [])
    # 恢复战斗结果
    new_state.battle_results_this_round = [
        BattleResult(**br) if isinstance(br, dict) else br
        for br in gs.get("battle_results_this_round", [])
    ]

    # 替换引擎中的游戏状态
    engine.state = new_state


router = APIRouter(prefix="/save", tags=["save"])


def _validate_save_id(save_id: str) -> str:
    """
    验证存档ID的安全性

    防止路径遍历攻击，确保存档ID不包含路径分隔符或上级目录引用。

    Args:
        save_id: 存档ID字符串

    Returns:
        str: 验证通过的存档ID

    Raises:
        HTTPException: 存档ID包含非法字符时返回400
    """
    if "/" in save_id or "\\" in save_id or ".." in save_id:
        raise HTTPException(status_code=400, detail="Invalid save ID")
    return save_id


def create_autosave_sync() -> None:
    """
    同步创建自动存档

    由回合推进逻辑调用，创建自动存档并清理旧存档。
    不返回结果，失败时仅记录日志。

    Side Effects:
        - 在SAVE_DIR下创建新的自动存档JSON文件
        - 可能删除旧存档以保持总数不超限
    """
    engine = get_engine()
    if not engine.state:
        return

    save_data = _save_game_state(engine.state)
    save_id = _generate_save_id(is_autosave=True)
    save_data["save_id"] = save_id
    save_data["timestamp"] = datetime.now().isoformat()
    save_data["metadata"]["manual"] = False
    save_data["metadata"]["autosave"] = True

    save_path = SAVE_DIR / f"{save_id}.json"
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    _cleanup_old_saves()


@router.post("/manual", response_model=SaveInfo)
async def create_manual_save(req: SaveRequest):
    """
    创建手动存档

    支持自定义存档名称和描述。创建后自动清理旧存档。

    Args:
        req: 存档请求，包含可选的名称和描述

    Returns:
        SaveInfo: 存档信息

    Raises:
        HTTPException: 游戏未初始化(400)、创建失败(500)
    """
    try:
        engine = get_engine()

        if not engine.state:
            raise HTTPException(status_code=400, detail="游戏未初始化")

        save_data = _save_game_state(engine.state)

        save_id = _generate_save_id(is_autosave=False, custom_name=req.name)
        save_data["save_id"] = save_id
        save_data["metadata"]["manual"] = True
        save_data["metadata"]["autosave"] = False

        if req.description:
            save_data["metadata"]["description"] = req.description

        save_path = SAVE_DIR / f"{save_id}.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        _cleanup_old_saves()

        return {
            "save_id": save_id,
            "timestamp": save_data["timestamp"],
            "round": save_data["round"],
            "metadata": save_data["metadata"],
            "description": req.description,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建存档失败：{str(e)}")


@router.post("/autosave")
async def create_autosave():
    """
    创建自动存档

    通过API手动触发自动存档（区别于回合推进时的自动存档）。

    Returns:
        dict: 包含存档ID、成功标志和消息

    Raises:
        HTTPException: 游戏未初始化(400)、创建失败(500)
    """
    try:
        engine = get_engine()

        if not engine.state:
            raise HTTPException(status_code=400, detail="游戏未初始化")

        save_data = _save_game_state(engine.state)

        current_round = engine.state.round
        save_id = _generate_save_id(is_autosave=True)
        save_data["save_id"] = save_id
        save_data["timestamp"] = datetime.now().isoformat()
        save_data["metadata"]["manual"] = False
        save_data["metadata"]["autosave"] = True

        save_path = SAVE_DIR / f"{save_id}.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        _cleanup_old_saves()

        return {
            "save_id": save_id,
            "success": True,
            "message": f"自动存档已创建：第{current_round}回"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建自动存档失败：{str(e)}")


@router.get("/list", response_model=List[SaveInfo])
async def list_saves():
    """
    获取存档列表

    按时间倒序返回所有存档的信息。

    Returns:
        List[SaveInfo]: 存档信息列表

    Raises:
        HTTPException: 获取失败(500)
    """
    try:
        saves = []

        for save_file in sorted(SAVE_DIR.glob("*.json"), reverse=True):
            try:
                with open(save_file, "r", encoding="utf-8") as f:
                    save_data = json.load(f)

                    save_info = {
                        "save_id": save_data["save_id"],
                        "timestamp": save_data["timestamp"],
                        "round": save_data["round"],
                        "metadata": save_data["metadata"],
                        "description": save_data["metadata"].get("description"),
                    }

                    saves.append(save_info)
            except Exception as e:
                logger.error(f"Error reading save file {save_file}: {e}")
                continue

        # 按时间倒序排列
        saves.sort(key=lambda x: x["timestamp"], reverse=True)

        return saves
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取存档列表失败：{str(e)}")


@router.post("/load/{save_id}")
async def load_save(save_id: str):
    """
    加载存档

    从指定存档文件恢复游戏状态，包含版本兼容性检查。

    Args:
        save_id: 存档ID

    Returns:
        dict: 包含存档ID、回合数、成功标志和消息

    Raises:
        HTTPException: 存档不存在(404)、版本不兼容(400)、加载失败(500)
    """
    save_id = _validate_save_id(save_id)
    try:
        save_path = SAVE_DIR / f"{save_id}.json"

        if not save_path.exists():
            raise HTTPException(status_code=404, detail="存档文件不存在")

        with open(save_path, "r", encoding="utf-8") as f:
            save_data = json.load(f)

        if not _check_version_compatible(save_data.get("version", "")):
            raise HTTPException(
                status_code=400,
                detail=f"存档版本不兼容：期望 {SAVE_VERSION}，实际 {save_data.get('version')}"
            )

        # 恢复游戏状态（替换当前引擎状态）
        _restore_game_state(save_data)

        loaded_round = save_data.get("game_state", {}).get("round", 1)

        return {
            "save_id": save_id,
            "round": loaded_round,
            "success": True,
            "message": f"存档已加载：第{loaded_round}回"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载存档失败：{str(e)}")


@router.delete("/{save_id}")
async def delete_save(save_id: str):
    """
    删除存档

    Args:
        save_id: 存档ID

    Returns:
        dict: 包含存档ID、删除标志和消息

    Raises:
        HTTPException: 存档不存在(404)、删除失败(500)
    """
    save_id = _validate_save_id(save_id)
    try:
        save_path = SAVE_DIR / f"{save_id}.json"

        if not save_path.exists():
            raise HTTPException(status_code=404, detail="存档文件不存在")

        save_path.unlink()

        return {
            "save_id": save_id,
            "deleted": True,
            "message": f"存档已删除：{save_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除存档失败：{str(e)}")


@router.get("/count")
async def get_save_count():
    """
    获取存档统计

    分别统计手动存档和自动存档的数量。

    Returns:
        dict: 包含手动存档数、自动存档数和总数

    Raises:
        HTTPException: 获取失败(500)
    """
    try:
        manual_count = 0
        autosave_count = 0

        for save_file in SAVE_DIR.glob("*.json"):
            try:
                with open(save_file, "r", encoding="utf-8") as f:
                    save_data = json.load(f)
                    metadata = save_data.get("metadata", {})

                    if metadata.get("manual", False):
                        manual_count += 1
                    elif metadata.get("autosave", False):
                        autosave_count += 1
            except Exception:
                continue

        return {
            "manual_count": manual_count,
            "autosave_count": autosave_count,
            "total_count": manual_count + autosave_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取存档统计失败：{str(e)}")
