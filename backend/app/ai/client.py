"""
AI客户端模块

提供与OpenAI兼容API的交互能力，包括非流式和流式两种调用模式。
当AI服务不可用或调用失败时，自动回退到预设的本地回复。

主要组件：
- AIClient: AI调用客户端，封装OpenAI兼容API的调用逻辑
- AIConfigManager: AI配置管理器（单例模式），管理各角色的模型配置和客户端实例
"""
import json
import logging
from typing import AsyncGenerator, Dict
from pathlib import Path
from .config import AIModelConfig, AI_ROLES, SYSTEM_PROMPTS

logger = logging.getLogger(__name__)

# AI配置文件路径，位于项目根目录的data文件夹下
CONFIG_FILE = Path(__file__).parent.parent.parent / "data" / "ai_config.json"


class AIClient:
    """AI调用客户端，封装与OpenAI兼容API的交互逻辑。

    支持两种调用模式：
    - 非流式调用(generate): 等待完整响应后返回
    - 流式调用(generate_stream): 逐token返回，支持思考过程输出

    当API不可用或调用失败时，自动回退到本地预设回复(_fallback_generate)。

    Attributes:
        config: AI模型配置，包含模型名称、API密钥、基础URL等
        _client: 延迟初始化的AsyncOpenAI客户端实例
    """

    def __init__(self, config: AIModelConfig):
        """初始化AI客户端。

        Args:
            config: AI模型配置对象，包含模型名称、API密钥、基础URL等参数
        """
        self.config = config
        self._client = None

    def _get_client(self):
        """获取或延迟初始化OpenAI异步客户端。

        采用延迟初始化策略，首次调用时才创建客户端实例。
        如果配置无效（缺少model/api_key/base_url），返回None。

        Returns:
            AsyncOpenAI客户端实例，配置无效或openai包未安装时返回None
        """
        if self._client is not None:
            return self._client

        if not self.config.is_valid():
            return None

        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
            return self._client
        except ImportError:
            return None

    async def generate(self, prompt_type: str, context: str) -> str:
        """非流式调用AI模型生成回复。

        根据prompt_type选择对应的系统提示词，将context注入后发送给AI模型。
        当输出因max_tokens限制被截断时，自动追加补充行动提示。

        Args:
            prompt_type: 提示词类型，如"country_wei"、"country_shu"、"chronicler"等，
                         用于从SYSTEM_PROMPTS中选取对应的系统提示词
            context: 当前局势上下文信息，将被注入到系统提示词的{context}占位符中

        Returns:
            AI生成的文本回复。API不可用时返回本地回退回复。

        Side Effects:
            - API调用失败时记录错误日志
            - 输出被截断时在末尾追加补充行动提示
        """
        client = self._get_client()
        if not client:
            return self._fallback_generate(prompt_type, context)

        # 根据prompt_type获取系统提示词，并将context注入占位符
        system_prompt = SYSTEM_PROMPTS.get(prompt_type, "").format(context=context)
        max_tokens = self.config.get_effective_max_tokens(prompt_type)

        try:
            response = await client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "请给出你的分析和决策。"},
                ],
                temperature=self.config.temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content or ""
            finish_reason = response.choices[0].finish_reason if response.choices else None
            # 输出被截断时，追加补充行动提示，确保AI至少执行基本行动（如征税）
            if finish_reason == "length":
                content += "\n\n（输出因长度限制被截断，以下为补充行动）\n征税\n"
            return content
        except Exception as e:
            logger.error(f"AI调用失败 ({prompt_type}): {e}")
            return self._fallback_generate(prompt_type, context)

    async def generate_stream(self, prompt_type: str, context: str) -> AsyncGenerator[dict, None]:
        """流式调用AI模型，逐token返回生成内容。

        支持三种事件类型：
        - "thinking": AI的思考过程（如深度推理模型的思维链），仅当模型返回reasoning_content时产生
        - "content": AI生成的正文内容
        - "truncated": 输出因长度限制被截断的信号

        Args:
            prompt_type: 提示词类型，同generate方法
            context: 当前局势上下文信息

        Yields:
            dict: 包含type和content字段的事件字典，type为"thinking"/"content"/"truncated"之一

        Side Effects:
            - API调用失败时记录错误日志并yield回退回复
        """
        client = self._get_client()
        if not client:
            yield {"type": "content", "content": self._fallback_generate(prompt_type, context)}
            return

        # 根据prompt_type获取系统提示词，并将context注入占位符
        system_prompt = SYSTEM_PROMPTS.get(prompt_type, "").format(context=context)
        max_tokens = self.config.get_effective_max_tokens(prompt_type)

        try:
            kwargs = {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "请给出你的分析和决策。"},
                ],
                "temperature": self.config.temperature,
                "max_tokens": max_tokens,
                "stream": True,
                # 请求返回token使用量信息，用于监控API消耗
                "stream_options": {"include_usage": True},
            }

            response = await client.chat.completions.create(**kwargs)

            async for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                # 处理深度推理模型的思考过程输出（如DeepSeek的reasoning_content）
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    yield {"type": "thinking", "content": delta.reasoning_content}

                # 处理正文内容输出
                if delta.content:
                    yield {"type": "content", "content": delta.content}

                # 输出被截断时发送截断信号
                if chunk.choices[0].finish_reason == "length":
                    yield {"type": "truncated", "content": ""}

        except Exception as e:
            logger.error(f"AI流式调用失败 ({prompt_type}): {e}")
            yield {"type": "content", "content": self._fallback_generate(prompt_type, context)}

    def _fallback_generate(self, prompt_type: str, context: str) -> str:
        """本地回退生成，当AI服务不可用时提供预设回复。

        根据prompt_type返回不同风格的预设文本：
        - 国家决策类：返回稳健策略建议
        - 史官类：返回文言风格的局势描述
        - 其他：返回通用错误提示

        Args:
            prompt_type: 提示词类型，用于选择回退文本风格
            context: 上下文信息（回退模式下未使用，但保留接口一致性）

        Returns:
            预设的回退文本
        """
        if "country" in prompt_type:
            return "基于当前局势分析，建议采取稳健策略，优先发展经济和军力。"
        elif "chronicler" in prompt_type:
            return "天下大势，分久必合，合久必分。各路诸侯割据一方，战火纷飞。"
        return "无法生成回复。"


