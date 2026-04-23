"""
AI API模块
处理AI配置、连接测试、AI决策流式输出等
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict
import json
import httpx

from ..ai import (
    AIModelConfig, AI_ROLES, ROLE_NAMES, ROLE_DESCRIPTIONS, SYSTEM_PROMPTS,
    get_ai_client, set_ai_config, is_all_configured, get_config_status
)

router = APIRouter(prefix="/ai", tags=["ai"])


class AIConfigRequest(BaseModel):
    """AI配置请求"""
    role: str
    model: str
    api_key: str
    base_url: str
    temperature: float = 0.7
    max_tokens: int = 2000


class TestConnectionRequest(BaseModel):
    """测试连接请求"""
    model: str
    api_key: str
    base_url: str


@router.get("/status")
def get_status():
    """
    获取AI配置状态
    返回所有角色的配置情况和是否全部配置完成
    """
    status = get_config_status()
    return {
        "roles": {role: {"name": ROLE_NAMES.get(role, role), "description": ROLE_DESCRIPTIONS.get(role, "")} for role in AI_ROLES},
        "configs": status,
        "all_configured": is_all_configured(),
    }


@router.get("/config/{role}")
def get_config(role: str):
    """获取指定角色的AI配置"""
    role = role.lower()
    if role not in AI_ROLES:
        raise HTTPException(status_code=400, detail=f"无效的角色: {role}")
    
    status = get_config_status()
    return status.get(role, {"model": "", "base_url": "", "has_api_key": False, "is_valid": False})


@router.post("/config")
def save_config(req: AIConfigRequest):
    """
    保存AI配置
    支持保留已有API Key（传入 __keep_existing__）
    """
    role = req.role.lower()
    if role not in AI_ROLES:
        raise HTTPException(status_code=400, detail=f"无效的角色: {role}")
    
    if not req.model:
        raise HTTPException(status_code=400, detail="请输入模型名称")
    if not req.base_url:
        raise HTTPException(status_code=400, detail="请输入Base URL")
    
    from ..ai import get_ai_config
    
    existing_config = get_ai_config(role)
    
    # 处理API Key保留逻辑
    if req.api_key == "__keep_existing__":
        api_key = existing_config.api_key
    elif req.api_key:
        api_key = req.api_key
    else:
        raise HTTPException(status_code=400, detail="请输入API Key")
    
    config = AIModelConfig(
        model=req.model,
        api_key=api_key,
        base_url=req.base_url,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
    )
    set_ai_config(role, config)
    return {"status": "ok", "message": f"{ROLE_NAMES.get(role, role)}配置已保存"}


@router.post("/test-connection")
async def test_connection(req: TestConnectionRequest):
    """
    测试AI连接
    发送简单请求验证API Key和Base URL是否有效
    """
    if not req.model:
        raise HTTPException(status_code=400, detail="请输入模型名称")
    if not req.api_key:
        raise HTTPException(status_code=400, detail="请输入API Key")
    if not req.base_url:
        raise HTTPException(status_code=400, detail="请输入Base URL")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{req.base_url.rstrip('/')}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {req.api_key}",
                },
                json={
                    "model": req.model,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                }
            )
            
            if response.status_code == 200:
                return {"status": "ok", "message": "连接成功"}
            elif response.status_code == 401:
                raise HTTPException(status_code=401, detail="API Key无效")
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail="模型不存在或API地址错误")
            else:
                error_detail = f"HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_detail = error_data["error"].get("message", str(error_data["error"]))
                except:
                    pass
                raise HTTPException(status_code=response.status_code, detail=error_detail)
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="连接超时，请检查网络或API地址")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="无法连接到API服务器，请检查API地址")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"连接测试失败: {str(e)}")


@router.get("/check")
def check_all_configured():
    """检查所有AI角色是否都已配置"""
    return {"all_configured": is_all_configured()}


def _build_context(state, country_name: str) -> str:
    """
    构建AI决策上下文
    整合国家状态、边境情况、外交关系等信息
    """
    from ..core.constants import ACTION_COSTS, get_config
    
    country = state.countries.get(country_name)
    if not country:
        return ""
    
    # 统计国家基础数据
    blocks = [b for b in state.blocks.values() if b.owner == country_name]
    total_garrison = sum(b.garrison for b in blocks)

    # 收集边境区块信息
    border_blocks = []
    for block in blocks:
        for neighbor_name in block.neighbors:
            neighbor = state.blocks.get(neighbor_name)
            if neighbor and neighbor.owner != country_name:
                border_blocks.append({
                    "from": block.name,
                    "to": neighbor_name,
                    "to_owner": neighbor.owner,
                    "from_garrison": block.garrison,
                    "to_garrison": neighbor.garrison,
                })

    # 收集外交关系信息
    relations_info = []
    for key, rel in state.relations.items():
        if country_name in (rel.country_a, rel.country_b):
            other = rel.country_b if rel.country_a == country_name else rel.country_a
            relations_info.append({
                "target": other,
                "trust": rel.trust,
                "grudge": rel.grudge,
                "is_allied": rel.is_allied,
                "at_war": rel.at_war,
            })

    # 行动规则说明
    action_rules = f"""
