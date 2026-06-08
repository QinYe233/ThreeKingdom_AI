"""
AI API模块

处理AI配置管理、连接测试、AI决策流式输出等。
本模块提供以下功能：
- AI角色配置的查询、保存、状态检查
- AI连接测试（使用表单配置或已保存配置）
- AI思考接口（仅思考不执行，SSE流式返回）
- AI思考并执行行动接口（SSE流式返回思考过程+决策+执行结果）
- 上下文构建：将游戏状态转换为AI可理解的文本格式
"""
import logging
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
from .game_state_holder import get_engine, is_ai_processing, acquire_ai_lock, release_ai_lock
from .game import execute_action, ActionRequest

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/ai", tags=["ai"])


class AIConfigRequest(BaseModel):
    """AI配置请求模型

    Attributes:
        role: AI角色名称（wei/shu/wu/chronicler）
        model: 模型名称（如 gpt-4o、deepseek-chat 等）
        api_key: API密钥，传入 __keep_existing__ 可保留已有密钥
        base_url: API基础URL
        temperature: 生成温度，越高越随机，默认0.7
        max_tokens: 最大生成token数，默认2000
        streaming: 是否启用流式输出，默认True
        deep_thinking: 是否启用深度思考（LLM决策），默认True
    """
    role: str
    model: str
    api_key: str
    base_url: str
    temperature: float = 0.7
    max_tokens: int = 2000
    streaming: bool = True
    deep_thinking: bool = True


class TestConnectionRequest(BaseModel):
    """测试连接请求模型

    Attributes:
        model: 模型名称
        api_key: API密钥
        base_url: API基础URL
    """
    model: str
    api_key: str
    base_url: str


@router.get("/status")
def get_status():
    """
    获取AI配置状态

    返回所有角色（魏/蜀/吴/史官）的配置情况，包括角色名称、描述、
    各角色配置详情和是否全部配置完成。

    Returns:
        dict: 包含角色信息、各角色配置、是否全部配置完成
    """
    status = get_config_status()
    return {
        "roles": {role: {"name": ROLE_NAMES.get(role, role), "description": ROLE_DESCRIPTIONS.get(role, "")} for role in AI_ROLES},
        "configs": status,
        "all_configured": is_all_configured(),
    }


@router.get("/config/{role}")
def get_config(role: str):
    """
    获取指定角色的AI配置

    Args:
        role: AI角色名称（wei/shu/wu/chronicler）

    Returns:
        dict: 该角色的配置信息，包括模型、URL、是否有API Key、是否有效

    Raises:
        HTTPException: 无效角色名(400)
    """
    role = role.lower()
    if role not in AI_ROLES:
        raise HTTPException(status_code=400, detail=f"无效的角色: {role}")

    status = get_config_status()
    return status.get(role, {"model": "", "base_url": "", "has_api_key": False, "is_valid": False})


@router.post("/config")
def save_config(req: AIConfigRequest):
    """
    保存AI配置

    支持保留已有API Key（传入 __keep_existing__），避免前端每次都需要重新输入密钥。
    保存后自动持久化到配置文件。

    Args:
        req: AI配置请求

    Returns:
        dict: 保存状态和消息

    Raises:
        HTTPException: 无效角色(400)、缺少模型名(400)、缺少URL(400)、缺少API Key(400)
    """
    role = req.role.lower()
    if role not in AI_ROLES:
        raise HTTPException(status_code=400, detail=f"无效的角色: {role}")

    if not req.model:
        raise HTTPException(status_code=400, detail="请输入模型名称")
    if not req.base_url:
        raise HTTPException(status_code=400, detail="请输入Base URL")

    existing_config = get_ai_config(role)

    # 处理API Key保留逻辑：前端可传入 __keep_existing__ 避免暴露已保存的密钥
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
        streaming=req.streaming,
        deep_thinking=req.deep_thinking,
    )
    set_ai_config(role, config)
    return {"status": "ok", "message": f"{ROLE_NAMES.get(role, role)}配置已保存"}


