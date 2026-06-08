"""
游戏常量与配置模块

定义游戏中的所有常量、初始配置和可调参数。
包括游戏规则常量、行动成本、国家初始配置、中立势力配置、
武将配置、核心区域定义、颜色映射等。

本模块还提供从game_config.json加载外部配置的能力，
允许在不修改代码的情况下调整游戏参数。

主要组件：
- GAME_CONSTANTS: 游戏核心常量（回合限制、阈值、概率等）
- ACTION_COSTS: 各行动的行动点消耗（毫点单位）
- INITIAL_COUNTRIES: 三个主要国家的初始配置
- SPECIAL_NEUTRAL_FORCES: 五个中立势力的初始配置
- INITIAL_GENERALS: 九位初始武将配置
- CORE_REGIONS: 核心区域与边境区域定义
- HISTORICAL_CAPITALS: 各国历史首都
- load_game_config/get_config: 外部配置加载与查询
"""
import json
import os
from typing import Any, Dict

# 外部配置文件路径
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "game_config.json")
# 全局配置缓存
_game_config: Dict[str, Any] = {}

def load_game_config() -> Dict[str, Any]:
    """从game_config.json加载外部游戏配置。

    如果配置文件不存在或解析失败，返回空字典。

    Returns:
        配置字典
    """
    global _game_config
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                _game_config = json.load(f)
        except Exception:
            _game_config = {}
    return _game_config

def get_config(key: str, default: Any = None) -> Any:
    """通过点分隔路径查询配置值。

    支持嵌套字典的路径查询，例如"game_settings.initial_action_points"
    会依次查找 _game_config["game_settings"]["initial_action_points"]。

    Args:
        key: 点分隔的配置路径
        default: 路径不存在时的默认返回值

    Returns:
        配置值，路径不存在时返回default
    """
    if not _game_config:
        load_game_config()
    keys = key.split(".")
    value = _game_config
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    return value

# 模块加载时自动读取配置文件
load_game_config()

# ==================== 游戏核心常量 ====================
GAME_CONSTANTS = {
    # 地图与回合
    "TOTAL_BLOCKS": 361,                    # 地图总区块数
    "INITIAL_YEAR": 200,                    # 游戏起始年份（建安五年）
    "INITIAL_MONTH": 1,                     # 游戏起始月份
    "MAX_ROUNDS": 500,                      # 最大回合数

    # 行动点
    "ACTION_POINTS_PER_ROUND": 6.0,         # 每回合行动点（浮点数）
    "MILLIPOINTS_PER_ROUND": 6000,          # 每回合行动毫点（1行动点=1000毫点）

    # 称帝条件
    "EMPEROR_REQUIRED_BLOCKS": 45,          # 称帝所需最少区块数

    # 经济
    "TAX_DENOMINATOR": 1400,                # 税收动态系数分母（控制边际递减速率）
    "ENCLAVE_ORDER_PENALTY": -2,            # 飞地秩序惩罚

    # 人力
    "MANPOWER_RECOVERY_RATE": 0.12,         # 人力池每回合恢复率（基础人力的12%）

    # 战争压力
    "WAR_PRESSURE_COLLAPSE_THRESHOLD": 60,  # 战争压力崩溃阈值

    # 记忆
    "MEMORY_LIMIT": 5,                      # 每国最大记忆条数

    # 外交冷却
    "BETRAYAL_COOLDOWN": 2,                 # 背叛冷却回合数
    "MOVE_CAPITAL_COOLDOWN": 36,            # 迁都冷却回合数

    # 出兵限制
    "MIN_ATTACK_TROOPS_RATIO": 0.10,        # 最小出兵比例（守军的10%）
    "MIN_ATTACK_TROOPS_ABSOLUTE": 200,      # 最小绝对出兵数
    "MAX_HARASS_TROOPS": 500,               # 骚扰最大出兵数
    "MIN_HARASS_TROOPS": 50,                # 骚扰最小出兵数

    # 武将
    "GENERAL_DEATH_PROBABILITY": 0.25,      # 武将阵亡概率（25%）
    "GENERAL_OLD_AGE_DEATH_PROBABILITY": 0.005,  # 武将老死概率（0.5%/回合）

    # 战争疲劳
    "FATIGUE_START_ROUND": 400,             # 疲劳开始回合
    "FATIGUE_INTERVAL_MIN": 5,              # 疲劳触发间隔下限
    "FATIGUE_INTERVAL_MAX": 8,              # 疲劳触发间隔上限

    # 迷雾阶段
    "FOG_PHASE_1_END": 120,                 # 第一阶段结束回合
    "FOG_PHASE_2_END": 240,                 # 第二阶段结束回合

    # 以下常量从game.py中提取，用于其他模块引用
    "MIN_TROOP_RATIO": 0.1,                 # 最小出兵比例
    "MIN_TROOP_ABSOLUTE": 50,               # 最小绝对出兵数
    "CORE_BONUS_GARRISON": 8,               # 核心区块守军奖励
    "CORE_BONUS_ORDER": 5,                  # 核心区块秩序奖励
    "SPECIAL_FORCE_GOLD": 200,              # 中立势力金铢奖励
    "SPECIAL_FORCE_MORALE": 5,              # 中立势力士气奖励
    "SPECIAL_FORCE_ORDER": 3,               # 中立势力秩序奖励
    "HARASS_MAX_TROOPS": 500,               # 骚扰最大出兵数
    "HARASS_MIN_TROOPS": 50,                # 骚扰最小出兵数
    "DISBAND_MIN_GARRISON": 100,            # 裁军最低保留守军
    "MOVE_CAPITAL_MIN_GARRISON": 500,       # 迁都最低守军要求
    "MOVE_CAPITAL_ORDER_PENALTY": 8,        # 迁都秩序惩罚
    "OLD_CAPITAL_ORDER_PENALTY": 15,        # 旧首都秩序惩罚
    "OLD_CAPITAL_MORALE_PENALTY": 10,       # 旧首都士气惩罚
}

