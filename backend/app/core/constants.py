import json
import os
from typing import Any, Dict

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "game_config.json")
_game_config: Dict[str, Any] = {}

def load_game_config() -> Dict[str, Any]:
    global _game_config
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                _game_config = json.load(f)
        except Exception:
            _game_config = {}
    return _game_config

def get_config(key: str, default: Any = None) -> Any:
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

load_game_config()

GAME_CONSTANTS = {
    "TOTAL_BLOCKS": 361,
    "INITIAL_YEAR": 200,
    "INITIAL_MONTH": 1,
    "MAX_ROUNDS": 500,
    "ACTION_POINTS_PER_ROUND": 6.0,
    "MILLIPOINTS_PER_ROUND": 6000,
    "EMPEROR_REQUIRED_BLOCKS": 45,
    "TAX_DENOMINATOR": 1400,
    "ENCLAVE_ORDER_PENALTY": -2,
    "MANPOWER_RECOVERY_RATE": 0.12,
    "WAR_PRESSURE_COLLAPSE_THRESHOLD": 60,
    "MEMORY_LIMIT": 5,
    "BETRAYAL_COOLDOWN": 2,
    "MOVE_CAPITAL_COOLDOWN": 36,
    "MIN_ATTACK_TROOPS_RATIO": 0.10,
    "MIN_ATTACK_TROOPS_ABSOLUTE": 200,
    "MAX_HARASS_TROOPS": 500,
    "MIN_HARASS_TROOPS": 50,
    "GENERAL_DEATH_PROBABILITY": 0.25,
    "GENERAL_OLD_AGE_DEATH_PROBABILITY": 0.005,
    "FATIGUE_START_ROUND": 400,
    "FATIGUE_INTERVAL_MIN": 5,
    "FATIGUE_INTERVAL_MAX": 8,
    "FOG_PHASE_1_END": 120,
    "FOG_PHASE_2_END": 240,
}

def get_action_cost(action: str) -> int:
    config_costs = get_config("action_costs", {})
    default_costs = {
        "move": 500,
        "attack": 1000,
        "harass": 500,
        "recruit": 1000,
        "develop": 1000,
        "tax": 500,
        "send_message": 500,
        "disband": 0,
        "move_capital": 2000,
        "declare_emperor": 0,
    }
    if config_costs and action in config_costs:
        return config_costs[action]
    return default_costs.get(action, 0)

ACTION_COSTS = {
    "move": 500,
    "attack": 1000,
    "harass": 500,
    "recruit": 1000,
    "develop": 1000,
    "tax": 500,
    "send_message": 500,
    "disband": 0,
    "move_capital": 2000,
    "declare_emperor": 0,
}

def reload_action_costs():
    global ACTION_COSTS
    config_costs = get_config("action_costs", {})
    if config_costs:
        ACTION_COSTS = {**ACTION_COSTS, **config_costs}

reload_action_costs()

COUNTRY_COLORS = {
    "魏": "#5470a6",
    "蜀": "#c44e52",
    "吴": "#56a67b",
    "neutral": "#b0b0b0",
    "公孙度": "#8b7355",
    "士燮": "#cd853f",
    "南中": "#8b4513",
    "山越": "#6b8e23",
    "凉州": "#d2691e",
}

INITIAL_COUNTRIES = {
    "魏": {
        "gold": 1800,
        "order": 78,
        "morale": 75,
        "capital": "许昌",
        "aggression": 0.6,
        "loyalty": 0.4,
        "risk_preference": 0.7,
        "blocks": [
            "许昌", "洛阳", "陈留", "宛城", "谯郡", "陈郡", "汝阴", "沛县",
            "山阳", "襄城", "荥阳", "开封", "睢阳", "濮阳", "任城", "定陶", "鄄城", "聊城"
        ],
    },
    "蜀": {
        "gold": 1200,
        "order": 80,
        "morale": 82,
        "capital": "成都",
        "aggression": 0.4,
        "loyalty": 0.8,
        "risk_preference": 0.5,
        "blocks": [
            "成都", "江阳", "汉嘉", "广汉", "梓潼", "德阳", "五城", "阳泉",
            "东广汉", "汉安", "乐山", "武阳", "僰道", "卑水"
        ],
    },
    "吴": {
        "gold": 1350,
        "order": 78,
        "morale": 76,
        "capital": "建业",
        "aggression": 0.5,
        "loyalty": 0.6,
        "risk_preference": 0.6,
        "blocks": [
            "建业", "吴郡", "会稽", "豫章", "新都", "鄱阳", "庐陵北", "临海",
            "建安", "东阳", "南平", "富春", "钱唐", "乌程"
        ],
    },
}

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