@router.post("/test-connection")
async def test_connection(req: TestConnectionRequest):
    """
    测试AI连接（使用表单中的配置）

    使用前端表单中填写的配置（非已保存配置）发送测试请求，
    与实际AI调用路径一致（使用OpenAI库）。

    Args:
        req: 测试连接请求，包含模型、API Key、Base URL

    Returns:
        dict: 连接测试结果，包含状态、消息、模型名

    Raises:
        HTTPException: 缺少参数(400)、认证失败(401)、模型不存在(404)、
                       连接超时(504)、无法连接(503)、其他错误(500)
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
        # 发送最简请求测试连接是否正常
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
        # 根据错误类型返回不同的HTTP状态码和提示
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

    使用后端已保存的API Key进行测试，无需前端重新输入密钥。

    Args:
        role: AI角色名称（wei/shu/wu/chronicler）

    Returns:
        dict: 连接测试结果

    Raises:
        HTTPException: 无效角色(400)、未完成配置(400)、认证失败(401)等
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
    """
    检查所有AI角色是否都已配置

    Returns:
        dict: 包含 all_configured 布尔值
    """
    return {"all_configured": is_all_configured()}


def _build_context(state, country_name: str) -> str:
    """
    构建AI决策所需的上下文文本

    将游戏状态转换为结构化的中文文本，供LLM理解当前局势。
    包含：国力概况、上回战报、可发展/征兵领地、秩序不稳之地、
    边境军情、邦交关系、可行之事等。

    Args:
        state: 当前游戏状态
        country_name: 国家名称

    Returns:
        str: 格式化的上下文文本，国家不存在时返回空字符串
    """
    country = state.countries.get(country_name)
    if not country:
        return ""

    # 统计国家基本数据
    blocks = [b for b in state.blocks.values() if b.owner == country_name]
    total_garrison = sum(b.garrison for b in blocks)
    total_manpower = sum(b.manpower_pool for b in blocks)

    # 收集边境信息：己方区块与敌方区块相邻的情况
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

    # 可发展领地：发展次数<3、补给连通、非新占领
    developable = []
    for b in blocks:
        if b.develop_count < 3 and b.supply_connected and not b.recently_conquered:
            developable.append(f"  {b.name}(人力池{b.manpower_pool}, 已发展{b.develop_count}次)")

    # 可征兵之地：人力池>=10、非新占领
    recruitable = []
    for b in blocks:
        if b.manpower_pool >= 10 and not b.recently_conquered:
            recruitable.append(f"  {b.name}(人力池{b.manpower_pool}, 守军{b.garrison})")

    # 秩序不稳之地：秩序<50
    low_order_blocks = []
    for b in blocks:
        if b.order < 50:
            low_order_blocks.append(f"  {b.name}(秩序{b.order})")

    # 构建上回战报：从上回合行动记录中提取关键信息
    last_actions_text = ""
    last_actions = state.last_round_actions.get(country_name, [])
    if last_actions:
        last_actions_text = "【上回战报】\n"
        for i, action in enumerate(last_actions, 1):
            action_type = action.get("action", "未知")
            params = action.get("parameters", {})
            result = action.get("result", {})

            # 根据行动类型格式化战报文本
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

    # 组装完整上下文
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

【可行之事】（你有{country.action_points:.1f}行动点，务必全部消耗，不留余量）
  进攻(1点)：从己方出兵攻邻地 | 征兵(1点)：在己地征兵(200金)
  发展(1点)：提升人力产出(400金) | 征税(0.5点)：收取税金
  调兵(0.5点)：己方领地间调兵 | 骚扰(0.5点)：扰敌士气秩序"""

    return context


