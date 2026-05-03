"""
AI API模块
处理AI配置、连接测试、AI决策流式输出等
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from ..ai import (
    AIModelConfig, AI_ROLES, ROLE_NAMES, ROLE_DESCRIPTIONS, SYSTEM_PROMPTS,
    get_ai_client, set_ai_config, is_all_configured, get_config_status,
    get_ai_config, AIDecisionEngine,
)
from ..core.constants import ACTION_COSTS, COUNTRY_TO_ROLE
from .game_state_holder import get_engine
from .game import execute_action, ActionRequest

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
    测试AI连接（使用表单中的配置）
    使用 OpenAI 库发送请求，与实际 AI 调用路径一致
    """
    if not req.model:
        raise HTTPException(status_code=400, detail="请输入模型名称")
    if not req.api_key:
        raise HTTPException(status_code=400, detail="请输入API Key")
    if not req.base_url:
        raise HTTPException(status_code=400, detail="请输入Base URL")
    
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=req.api_key,
            base_url=req.base_url,
            timeout=30.0,
        )
        response = await client.chat.completions.create(
            model=req.model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
        )
        return {
            "status": "ok",
            "message": "连接成功",
            "model": response.model,
        }
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "auth" in error_msg.lower() or "api key" in error_msg.lower():
            raise HTTPException(status_code=401, detail=f"API Key无效: {error_msg}")
        elif "404" in error_msg or "model_not_found" in error_msg.lower() or "does not exist" in error_msg.lower():
            raise HTTPException(status_code=404, detail=f"模型不存在或API地址错误: {error_msg}")
        elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            raise HTTPException(status_code=504, detail=f"连接超时，请检查网络或API地址: {error_msg}")
        elif "connect" in error_msg.lower() or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail=f"无法连接到API服务器，请检查Base URL: {error_msg}")
        else:
            raise HTTPException(status_code=500, detail=f"连接测试失败: {error_msg}")


@router.post("/test-connection/{role}")
async def test_connection_by_role(role: str):
    """
    测试已保存的AI配置连接
    使用后端已保存的 API Key 进行测试，无需前端重新输入
    """
    role = role.lower()
    if role not in AI_ROLES:
        raise HTTPException(status_code=400, detail=f"无效的角色: {role}")

    config = get_ai_config(role)

    if not config.is_valid():
        raise HTTPException(status_code=400, detail=f"{ROLE_NAMES.get(role, role)}未完成配置，请先填写模型、API Key和Base URL")

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=30.0,
        )
        response = await client.chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
        )
        return {
            "status": "ok",
            "message": f"{ROLE_NAMES.get(role, role)}连接成功",
            "model": response.model,
        }
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "auth" in error_msg.lower() or "api key" in error_msg.lower():
            raise HTTPException(status_code=401, detail=f"API Key无效: {error_msg}")
        elif "404" in error_msg or "model_not_found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=f"模型不存在: {error_msg}")
        elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            raise HTTPException(status_code=504, detail=f"连接超时: {error_msg}")
        elif "connect" in error_msg.lower() or "connection" in error_msg.lower():
            raise HTTPException(status_code=503, detail=f"无法连接到API服务器: {error_msg}")
        else:
            raise HTTPException(status_code=500, detail=f"连接测试失败: {error_msg}")


@router.get("/check")
def check_all_configured():
    """检查所有AI角色是否都已配置"""
    return {"all_configured": is_all_configured()}