# ==================== 行动成本（毫点单位） ====================
# 1行动点 = 1000毫点，成本以毫点为单位便于精细控制
ACTION_COSTS = {
    "move": 500,              # 调兵：0.5行动点
    "attack": 1000,           # 进攻：1.0行动点
    "harass": 500,            # 骚扰：0.5行动点
    "recruit": 1000,          # 征兵：1.0行动点
    "develop": 1000,          # 发展：1.0行动点
    "tax": 500,               # 征税：0.5行动点
    "send_message": 500,      # 外交消息：0.5行动点
    "disband": 0,             # 裁军：免费
    "move_capital": 2000,     # 迁都：2.0行动点
    "declare_emperor": 0,     # 称帝：免费（但需满足条件）
}

def reload_action_costs():
    """从外部配置重新加载行动成本。

    允许通过game_config.json中的action_costs字段覆盖默认成本。
    合并策略：外部配置覆盖同名默认值，未指定的保持默认。
    """
    global ACTION_COSTS
    config_costs = get_config("action_costs", {})
    if config_costs:
        ACTION_COSTS = {**ACTION_COSTS, **config_costs}

# 模块加载时自动加载外部行动成本配置
reload_action_costs()

# ==================== 国家颜色映射 ====================
# 用于前端地图渲染，每个势力对应一个颜色
COUNTRY_COLORS = {
    "魏": "#5470a6",          # 蓝色系
    "蜀": "#c44e52",          # 红色系
    "吴": "#56a67b",          # 绿色系
    "neutral": "#b0b0b0",     # 中立：灰色
    "公孙度": "#8b7355",      # 棕色系
    "士燮": "#cd853f",        # 秘鲁色
    "南中": "#8b4513",        # 马鞍棕
    "山越": "#6b8e23",        # 橄榄绿
    "凉州": "#d2691e",        # 巧克力色
}

