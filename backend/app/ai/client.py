import json
from typing import AsyncGenerator, Dict
from pathlib import Path
from .config import AIModelConfig, AI_ROLES, SYSTEM_PROMPTS

CONFIG_FILE = Path(__file__).parent.parent.parent / "data" / "ai_config.json"


class AIClient:
    def __init__(self, config: AIModelConfig):
        self.config = config
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

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
        client = self._get_client()
        if not client:
            return self._fallback_generate(prompt_type, context)

        system_prompt = SYSTEM_PROMPTS.get(prompt_type, "").format(context=context)

        try:
            response = await client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "请给出你的分析和决策。"},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"AI调用失败: {str(e)}"

    async def generate_stream(self, prompt_type: str, context: str) -> AsyncGenerator[dict, None]:
        client = self._get_client()
        if not client:
            yield {"type": "content", "content": self._fallback_generate(prompt_type, context)}
            return

        system_prompt = SYSTEM_PROMPTS.get(prompt_type, "").format(context=context)

        try:
            kwargs = {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "请给出你的分析和决策。"},
                ],
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "stream": True,
            }

            response = await client.chat.completions.create(**kwargs)

            async for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    yield {"type": "thinking", "content": delta.reasoning_content}

                if delta.content:
                    yield {"type": "content", "content": delta.content}

        except Exception as e:
            yield {"type": "content", "content": f"[错误] {str(e)}"}

    def _fallback_generate(self, prompt_type: str, context: str) -> str:
        if "country" in prompt_type:
            return "基于当前局势分析，建议采取稳健策略，优先发展经济和军力。"
        elif "chronicler" in prompt_type:
            return "天下大势，分久必合，合久必分。各路诸侯割据一方，战火纷飞。"
        return "无法生成回复。"


class AIConfigManager:
    _instance = None
    _configs: Dict[str, AIModelConfig] = {}
    _clients: Dict[str, AIClient] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_configs()
        return cls._instance

    def _load_configs(self):
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
                                max_tokens=cfg.get("max_tokens", 2000),
                            )
            except Exception as e:
                print(f"加载AI配置失败: {e}")

        for role in AI_ROLES:
            if role not in self._configs:
                self._configs[role] = AIModelConfig()

    def _save_configs(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for role, config in self._configs.items():
            data[role] = {
                "model": config.model,
                "api_key": config.api_key,
                "base_url": config.base_url,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
            }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_config(self, role: str) -> AIModelConfig:
        role = role.lower()
        if role not in AI_ROLES:
            role = "wei"
        return self._configs.get(role, AIModelConfig())

    def set_config(self, role: str, config: AIModelConfig):
        role = role.lower()
        if role not in AI_ROLES:
            return
        self._configs[role] = config
        self._clients.pop(role, None)
        self._save_configs()

    def get_client(self, role: str) -> AIClient:
        role = role.lower()
        if role not in AI_ROLES:
            role = "wei"
        if role not in self._clients:
            self._clients[role] = AIClient(self._configs.get(role, AIModelConfig()))
        return self._clients[role]

    def get_all_configs(self) -> Dict[str, AIModelConfig]:
        return self._configs.copy()

    def is_all_configured(self) -> bool:
        for role in AI_ROLES:
            config = self._configs.get(role)
            if not config or not config.is_valid():
                return False
        return True

    def get_config_status(self) -> Dict[str, dict]:
        result = {}
        for role in AI_ROLES:
            config = self._configs.get(role, AIModelConfig())
            result[role] = {
                "model": config.model,
                "base_url": config.base_url,
                "has_api_key": bool(config.api_key),
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "is_valid": config.is_valid(),
            }
        return result


config_manager = AIConfigManager()