def _build_context(state, country_name: str) -> str:
    country = state.countries.get(country_name)
    if not country:
        return ""

    blocks = [b for b in state.blocks.values() if b.owner == country_name]
    total_garrison = sum(b.garrison for b in blocks)
    total_manpower = sum(b.manpower_pool for b in blocks)

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

    developable = []
    for b in blocks:
        if b.develop_count < 3 and b.supply_connected and not b.recently_conquered:
            developable.append(f"  {b.name}(人力池{b.manpower_pool}, 已发展{b.develop_count}次)")

    recruitable = []
    for b in blocks:
        if b.manpower_pool >= 10 and not b.recently_conquered:
            recruitable.append(f"  {b.name}(人力池{b.manpower_pool}, 守军{b.garrison})")

    low_order_blocks = []
    for b in blocks:
        if b.order < 50:
            low_order_blocks.append(f"  {b.name}(秩序{b.order})")

    last_actions_text = ""
    last_actions = state.last_round_actions.get(country_name, [])
    if last_actions:
        last_actions_text = "【上回战报】\n"
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
                    last_actions_text += f"  {i}. 攻占{to_block}！从{from_block}出兵{troops}，歼敌{defender_loss}，损兵{attacker_loss}\n"
                else:
                    last_actions_text += f"  {i}. 进攻{to_block}受挫，损兵{attacker_loss}，歼敌{defender_loss}\n"
            elif action_type == "recruit":
                block = params.get("block", "?")
                recruited = result.get("troops_recruited", 0)
                last_actions_text += f"  {i}. {block}征兵{recruited}人\n"
            elif action_type == "develop":
                block = params.get("block", "?")
                inc = result.get("manpower_increase", 0)
                last_actions_text += f"  {i}. 发展{block}，人力+{inc}\n"
            elif action_type == "tax":
                gold = result.get("gold_earned", 0)
                last_actions_text += f"  {i}. 征税得{gold}金\n"
            elif action_type == "move":
                from_b = params.get("from", "?")
                to_b = params.get("to", "?")
                troops = params.get("troops", 0)
                last_actions_text += f"  {i}. 调兵{troops}自{from_b}至{to_b}\n"
            elif action_type == "harass":
                to_block = params.get("to", "?")
                last_actions_text += f"  {i}. 骚扰{to_block}\n"
            elif action_type == "send_message":
                to_country = params.get("to_country", "?")
                last_actions_text += f"  {i}. 致书{to_country}\n"
            else:
                last_actions_text += f"  {i}. {action_type}\n"

    context = f"""【国力概况】
  国库：{country.gold}金 | 兵力：{total_garrison} | 人力储备：{total_manpower}
  秩序：{country.order} | 士气：{country.morale} | 领地：{len(blocks)}处
  首都：{country.capital} | 行动点：{country.action_points}

{last_actions_text}

【可发展领地】（花费400金，增加人力产出，最多3次）
{chr(10).join(developable[:8]) if developable else "  无"}

【可征兵之地】（花费200金，征召士兵）
{chr(10).join(recruitable[:8]) if recruitable else "  无"}

{"【秩序不稳之地】" + chr(10) + chr(10).join(low_order_blocks[:5]) if low_order_blocks else ""}

【边境军情】
{chr(10).join(f"  {b['from']}({b['from_garrison']}兵) → {b['to']}({b['to_owner']},{b['to_garrison']}兵)" for b in border_blocks[:12])}

【邦交】
{chr(10).join(f"  {r['target']}：{'同盟' if r['is_allied'] else '交战' if r['at_war'] else '中立'}（信任{r['trust']:.0f} 仇怨{r['grudge']:.0f}）" for r in relations_info)}

【可行之事】（你有{country.action_points:.1f}行动点）
  进攻(1点)：从己方出兵攻邻地 | 征兵(1点)：在己地征兵(200金)
  发展(1点)：提升人力产出(400金) | 征税(0.5点)：收取税金
  调兵(0.5点)：己方领地间调兵 | 骚扰(0.5点)：扰敌士气秩序"""

    return context