# ==================== 主要国家初始配置 ====================
# 定义魏/蜀/吴三个可操控国家的初始状态
INITIAL_COUNTRIES = {
    "魏": {
        "gold": 1800,         # 初始金铢（最富，中原沃土）
        "order": 78,          # 初始秩序
        "morale": 75,         # 初始士气
        "capital": "许昌",    # 首都
        "aggression": 0.6,    # 侵略性（最高，以攻代守）
        "loyalty": 0.4,       # 忠诚度（最低，多疑）
        "risk_preference": 0.7,  # 风险偏好（最高，敢于冒险）
        "blocks": [
            "许昌", "洛阳", "陈留", "宛城", "谯郡", "陈郡", "汝阴", "沛县",
            "山阳", "襄城", "荥阳", "开封", "睢阳", "濮阳", "任城", "定陶", "鄄城", "聊城"
        ],
    },
    "蜀": {
        "gold": 1200,         # 初始金铢（最穷，益州偏远）
        "order": 80,          # 初始秩序（最高，仁政安民）
        "morale": 82,         # 初始士气（最高，兴复汉室）
        "capital": "成都",    # 首都
        "aggression": 0.4,    # 侵略性（最低，守势为主）
        "loyalty": 0.8,       # 忠诚度（最高，君臣一心）
        "risk_preference": 0.5,  # 风险偏好（最低，稳健行事）
        "blocks": [
            "成都", "江阳", "汉嘉", "广汉", "梓潼", "德阳", "五城", "阳泉",
            "东广汉", "汉安", "乐山", "武阳", "僰道", "卑水"
        ],
    },
    "吴": {
        "gold": 1350,         # 初始金铢（中等，江东富庶）
        "order": 78,          # 初始秩序
        "morale": 76,         # 初始士气
        "capital": "建业",    # 首都
        "aggression": 0.5,    # 侵略性（中等，伺机而动）
        "loyalty": 0.6,       # 忠诚度（中等）
        "risk_preference": 0.6,  # 风险偏好（中等）
        "blocks": [
            "建业", "吴郡", "会稽", "豫章", "新都", "鄱阳", "庐陵北", "临海",
            "建安", "东阳", "南平", "富春", "钱唐", "乌程"
        ],
    },
}

# ==================== 特殊中立势力配置 ====================
# 五个不可操控的中立势力，不会主动进攻但会防守领地
SPECIAL_NEUTRAL_FORCES = {
    "公孙度": {
        "blocks": ["襄平", "新昌", "玄菟", "扶余南", "扶余北", "黑山南", "黑山北", "界鲜卑"],
        "capital": "襄平",
    },
    "士燮": {
        "blocks": ["龙编", "龙编西", "龙编中", "九真北", "九真南", "日南", "南海", "苍梧",
                   "郁林", "合浦", "高凉", "恩平", "朱崖州"],
        "capital": "龙编",
    },
    "南中": {
        "blocks": ["永昌", "云南", "建宁", "兴古", "且兰", "万宁", "朱提", "邛都", "会无", "堂狼", "昆明", "定苲"],
        "capital": "永昌",
    },
    "山越": {
        "blocks": ["武陵", "零陵", "桂阳", "营阳", "衡阳"],
        "capital": "武陵",
    },
    "凉州": {
        "blocks": ["金城", "西都", "姑臧", "酒泉东", "酒泉西", "敦煌"],
        "capital": "金城",
    },
}

# 中立势力名称列表
SPECIAL_NEUTRAL_FORCE_NAMES = list(SPECIAL_NEUTRAL_FORCES.keys())

# ==================== 初始武将配置 ====================
# 九位历史武将，分属三国，各具独特特性
INITIAL_GENERALS = [
    # 魏国武将
    {"name": "张辽", "country": "魏", "block": "合肥", "trait": "wei_zhen_xiaoyaojin"},   # 威震逍遥津：守军>=500时防御+15%
    {"name": "夏侯惇", "country": "魏", "block": "陈留", "trait": "ba_shi_dan_yan"},       # 拔矢啖睛：阵亡概率减半
    {"name": "曹仁", "country": "魏", "block": "樊城", "trait": "tie_bi"},                  # 铁壁：预留特性
    # 蜀国武将
    {"name": "关羽", "country": "蜀", "block": "江陵", "trait": "wei_zhen_huaxia"},         # 威震华夏：攻击+12%
    {"name": "张飞", "country": "蜀", "block": "阆中", "trait": "wan_ren_di"},              # 万人敌：目标有守军时攻击+10%
    {"name": "赵云", "country": "蜀", "block": "汉中", "trait": "yi_shen_shi_dan"},         # 一身是胆：预留特性
    # 吴国武将
    {"name": "周瑜", "country": "吴", "block": "柴桑", "trait": "huo_shao_chibi"},          # 火烧赤壁：防御+10%
    {"name": "陆逊", "country": "吴", "block": "江夏", "trait": "huo_shao_lianying"},       # 火烧连营：以少胜多时防御+20%
    {"name": "甘宁", "country": "吴", "block": "建业", "trait": "jin_fan_tu_ji"},           # 锦帆突袭：攻击+8%
]