【行动规则】
每回合你有 {country.action_points:.1f} 行动点数(AP)，可执行多个行动直到AP耗尽：

行动类型及消耗：
- 进攻(attack): 消耗 1.0 AP，从己方区块出兵攻击相邻敌方或中立区块
  * 出兵数量建议：至少100兵，推荐出兵30%-50%的守军
  * 成功条件：攻击方兵力需明显多于防守方
  * 注意：可以多次进攻，每次消耗1AP
  
- 征兵(recruit): 消耗 0.5 AP，在己方区块征召士兵
  * 需要：区块有人力池(manpower_pool)，每点人力可征1兵
  * 花费：每征100兵消耗约50金
  
- 发展(develop): 消耗 0.8 AP，提升区块人力池上限
  * 花费：约300金
  * 效果：永久增加区块人力产出
  
- 征税(tax): 消耗 0 AP，立即获得黄金
  * 收入：根据控制的区块数量计算
  
- 调兵(move): 消耗 0.5 AP，在己方相邻区块间调动兵力
  * 用途：集中兵力准备进攻或防守
  
- 骚扰(harass): 消耗 0.5 AP，削弱敌方区块
  * 效果：降低敌方士气和秩序
  
- 外交(send_message): 消耗 0.5 AP，向其他国家发送外交信函
  * 每回合仅限一次外交行动
  
- 迁都(move_capital): 消耗 2.0 AP，将首都迁至其他己方区块
  
- 称帝(declare_emperor): 消耗 3.0 AP，宣布称帝（需满足条件）

重要提示：
1. 你可以执行多个相同类型的行动（如连续进攻多个区块）
2. 行动点数每回合重置为6.0
3. 合理规划行动顺序，优先执行最重要的行动
"""

    # 上一回合行动结果回顾
    last_actions_text = ""
    last_actions = state.last_round_actions.get(country_name, [])
    if last_actions:
        last_actions_text = "\n【上一回合你的行动结果】\n"
        for i, action in enumerate(last_actions, 1):
            action_type = action.get("action", "未知")
            params = action.get("parameters", {})
            result = action.get("result", {})
            
            if action_type == "attack":
                from_block = params.get("from", "?")
                to_block = params.get("to", "?")
                troops = params.get("troops", 0)
                success = result.get("battle_result", {}).get("block_captured", False)
                attacker_loss = result.get("battle_result", {}).get("attacker_loss", 0)
                defender_loss = result.get("battle_result", {}).get("defender_loss", 0)
                if success:
                    last_actions_text += f"{i}. 进攻成功！从{from_block}出兵{troops}攻占{to_block}，敌军损失{defender_loss}，我军损失{attacker_loss}\n"
                else:
                    last_actions_text += f"{i}. 进攻受挫：从{from_block}出兵{troops}进攻{to_block}失败，我军损失{attacker_loss}，敌军损失{defender_loss}\n"
            elif action_type == "recruit":
                block = params.get("block", "?")
                recruited = result.get("troops_recruited", 0)
                last_actions_text += f"{i}. 在{block}征兵{recruited}人\n"
            elif action_type == "develop":
                block = params.get("block", "?")
                inc = result.get("manpower_increase", 0)
                last_actions_text += f"{i}. 发展{block}，人力池+{inc}\n"
            elif action_type == "tax":
                gold = result.get("gold_earned", 0)
                last_actions_text += f"{i}. 征税获得{gold}金\n"
            elif action_type == "move":
                from_b = params.get("from", "?")
                to_b = params.get("to", "?")
                troops = params.get("troops", 0)
                last_actions_text += f"{i}. 从{from_b}调兵{troops}至{to_b}\n"
            elif action_type == "harass":
                to_block = params.get("to", "?")
                last_actions_text += f"{i}. 骚扰{to_block}\n"
            elif action_type == "send_message":
                to_country = params.get("to_country", "?")
                last_actions_text += f"{i}. 向{to_country}发送外交信函\n"
            else:
                last_actions_text += f"{i}. 执行了{action_type}\n"

    # 组装完整上下文
    context = f"""