@router.post("/think/{country_name}")
async def ai_think(country_name: str):
    """
    AI思考接口（仅思考不执行）

    流式返回AI的思考过程，不执行任何行动。
    用于让玩家预览AI的决策思路。

    Args:
        country_name: 国家名称

    Returns:
        StreamingResponse: SSE流，包含思考过程和决策内容

    Raises:
        HTTPException: 游戏未初始化(400)、国家不存在(404)
    """
    engine = get_engine()
    if not engine.state:
        raise HTTPException(status_code=400, detail="游戏未初始化")

    state = engine.state
    context = _build_context(state, country_name)

    if not context:
        raise HTTPException(status_code=404, detail="国家不存在")

    # 根据国家名映射到AI角色
    role = COUNTRY_TO_ROLE.get(country_name, "wei")

    # 选择对应的系统提示词
    prompt_type = f"country_{role}"
    if prompt_type not in SYSTEM_PROMPTS:
        prompt_type = "country_wei"

    ai_client = get_ai_client(role)
    ai_configured = ai_client.config.is_valid()

    async def stream_generator():
        """SSE流生成器：逐块返回AI思考内容"""
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

    流式返回思考过程、决策内容、执行结果。
    流程：
    1. 获取AI锁（防止并发执行）
    2. 构建上下文，调用LLM生成思考内容（流式或非流式）
    3. 根据LLM输出解析行动（或使用规则引擎回退）
    4. 逐个执行行动并流式返回结果
    5. 释放AI锁

    SSE事件类型：
    - start: 开始处理
    - thinking: 深度思考内容（如模型支持）
    - content: LLM生成的决策文本
    - truncated: 输出被截断
    - thinking_end: 思考阶段结束
    - actions_start: 开始执行行动
    - action: 单个行动执行结果
    - end: 全部完成

    Args:
        country_name: 国家名称

    Returns:
        StreamingResponse: SSE流

    Raises:
        HTTPException: AI正在处理中(409)、游戏未初始化(400)、国家不存在(404)
    """
    # 检查AI是否正在处理，防止并发
    if is_ai_processing():
        raise HTTPException(status_code=409, detail="AI is currently processing, please wait")

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

    # 根据国家名映射到AI角色和系统提示词
    role = COUNTRY_TO_ROLE.get(country_name, "wei")

    prompt_type = f"country_{role}"
    if prompt_type not in SYSTEM_PROMPTS:
        prompt_type = "country_wei"

    ai_client = get_ai_client(role)
    ai_configured = ai_client.config.is_valid()

    async def stream_generator():
        """SSE流生成器：思考→决策→执行，全程流式返回"""
        # 获取AI锁，确保同一时间只有一个AI在执行
        acquired = await acquire_ai_lock()
        if not acquired:
            yield f"data: {json.dumps({'type': 'error', 'message': 'AI is currently processing'})}\n\n"
            return
        try:
            yield f"data: {json.dumps({'type': 'start', 'country': country_name})}\n\n"

            thinking = ""
            content = ""
            was_truncated = False

            config = ai_client.config

            # 阶段1：LLM思考
            # 如果深度思考开启且AI已配置，调用LLM生成决策
            if ai_configured and config.deep_thinking:
                if config.streaming:
                    # 流式模式：逐块接收思考内容和决策文本
                    async for chunk in ai_client.generate_stream(prompt_type, context):
                        yield f"data: {json.dumps(chunk)}\n\n"
                        if chunk.get("type") == "thinking":
                            thinking += chunk.get("content", "")
                        elif chunk.get("type") == "content":
                            content += chunk.get("content", "")
                        elif chunk.get("type") == "truncated":
                            was_truncated = True
                else:
                    # 非流式模式：一次性获取全部内容
                    llm_content = await ai_client.generate(prompt_type, context)
                    content = llm_content
                    yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
            else:
                # AI未配置或深度思考关闭，使用规则引擎
                content = f"[{country_name}AI未配置或深度思考已关闭，使用规则引擎自动决策]"
                yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"

            yield f"data: {json.dumps({'type': 'thinking_end', 'thinking': thinking, 'content': content})}\n\n"

            # 阶段2：决策解析
            ai = AIDecisionEngine(state)

            if ai_configured and config.deep_thinking and content:
                if was_truncated:
                    # 输出被截断时，LLM内容可能不完整，回退到规则引擎
                    actions = ai.decide_actions(country_name, initial_ap)
                else:
                    # 混合决策：结合LLM输出和规则引擎
                    actions = ai.hybrid_decide(country_name, content, initial_ap)
            else:
                # 纯规则引擎决策
                actions = ai.decide_actions(country_name, initial_ap)

            logger.info(f"[AI-SSE] {country_name}: decided {len(actions)} actions, AP={initial_ap}")
            for i, action in enumerate(actions):
                logger.info(f"[AI-SSE] {country_name} action[{i}]: {action['action_type']} {action.get('parameters', {})}")

            yield f"data: {json.dumps({'type': 'actions_start', 'count': len(actions)})}\n\n"

            # 阶段3：逐个执行行动
            results = []
            for i, action in enumerate(actions):
                cost = ACTION_COSTS.get(action["action_type"], 0)
                ap_cost = cost / 1000
                # 行动点不足时跳过（execute_action 也会检查，此处提前过滤减少无效调用）
                if country.action_points < ap_cost:
                    continue

                # 安全检查：防止AI攻击己方区块
                if action["action_type"] == "attack":
                    target_name = action["parameters"].get("to", "")
                    target_block = state.blocks.get(target_name)
                    if target_block and target_block.owner == country_name:
                        continue

                # 安全检查：调兵时确保源区块留有最低守军
                if action["action_type"] == "move":
                    from_name = action["parameters"].get("from", "")
                    from_block = state.blocks.get(from_name)
                    troops = action["parameters"].get("troops", 0)
                    if from_block and from_block.garrison <= troops:
                        # 自动调整调兵数量，保留30守军
                        action["parameters"]["troops"] = max(from_block.garrison - 30, 0)
                        if action["parameters"]["troops"] <= 0:
                            continue

                # 骚扰行动的安全检查和参数补全
                if action["action_type"] == "harass":
                    to_name = action["parameters"].get("to", "")
                    to_block = state.blocks.get(to_name)
                    # 防止骚扰己方区块
                    if to_block and to_block.owner == country_name:
                        continue
                    # 自动选择最佳出发区块
                    from_name = action["parameters"].get("from", "")
                    if not from_name:
                        border = [b for b in state.blocks.values()
                                  if b.owner == country_name and to_name in b.neighbors]
                        if border:
                            best = max(border, key=lambda b: b.garrison)
                            from_name = best.name
                            action["parameters"]["from"] = from_name
                            # 自动计算骚扰兵力
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
                try:
                    result = execute_action(req)
                except Exception as e:
                    result = {"error": str(e.detail) if hasattr(e, 'detail') else str(e)}

                # execute_action 内部已扣除行动点，此处不再重复扣除

                if "error" in result:
                    logger.warning(f"[AI-SSE] {country_name} action[{i}] FAILED: {action['action_type']} error={result.get('error', 'unknown')}")
                else:
                    logger.info(f"[AI-SSE] {country_name} action[{i}] OK: {action['action_type']}")

                results.append({
                    "action": action["action_type"],
                    "parameters": action["parameters"],
                    "result": result,
                })

                yield f"data: {json.dumps({'type': 'action', 'index': i, 'action': action['action_type'], 'parameters': action['parameters'], 'result': result})}\n\n"

            # 保存本回合行动记录，供下回合构建上下文使用
            state.last_round_actions[country_name] = results

            yield f"data: {json.dumps({'type': 'end', 'country': country_name, 'actions_executed': len(results), 'results': results})}\n\n"
        finally:
            # 确保释放AI锁
            release_ai_lock()

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
    )