# ==================== 核心区域定义 ====================
# 定义各州的核心区块和边境区块
# 区域名以"_frontier"结尾的为边境区域，其余为核心区域
CORE_REGIONS = {
    "司隶": ["洛阳", "许昌", "长安", "弘农", "河东", "河内", "河南"],
    "豫州": ["陈留", "汝南", "颍川", "谯郡", "梁国", "沛县"],
    "兖州": ["陈留东", "东郡", "济阴", "山阳", "任城"],
    "徐州": ["彭城", "下邳", "郯县", "广陵", "海安"],
    "青州": ["临淄", "北海", "东莱", "乐安", "长广"],
    "冀州": ["邺城", "邯郸", "信都", "常山", "中山", "清河", "渤海湾"],
    "幽州_core": ["蓟县", "右北平", "徐无", "临渝"],
    "幽州_frontier": ["昌黎", "柳城", "襄平", "玄菟", "扶余", "乐浪", "带方"],
    "并州_core": ["晋阳", "上党", "平阳", "雁门", "新兴"],
    "并州_frontier": ["盛乐", "五原", "朔方"],
    "凉州_core": ["武威", "金城", "西都", "张掖", "酒泉", "敦煌"],
    "凉州_frontier": ["居延", "玉门"],
    "益州_core": ["成都", "汉中", "江阳", "广汉", "梓潼", "巴郡", "阆中"],
    "益州_frontier": ["永昌", "云南", "建宁", "兴古", "且兰", "邛都", "朱提", "卑水"],
    "荆州": ["江陵", "襄阳", "樊城", "江夏", "武陵", "零陵", "桂阳", "长沙"],
    "扬州_core": ["建业", "吴郡", "会稽", "豫章", "柴桑", "庐陵", "临川", "丹阳"],
    "扬州_frontier": ["建安", "南平", "晋安", "永宁"],
    "交州": ["龙编", "九真", "日南", "南海", "苍梧", "郁林", "合浦", "高凉", "朱崖州"],
}

# ==================== 秩序/士气描述映射 ====================
# 将数值映射为文言描述，用于编年史系统
ORDER_MORALE_DESCRIPTIONS = {
    (80, 100): ("政通人和", "士气如虹"),
    (50, 79): ("局势稳定", "军心可用"),
    (30, 49): ("暗流涌动", "士气低迷"),
    (0, 29): ("民不聊生", "军心涣散"),
}

# ==================== 历史首都 ====================
# 各国的历史首都，控制历史首都是称帝的必要条件之一
HISTORICAL_CAPITALS = {
    "魏": ["许昌", "洛阳"],
    "蜀": ["成都", "长安"],
    "吴": ["建业", "武昌"],
}

# ==================== 可操控国家列表 ====================
PLAYABLE_COUNTRIES = ["魏", "蜀", "吴"]

# ==================== 编年史排除的国家 ====================
# 这些中立势力不参与编年史的态势分析
EXCLUDED_CHRONICLER_COUNTRIES = ["公孙度", "士燮", "南中", "山越", "凉州"]

# ==================== 国家名到AI角色映射 ====================
COUNTRY_TO_ROLE = {"魏": "wei", "蜀": "shu", "吴": "wu"}

# ==================== 专精标签映射 ====================
SPECIALIZATION_LABELS = {"farming": "农垦", "trade": "商贸", "fortress": "堡垒"}

# ==================== 战略目标标签映射 ====================
GOAL_LABELS = {
    "expand": "扩张",
    "defend": "防御",
    "revenge": "复仇",
    "stabilize": "稳定",
    "declare_emperor": "称帝",
}