INITIAL_GENERALS = [
    {"name": "张辽", "country": "魏", "block": "合肥", "trait": "wei_zhen_xiaoyaojin"},
    {"name": "夏侯惇", "country": "魏", "block": "陈留", "trait": "ba_shi_dan_yan"},
    {"name": "曹仁", "country": "魏", "block": "樊城", "trait": "tie_bi"},
    {"name": "关羽", "country": "蜀", "block": "江陵", "trait": "wei_zhen_huaxia"},
    {"name": "张飞", "country": "蜀", "block": "阆中", "trait": "wan_ren_di"},
    {"name": "赵云", "country": "蜀", "block": "汉中", "trait": "yi_shen_shi_dan"},
    {"name": "周瑜", "country": "吴", "block": "柴桑", "trait": "huo_shao_chibi"},
    {"name": "陆逊", "country": "吴", "block": "江夏", "trait": "huo_shao_lianying"},
    {"name": "甘宁", "country": "吴", "block": "建业", "trait": "jin_fan_tu_ji"},
]

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

ORDER_MORALE_DESCRIPTIONS = {
    (80, 100): ("政通人和", "士气如虹"),
    (50, 79): ("局势稳定", "军心可用"),
    (30, 49): ("暗流涌动", "士气低迷"),
    (0, 29): ("民不聊生", "军心涣散"),
}

DIPLOMATIC_EVENTS = {
    "attack": "【系统】{attacker}向{defender}（{block}）发动军事进攻，两国进入交战状态。",
    "betrayal": "【系统】{attacker}背弃盟约，突袭{defender}（{block}）！同盟破裂。",
    "truce": "【系统】{country_a}与{country_b}宣布停战。",
    "alliance": "【系统】{country_a}与{country_b}缔结同盟，誓约共进退。",
    "break_alliance": "【系统】{country_a}宣布与{country_b}解除同盟关系。",
    "declare_emperor": "【系统】{country}君主登基称帝，国号{title}，改元{era}。",
    "capital_fallen": "【系统】{country}都城陷落！朝廷仓皇南迁，天下震动。",
    "nation_defeated": "【系统】{country}疆土尽丧，社稷覆亡。",
    "move_capital": "【系统】{country}迁都至{new_capital}，旧都萧条，新政伊始。",
}

HISTORICAL_EVENTS = {
    "guandu": {
        "name": "官渡之战",
        "trigger_date": (200, 10),
        "perceive_start": (200, 7),
        "perceive_content": "河北袁绍厉兵秣马",
        "conditions": {"country": "魏"},
        "effects": {"morale": 10, "gold": 500},
    },
    "sun_ce_death": {
        "name": "孙策遇刺",
        "trigger_date": (200, 4),
        "perceive_start": (200, 1),
        "perceive_content": "许贡门客阴蓄复仇之志",
        "conditions": {"country": "吴"},
        "effects": {"order": -8, "morale": -5},
    },
    "chibi": {
        "name": "赤壁之战",
        "trigger_date": (208, 11),
        "perceive_start": (208, 7),
        "perceive_content": "曹操有吞并江东之意",
        "conditions": {"country": "魏"},
        "effects": {},
    },
    "hanzhong": {
        "name": "汉中争夺战",
        "trigger_date": (217, 1),
        "perceive_start": (216, 7),
        "perceive_content": "汉中张鲁已降曹",
        "conditions": {},
        "effects": {},
    },
    "guanyu_northern": {
        "name": "关羽北伐",
        "trigger_date": (219, 7),
        "perceive_start": (219, 1),
        "perceive_content": "关羽北上之意昭然",
        "conditions": {"country": "蜀", "general": "关羽"},
        "effects": {},
    },
    "yiling": {
        "name": "夷陵之战",
        "trigger_date": (221, 7),
        "perceive_start": (221, 1),
        "perceive_content": "刘备誓言复仇",
        "conditions": {"country": "蜀"},
        "effects": {},
    },
    "nanzheng": {
        "name": "诸葛亮南征",
        "trigger_date": (225, 3),
        "perceive_start": (224, 7),
        "perceive_content": "南中蛮部屡叛",
        "conditions": {"country": "蜀", "general": "诸葛亮"},
        "effects": {},
    },
    "beifa": {
        "name": "诸葛亮北伐",
        "trigger_date": (227, 3),
        "perceive_start": (226, 7),
        "perceive_content": "北伐之议已定",
        "conditions": {"country": "蜀", "general": "诸葛亮"},
        "effects": {"action_points_bonus": 1.0},
    },
    "simazhao_coup": {
        "name": "司马懿政变",
        "trigger_date": (249, 1),
        "perceive_start": (248, 7),
        "perceive_content": "司马懿称病不朝",
        "conditions": {"country": "魏"},
        "effects": {"order": -15, "morale": -10},
    },
}