class AIConfigManager:
    """AI配置管理器，采用单例模式管理各AI角色的模型配置和客户端实例。

    管理四个AI角色：魏(wei)、蜀(shu)、吴(wu)、史官(chronicler)，
    每个角色拥有独立的模型配置（可配置不同的模型、API密钥、基础URL等）。
    配置持久化存储在data/ai_config.json文件中。

    采用单例模式确保全局只有一个配置管理器实例，避免配置冲突。

    Attributes:
        _instance: 单例实例
        _configs: 各角色的AI模型配置字典，键为角色名，值为AIModelConfig
        _clients: 各角色的AI客户端实例字典，键为角色名，值为AIClient
    """

    _instance = None
    _configs: Dict[str, AIModelConfig] = {}
    _clients: Dict[str, AIClient] = {}

    def __new__(cls):
        """单例模式实现，确保全局只有一个配置管理器实例。

        首次创建时自动加载持久化配置文件。

        Returns:
            AIConfigManager的唯一实例
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_configs()
        return cls._instance

    def _load_configs(self):
        """从配置文件加载各角色的AI模型配置。

        从data/ai_config.json读取配置，为每个AI_ROLES中的角色创建对应的AIModelConfig。
        如果配置文件不存在或某个角色缺少配置，使用默认空配置。

        Side Effects:
            - 读取CONFIG_FILE文件
            - 填充self._configs字典
        """
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for role in AI_ROLES:
                        if role in data:
                            cfg = data[role]
                            self._configs[role] = AIModelConfig(
                                model=cfg.get("model", ""),
                                api_key=cfg.get("api_key", ""),
                                base_url=cfg.get("base_url", ""),
                                temperature=cfg.get("temperature", 0.7),
                                max_tokens=cfg.get("max_tokens", 4096),
                                streaming=cfg.get("streaming", True),
                                deep_thinking=cfg.get("deep_thinking", True),
                            )
            except Exception as e:
                logger.error(f"加载AI配置失败: {e}")

        # 为缺少配置的角色创建默认空配置
        for role in AI_ROLES:
            if role not in self._configs:
                self._configs[role] = AIModelConfig()

    def _save_configs(self):
        """将当前配置持久化保存到配置文件。

        将所有角色的配置序列化为JSON格式写入data/ai_config.json。
        如果data目录不存在，自动创建。

        Side Effects:
            - 创建CONFIG_FILE的父目录（如不存在）
            - 写入CONFIG_FILE文件
        """
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for role, config in self._configs.items():
            data[role] = {
                "model": config.model,
                "api_key": config.api_key,
                "base_url": config.base_url,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "streaming": config.streaming,
                "deep_thinking": config.deep_thinking,
            }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_config(self, role: str) -> AIModelConfig:
        """获取指定角色的AI模型配置。

        Args:
            role: 角色名称（如"wei"、"shu"、"wu"、"chronicler"），不区分大小写。
                  如果角色不在AI_ROLES中，默认返回魏国配置。

        Returns:
            对应角色的AIModelConfig配置对象
        """
        role = role.lower()
        if role not in AI_ROLES:
            role = "wei"
        return self._configs.get(role, AIModelConfig())

    def set_config(self, role: str, config: AIModelConfig):
        """设置指定角色的AI模型配置并持久化保存。

        更新配置后，会清除该角色的旧客户端实例（下次获取时重新创建），
        并将新配置写入配置文件。

        Args:
            role: 角色名称，必须在AI_ROLES中，否则忽略
            config: 新的AI模型配置对象

        Side Effects:
            - 清除该角色的旧AIClient实例
            - 将配置写入持久化文件
        """
        role = role.lower()
        if role not in AI_ROLES:
            return
        self._configs[role] = config
        # 清除旧客户端，确保下次获取时使用新配置创建
        self._clients.pop(role, None)
        self._save_configs()

    def get_client(self, role: str) -> AIClient:
        """获取指定角色的AI客户端实例。

        如果该角色尚无客户端实例，使用其配置创建新实例并缓存。

        Args:
            role: 角色名称，不在AI_ROLES中时默认使用魏国

        Returns:
            对应角色的AIClient实例
        """
        role = role.lower()
        if role not in AI_ROLES:
            role = "wei"
        if role not in self._clients:
            self._clients[role] = AIClient(self._configs.get(role, AIModelConfig()))
        return self._clients[role]

    def get_all_configs(self) -> Dict[str, AIModelConfig]:
        """获取所有角色的AI模型配置副本。

        Returns:
            角色名到AIModelConfig的字典副本
        """
        return self._configs.copy()

    def is_all_configured(self) -> bool:
        """检查所有AI角色是否都已有效配置。

        所有角色都必须有有效的model、api_key和base_url才算配置完成。

        Returns:
            True表示所有角色配置有效，False表示至少有一个角色未配置
        """
        for role in AI_ROLES:
            config = self._configs.get(role)
            if not config or not config.is_valid():
                return False
        return True

    def get_config_status(self) -> Dict[str, dict]:
        """获取所有角色的配置状态摘要。

        返回每个角色的配置信息（隐藏API密钥原文，仅显示是否已设置），
        用于前端展示配置状态。

        Returns:
            角色名到配置状态字典的映射，每个字典包含：
            - model: 模型名称
            - base_url: API基础URL
            - has_api_key: 是否已设置API密钥（布尔值，不暴露密钥原文）
            - temperature: 温度参数
            - max_tokens: 最大token数
            - streaming: 是否启用流式输出
            - deep_thinking: 是否启用深度思考
            - is_valid: 配置是否有效
        """
        result = {}
        for role in AI_ROLES:
            config = self._configs.get(role, AIModelConfig())
            result[role] = {
                "model": config.model,
                "base_url": config.base_url,
                "has_api_key": bool(config.api_key),
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "streaming": config.streaming,
                "deep_thinking": config.deep_thinking,
                "is_valid": config.is_valid(),
            }
        return result


# 全局配置管理器单例，供其他模块直接使用
config_manager = AIConfigManager()