@router.post("/think/{country_name}")
async def ai_think(country_name: str):
    """
    AI思考接口（仅思考不执行）
    流式返回AI的思考过程
    """
    engine = get_engine()
    if not engine.state:
        raise HTTPException(status_code=400, detail="游戏未初始化")

    state = engine.state
    context = _build_context(state, country_name)
    
    if not context:
        raise HTTPException(status_code=404, detail="国家不存在")

    role = COUNTRY_TO_ROLE.get(country_name, "wei")
    
    prompt_type = f"country_{role}"
    if prompt_type not in SYSTEM_PROMPTS:
        prompt_type = "country_wei"

    ai_client = get_ai_client(role)
    ai_configured = ai_client.config.is_valid()

    async def stream_generator():
        yield f"data: {json.dumps({'type': 'start', 'country': country_name})}\n\n"
        if ai_configured:
            async for chunk in ai_client.generate_stream(prompt_type, context):
                yield f"data: {json.dumps(chunk)}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'content', 'content': f'[{country_name}AI未配置]'})}\n\n"
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
    engine = get_engine()
    
    if not engine.state:
        raise HTTPException(status_code=400, detail="游戏未初始化")

    state = engine.state
    country = state.countries.get(country_name)
    if not country:
        raise HTTPException(status_code=404, detail="国家不存在")
    
    if country.is_defeated:
        return {"actions": [], "message": "Country is defeated"}

    initial_ap = country.action_points
    context = _build_context(state, country_name)
    
    role = COUNTRY_TO_ROLE.get(country_name, "wei")
    
    prompt_type = f"country_{role}"
    if prompt_type not in SYSTEM_PROMPTS:
        prompt_type = "country_wei"

    ai_client = get_ai_client(role)
    ai_configured = ai_client.config.is_valid()

    async def stream_generator():
        yield f"data: {json.dumps({'type': 'start', 'country': country_name})}\n\n"
        
        thinking = ""
        content = ""
        was_truncated = False

        if ai_configured:
            async for chunk in ai_client.generate_stream(prompt_type, context):
                yield f"data: {json.dumps(chunk)}\n\n"
                if chunk.get("type") == "thinking":
                    thinking += chunk.get("content", "")
                elif chunk.get("type") == "content":
                    content += chunk.get("content", "")
                elif chunk.get("type") == "truncated":
                    was_truncated = True
        else:
            content = f"[{country_name}AI未配置，使用规则引擎自动决策]"
            yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
        
        yield f"data: {json.dumps({'type': 'thinking_end', 'thinking': thinking, 'content': content})}\n\n"
        
        ai = AIDecisionEngine(state)

        if ai_configured and content:
            if was_truncated:
                actions = ai.decide_actions(country_name, initial_ap)
            else:
                actions = ai.hybrid_decide(country_name, content, initial_ap)
        else:
            actions = ai.decide_actions(country_name, initial_ap)
        
        yield f"data: {json.dumps({'type': 'actions_start', 'count': len(actions)})}\n\n"
        
        results = []
        remaining_ap = initial_ap
        for i, action in enumerate(actions):
            cost = ACTION_COSTS.get(action["action_type"], 0)
            ap_cost = cost / 1000
            if remaining_ap < ap_cost:
                continue

            if action["action_type"] == "attack":
                target_name = action["parameters"].get("to", "")
                target_block = state.blocks.get(target_name)
                if target_block and target_block.owner == country_name:
                    continue

            if action["action_type"] == "move":
                from_name = action["parameters"].get("from", "")
                from_block = state.blocks.get(from_name)
                troops = action["parameters"].get("troops", 0)
                if from_block and from_block.garrison <= troops:
                    action["parameters"]["troops"] = max(from_block.garrison - 30, 0)
                    if action["parameters"]["troops"] <= 0:
                        continue

            if action["action_type"] == "harass":
                to_name = action["parameters"].get("to", "")
                to_block = state.blocks.get(to_name)
                if to_block and to_block.owner == country_name:
                    continue
                from_name = action["parameters"].get("from", "")
                if not from_name:
                    border = [b for b in state.blocks.values()
                              if b.owner == country_name and to_name in b.neighbors]
                    if border:
                        best = max(border, key=lambda b: b.garrison)
                        from_name = best.name
                        action["parameters"]["from"] = from_name
                        troops = action["parameters"].get("troops", 0)
                        if troops <= 0:
                            troops = min(best.garrison // 3, 300)
                        troops = max(50, min(troops, 500, best.garrison - 50))
                        action["parameters"]["troops"] = troops

            req = ActionRequest(
                country=country_name,
                action_type=action["action_type"],
                parameters=action["parameters"],
            )
            result = execute_action(req)
            
            if "error" not in result:
                remaining_ap -= ap_cost
                country.action_points = max(0, remaining_ap)
            
            results.append({
                "action": action["action_type"],
                "parameters": action["parameters"],
                "result": result,
            })
            
            yield f"data: {json.dumps({'type': 'action', 'index': i, 'action': action['action_type'], 'parameters': action['parameters'], 'result': result})}\n\n"
        
        state.last_round_actions[country_name] = results
        
        yield f"data: {json.dumps({'type': 'end', 'country': country_name, 'actions_executed': len(results), 'results': results})}\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
    )
