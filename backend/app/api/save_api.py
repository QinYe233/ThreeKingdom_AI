"""
游戏存档API模块
处理手动存档、自动存档、加载、删除等功能
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import shutil

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


# ===========================
# 存档系统配置
# ===========================
SAVE_DIR = Path(__file__).parent.parent.parent / "data" / "saves"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

SAVE_VERSION = "1.0.0"  # 存档版本号
KEEP_MANUAL_SAVES = 10  # 保留的手动存档数量
KEEP_AUTO_SAVES = 3  # 保留的自动存档数量


# ===========================
# 数据模型
# ===========================
class SaveRequest(BaseModel):
    """手动存档请求"""
    name: Optional[str] = None
    description: Optional[str] = None


class SaveInfo(BaseModel):
    """存档信息"""
    save_id: str
    timestamp: str
    round: int
    metadata: dict
    description: Optional[str] = None


class LoadSaveRequest(BaseModel):
    """加载存档请求"""
    save_id: str


# ===========================
# 辅助函数
# ===========================
def _cleanup_old_saves(keep_manual: int = KEEP_MANUAL_SAVES, keep_autosave: int = KEEP_AUTO_SAVES) -> None:
    """清理旧存档文件"""
    all_saves = []

    # 获取所有存档文件
    for save_file in SAVE_DIR.glob("*.json"):
        try:
            with open(save_file, "r", encoding="utf-8") as f:
                save_data = json.load(f)
                metadata = save_data.get("metadata", {})

                if metadata.get("autosave", False):
                    all_saves.append((save_file, save_data["timestamp"]))
                elif keep_manual > 0:
                    all_saves.append((save_file, save_data["timestamp"]))
        except Exception as e:
            print(f"Error reading save file {save_file}: {e}")
            continue

    # 按时间戳排序（新的在前）
    all_saves.sort(key=lambda x: x[1], reverse=True)

    # 分离自动存档和手动存档
    autosaves = []
    manualsaves = []

    for save_file, timestamp in all_saves:
        try:
            with open(save_file, "r", encoding="utf-8") as f:
                save_data = json.load(f)
                metadata = save_data.get("metadata", {})

                if metadata.get("autosave", False):
                    autosaves.append((save_file, timestamp))
                else:
                    manualsaves.append((save_file, timestamp))
        except Exception:
            continue

    # 删除多余的自动存档
    while len(autosaves) > keep_autosave:
        save_file, _ = autosaves.pop()
        try:
            save_file.unlink()
            print(f"Deleted old autosave: {save_file.name}")
        except Exception:
            print(f"Error deleting autosave {save_file.name}: {e}")

    # 删除过多的手动存档
    while len(manualsaves) > keep_manual:
        save_file, _ = manualsaves.pop()
        try:
            save_file.unlink()
            print(f"Deleted old manual save: {save_file.name}")
        except Exception:
            print(f"Error deleting manual save {save_file.name}: {e}")


def _generate_save_id(is_autosave: bool = False, custom_name: Optional[str] = None) -> str:
    """生成存档ID"""
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

    if is_autosave:
        # 自动存档使用特殊格式
        save_id = f"auto_{timestamp}"
    elif custom_name:
        # 手动存档使用自定义名称
        safe_name = "".join(c for c in custom_name if c.isalnum() or c in ('-', '_', ' '))
        save_id = f"manual_{safe_name}_{timestamp}"
    else:
        save_id = f"manual_{timestamp}"

    return save_id


def _save_game_state(game_state) -> dict:
    """保存游戏状态到字典"""
    if game_state is None:
        return {}

    # 序列化游戏状态（简化版）
    save_data = {
        "version": SAVE_VERSION,
        "save_id": "",
        "timestamp": datetime.now().isoformat(),
        "round": game_state.round,
        "metadata": {
            "manual": True,
            "autosave": False,
            "player_country": None,  # 未来可扩展玩家模式
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
            "battle_results_this_round": [],
            "action_log": [],
            "history": [],
        },
        "ai_states": {}  # 存储AI偏好（未来扩展）
    }

    # 序列化国家
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
        }

    # 序列化区块
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
            "specialization": block.specialization.value if hasattr(block, "specialization") else None,
            "develop_count": block.develop_count if hasattr(block, "develop_count") else 0,
            "recently_conquered": block.recently_conquered if hasattr(block, "recently_conquered") else False,
            "supply_connected": block.supply_connected if hasattr(block, "supply_connected") else False,
        }

    # 序列化关系
    for rel_key, relation in game_state.relations.items():
        save_data["game_state"]["relations"][rel_key] = {
            "country_a": relation.country_a,
            "country_b": relation.country_b,
            "trust": relation.trust,
            "grudge": relation.grudge,
            "is_allied": relation.is_allied,
            "at_war": relation.at_war,
        }

    # 序列化国家记忆
    for mem_key, memory in game_state.country_memories.items():
        save_data["game_state"]["country_memories"][mem_key] = {
            "country": memory.country if hasattr(memory, "country") else None,
            "memories": [
                {
                    "round": mem.round,
                    "target": mem.target if hasattr(mem, "target") else None,
                    "event_type": mem.event_type.value if hasattr(mem, "event_type") else None,
                    "impact": mem.impact.value if hasattr(mem, "impact") else None,
                    "emotion": mem.emotion.value if hasattr(mem, "emotion") else None,
                    "details": mem.details if hasattr(mem, "details") else None,
                }
                for mem in memory.memories
            ],
        }

    return save_data


def _load_game_state(save_data: dict) -> dict:
    """从字典恢复游戏状态"""
    if save_data.get("version") != SAVE_VERSION:
        raise HTTPException(
            status_code=400,
            detail=f"存档版本不兼容：期望 {SAVE_VERSION}，实际 {save_data.get('version')}"
        )

    game_state_data = save_data.get("game_state", {})

    # 反序列化游戏状态（这里简化处理，实际应该使用游戏引擎的完整逻辑）
    # 返回包含关键字段但不包含完整对象的字典
    return {
        "round": game_state_data.get("round", 1),
        "timeline": game_state_data.get("timeline", {"year": 200, "month": 1}),
        "countries": game_state_data.get("countries", {}),
        "blocks": game_state_data.get("blocks", {}),
        "relations": game_state_data.get("relations", {}),
        "country_memories": game_state_data.get("country_memories", {}),
        "battle_results_this_round": game_state_data.get("battle_results_this_round", []),
        "action_log": game_state_data.get("action_log", []),
        "history": game_state_data.get("history", []),
    }


router = APIRouter(prefix="/save", tags=["save"])


# ===========================
# API端点
# ===========================

@router.post("/manual", response_model=SaveInfo)
async def create_manual_save(req: SaveRequest):
    """创建手动存档"""
    try:
        # 导入游戏引擎（需要在函数外部导入）
        from ..main import engine

        if not engine.state:
            raise HTTPException(status_code=400, detail="游戏未初始化")

        # 准备存档数据
        save_data = _save_game_state(engine.state)

        # 设置存档ID
        save_id = _generate_save_id(is_autosave=False, custom_name=req.name)
        save_data["save_id"] = save_id
        save_data["metadata"]["manual"] = True
        save_data["metadata"]["autosave"] = False

        # 如果有描述，添加到metadata
        if req.description:
            save_data["metadata"]["description"] = req.description

        # 保存到文件
        save_path = SAVE_DIR / f"{save_id}.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        # 清理旧存档
        _cleanup_old_saves()

        return {
            "save_id": save_id,
            "success": True,
            "message": f"存档已创建：{req.name or '未命名'}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建存档失败：{str(e)}")


@router.post("/autosave")
async def create_autosave():
    """创建自动存档"""
    try:
        # 导入游戏引擎
        from ..main import engine

        if not engine.state:
            raise HTTPException(status_code=400, detail="游戏未初始化")

        # 准备存档数据
        save_data = _save_game_state(engine.state)

        # 设置存档ID
        round = engine.state.round
        save_id = _generate_save_id(is_autosave=True)
        save_data["save_id"] = save_id
        save_data["timestamp"] = datetime.now().isoformat()
        save_data["metadata"]["manual"] = False
        save_data["metadata"]["autosave"] = True

        # 保存到文件
        save_path = SAVE_DIR / f"{save_id}.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        # 清理旧自动存档
        _cleanup_old_saves()

        return {
            "save_id": save_id,
            "success": True,
            "message": f"自动存档已创建：第{round}回"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建自动存档失败：{str(e)}")


@router.get("/list", response_model=List[SaveInfo])
async def list_saves():
    """列出所有可用存档"""
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
                print(f"Error reading save file {save_file}: {e}")
                continue

        # 按时间戳排序
        saves.sort(key=lambda x: x["timestamp"], reverse=True)

        return saves
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取存档列表失败：{str(e)}")


@router.post("/load/{save_id}")
async def load_save(save_id: str):
    """加载指定存档"""
    try:
        save_path = SAVE_DIR / f"{save_id}.json"

        if not save_path.exists():
            raise HTTPException(status_code=404, detail="存档文件不存在")

        with open(save_path, "r", encoding="utf-8") as f:
            save_data = json.load(f)

        # 验证版本
        if save_data.get("version") != SAVE_VERSION:
            raise HTTPException(
                status_code=400,
                detail=f"存档版本不兼容：期望 {SAVE_VERSION}，实际 {save_data.get('version')}"
            )

        # 恢复游戏状态（这里需要游戏引擎的完整恢复逻辑）
        # 返回游戏状态数据，前端将重新加载游戏
        game_state_data = _load_game_state(save_data)

        return {
            "save_id": save_id,
            "round": game_state_data["round"],
            "success": True,
            "message": f"存档已加载：第{game_state_data['round']}回"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载存档失败：{str(e)}")


@router.delete("/{save_id}")
async def delete_save(save_id: str):
    """删除指定存档"""
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除存档失败：{str(e)}")


@router.get("/count")
async def get_save_count():
    """获取存档数量统计"""
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