国家: {country_name}
黄金: {country.gold}
秩序: {country.order}
士气: {country.morale}
首都: {country.capital}
战略目标: {country.goal.value}
控制区块数: {len(blocks)}
总兵力: {total_garrison}
行动点: {country.action_points}

{action_rules}

{last_actions_text}

边境情况:
{chr(10).join(f"  {b['from']}({b['from_garrison']}兵) → {b['to']}({b['to_owner']},{b['to_garrison']}兵)" for b in border_blocks[:15])}

外交关系:
{chr(10).join(f"  {r['target']}: 信任{r['trust']:.1f} 仇怨{r['grudge']:.1f} {'同盟' if r['is_allied'] else '交战' if r['at_war'] else '中立'}" for r in relations_info)}
"""
    return context


@router.post("/think/{country_name}")
async def ai_think(country_name: str):
    """
    AI思考接口（仅思考不执行）
    流式返回AI的思考过程
    """
    from ..api.game import engine
    if not engine.state:
        raise HTTPException(status_code=400, detail="游戏未初始化")

    state = engine.state
    context = _build_context(state, country_name)
    
    if not context:
        raise HTTPException(status_code=404, detail="国家不存在")

    # 国家到AI角色的映射
    country_to_role = {"魏": "wei", "蜀": "shu", "吴": "wu"}
    role = country_to_role.get(country_name, "wei")
    
    prompt_type = f"country_{role}"
    if prompt_type not in SYSTEM_PROMPTS:
        prompt_type = "country_wei"

    ai_client = get_ai_client(role)

    async def stream_generator():
        yield f"data: {json.dumps({'type': 'start', 'country': country_name})}\n\n"
        async for chunk in ai_client.generate_stream(prompt_type, context):
            yield f"data: {json.dumps(chunk)}\n\n"
        yield f"data: {json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
    )


@router.post("/think-and-act/{country_name}")
async def ai_think_and_act(country_name: str):
    """
    AI思考并执行行动
    流式返回思考过程、决策内容、执行结果
    """
    from ..api.game import engine
    from ..core.constants import ACTION_COSTS
    
    if not engine.state:
        raise HTTPException(status_code=400, detail="游戏未初始化")

    state = engine.state
    country = state.countries.get(country_name)
    if not country:
        raise HTTPException(status_code=404, detail="国家不存在")
    
    if country.is_defeated:
        return {"actions": [], "message": "Country is defeated"}

    context = _build_context(state, country_name)
    
    # 国家到AI角色的映射
    country_to_role = {"魏": "wei", "蜀": "shu", "吴": "wu"}
    role = country_to_role.get(country_name, "wei")
    
    prompt_type = f"country_{role}"
    if prompt_type not in SYSTEM_PROMPTS:
        prompt_type = "country_wei"

    ai_client = get_ai_client(role)

    async def stream_generator():
        yield f"data: {json.dumps({'type': 'start', 'country': country_name})}\n\n"
        
        # 收集思考和内容
        thinking = ""
        content = ""
        async for chunk in ai_client.generate_stream(prompt_type, context):
            yield f"data: {json.dumps(chunk)}\n\n"
            if chunk.get("type") == "thinking":
                thinking += chunk.get("content", "")
            elif chunk.get("type") == "content":
                content += chunk.get("content", "")
        
        yield f"data: {json.dumps({'type': 'thinking_end', 'thinking': thinking, 'content': content})}\n\n"
        
        # AI决策引擎生成行动
        from ..ai import AIDecisionEngine
        ai = AIDecisionEngine(state)
        actions = ai.decide_actions(country_name, country.action_points)
        
        yield f"data: {json.dumps({'type': 'actions_start', 'count': len(actions)})}\n\n"
        
        # 逐个执行行动
        results = []
        for i, action in enumerate(actions):
            cost = ACTION_COSTS.get(action["action_type"], 0)
            if cost > 0 and country.action_points * 1000 < cost:
                continue
            
            from ..api.game import ActionRequest, execute_action
            req = ActionRequest(
                country=country_name,
                action_type=action["action_type"],
                parameters=action["parameters"],
            )
            result = execute_action(req)
            
            # 扣除行动点数
            if "error" not in result:
                country.action_points = max(0, country.action_points - cost / 1000)
            
            results.append({
                "action": action["action_type"],
                "parameters": action["parameters"],
                "result": result,
            })
            
            yield f"data: {json.dumps({'type': 'action', 'index': i, 'action': action['action_type'], 'parameters': action['parameters'], 'result': result})}\n\n"
        
        # 保存本回合行动结果
        state.last_round_actions[country_name] = results
        
        yield f"data: {json.dumps({'type': 'end', 'country': country_name, 'actions_executed': len(results), 'results': results})}\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
    )
