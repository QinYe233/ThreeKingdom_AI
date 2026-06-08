"""
数据模型模块

定义游戏中所有核心数据结构，使用Pydantic BaseModel确保数据验证和序列化。
本模块是游戏状态的数据层，所有游戏逻辑都基于这些模型进行操作。

模型层次结构：
- GameState: 顶层游戏状态，包含所有子模型
  - Block: 区块（地图基本单元）
  - Country: 国家
  - Relation: 国家间外交关系
  - General: 武将
  - DiplomaticMessage: 外交消息
  - BattleResult: 战斗结果
  - Action: 行动指令
  - Timeline: 时间线
  - CountryMemory: 国家记忆
  - BlockVisibility: 区块可见性（迷雾系统）

枚举类型：
- RegionType: 区块类型（核心/边境）
- GeographicTrait: 地理特性（农业/贸易/要塞/无）
- BlockSpecialization: 区块专精（农垦/商贸/堡垒）
- StrategicGoal: 战略目标（扩张/防御/复仇/稳定/称帝）
- MemoryImpact: 记忆影响程度（高/中/低）
- MemoryEmotion: 记忆情感类型（愤怒/恐惧/感恩/悲伤）
- GeneralTrait: 武将特性（九种历史特性）
- ActionType: 行动类型（十种行动）
- WinRateLabel: 胜率标签（高/中/低/未知）
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class RegionType(str, Enum):
    """区块类型枚举，区分核心领土和边境地区。

    核心区块享有守军和秩序奖励，边境区块征兵效率降低。
    """
    CORE = "core"          # 核心领土：守军+8，秩序+5
    FRONTIER = "frontier"  # 边境地区：征兵效率×0.8


class GeographicTrait(str, Enum):
    """地理特性枚举，表示区块的天然地理优势。

    地理特性与专精匹配时可获得额外加成（synergy效果）。
    """
    FARMING = "farming"    # 农业：农垦专精额外+100人力
    TRADE = "trade"        # 贸易：商贸专精税收倍率1.8（而非1.5）
    FORTRESS = "fortress"  # 要塞：堡垒专精防御1.08（而非1.05）
    NONE = "none"          # 无特殊地理特性


class BlockSpecialization(str, Enum):
    """区块专精枚举，满发展（3级）后可选择的方向。

    每个区块只能选择一种专精，不可更改。
    """
    FARMING = "farming"    # 农垦：基础人力+300~400
    TRADE = "trade"        # 商贸：税收倍率1.5~1.8
    FORTRESS = "fortress"  # 堡垒：防御下限1.05~1.08


class Block(BaseModel):
    """区块模型，地图的基本单元。

    每个区块代表三国时期的一个地理区域，拥有独立的经济、军事和政治属性。
    区块是税收、征兵、发展的基本单位，也是战斗的攻防目标。

    Attributes:
        name: 区块名称（如"许昌"、"成都"）
        neighbors: 相邻区块名称列表
        base_manpower: 基础人力，决定税收和征兵上限
        manpower_pool: 当前人力池，征兵时消耗
        owner: 所有者国家名，"neutral"表示中立
        garrison: 守军数量
        order: 秩序值（0-100），影响税收和征兵效率
        morale: 士气值（0-100），影响战斗表现
        last_recruit_round: 上次征兵回合，用于冷却期计算
        develop_count: 发展次数（0-3），3次后可设专精
        recently_conquered: 是否新占领（限制征兵和发展）
        region_type: 区块类型（核心/边境）
        supply_connected: 是否与首都补给连通
        geographic_trait: 地理特性
        specialization: 区块专精（需满发展后设置）
    """
    name: str
    neighbors: list[str] = Field(default_factory=list)
    base_manpower: int = 0
    manpower_pool: int = 0
    owner: str = "neutral"
    garrison: int = 0
    order: int = 50
    morale: int = 50
    last_recruit_round: int = -10
    develop_count: int = 0
    recently_conquered: bool = False
    region_type: RegionType = RegionType.CORE
    supply_connected: bool = True
    geographic_trait: GeographicTrait = GeographicTrait.NONE
    specialization: Optional[BlockSpecialization] = None


class StrategicGoal(str, Enum):
    """战略目标枚举，影响AI决策方向。

    由游戏引擎根据国家状况自动更新：
    - STABILIZE: 内政不稳时优先恢复秩序
    - DEFEND: 预留，当前未使用
    - REVENGE: 有高仇怨时优先攻击仇敌
    - EXPAND: 默认目标，优先扩张领土
    - DECLARE_EMPEROR: 满足条件时称帝
    """
    EXPAND = "expand"                    # 扩张
    DEFEND = "defend"                    # 防御
    REVENGE = "revenge"                  # 复仇
    STABILIZE = "stabilize"              # 稳定
    DECLARE_EMPEROR = "declare_emperor"  # 称帝


class Country(BaseModel):
    """国家模型，代表一个政治实体。

    包含国家的经济、政治、军事和外交属性。
    三个主要国家（魏/蜀/吴）可由AI或玩家控制，
    中立势力仅自动防守。

    Attributes:
        name: 国家名称
        gold: 金铢储备，用于征兵、发展等
        order: 国家秩序（0-100），影响税收和稳定
        morale: 国家士气（0-100），影响战斗力
        capital: 首都区块名
        in_exile: 是否处于流亡状态（首都被占）
        former_capital: 原首都名（流亡时记录）
        exile_rounds: 流亡剩余回合数
        has_declared_emperor: 是否已称帝
        goal: 当前战略目标
        aggression: 侵略性（0-1），影响AI进攻倾向
        loyalty: 忠诚度（0-1），影响AI同盟倾向
        risk_preference: 风险偏好（0-1），影响AI冒险行为
        is_defeated: 是否已灭亡
        last_betrayal_round: 上次背叛回合，用于冷却期
        last_move_capital_round: 上次迁都回合，用于冷却期
        action_points: 当前行动点（毫点单位，6000=6.0行动点）
        war_pressure: 战争压力，累积到阈值可能崩溃
    """
    name: str
    gold: int = 0
    order: int = 50
    morale: int = 50
    capital: str = ""
    in_exile: bool = False
    former_capital: Optional[str] = None
    exile_rounds: int = 0
    has_declared_emperor: bool = False
    goal: StrategicGoal = StrategicGoal.EXPAND
    aggression: float = 0.5
    loyalty: float = 0.5
    risk_preference: float = 0.5
    is_defeated: bool = False
    last_betrayal_round: int = -10
    last_move_capital_round: int = -100
    action_points: float = 6.0
    war_pressure: int = 0


class Relation(BaseModel):
    """国家间外交关系模型。

    每对国家最多一个Relation实例，通过sorted键确保唯一性。

    Attributes:
        country_a: 国家A名称
        country_b: 国家B名称
        trust: 信任度（0-1），影响同盟和外交决策
        grudge: 仇怨度（0-1），影响宣战和复仇倾向
        is_allied: 是否同盟
        alliance_round: 同盟形成回合，-1表示未同盟
        at_war: 是否处于交战状态
    """
    country_a: str
    country_b: str
    trust: float = 0.5
    grudge: float = 0.0
    is_allied: bool = False
    alliance_round: int = -1
    at_war: bool = False


class MemoryImpact(str, Enum):
    """记忆影响程度枚举。"""
    HIGH = "high"        # 高影响：如背叛、背刺
    MEDIUM = "medium"    # 中影响：如宣战、结盟
    LOW = "low"          # 低影响：如普通外交消息


class MemoryEmotion(str, Enum):
    """记忆情感类型枚举。"""
    ANGER = "anger"          # 愤怒：被攻击、被背叛
    FEAR = "fear"            # 恐惧：面临威胁
    GRATITUDE = "gratitude"  # 感恩：结盟、停战
    GRIEF = "grief"          # 悲伤：失去领土


class Memory(BaseModel):
    """外交记忆模型，记录国家间的历史事件。

    记忆用于AI决策时参考历史，影响对其他国家的态度。
    记忆会随时间衰减，强度低于0.2时被遗忘。

    Attributes:
        round: 事件发生回合
        event: 事件描述
        impact: 影响程度
        emotion: 情感类型
        target: 事件目标国家
        decay: 每回合衰减值，默认0.1
        current_value: 当前记忆强度，初始1.0，低于0.2被遗忘
    """
    round: int
    event: str
    impact: MemoryImpact
    emotion: MemoryEmotion
    target: str
    decay: float = 0.1
    current_value: float = 1.0


class GeneralTrait(str, Enum):
    """武将特性枚举，每位武将拥有独特的战场能力。

    特性效果在战斗系统中实现：
    - 攻击方特性：影响攻方战力
    - 防御方特性：影响守方战力（需驻守在防守区块）
    - 被动特性：影响阵亡概率等
    """
    WEI_ZHEN_XIAOYAOJIN = "wei_zhen_xiaoyaojin"  # 威震逍遥津（张辽）：守军>=500时防御+15%
    BA_SHI_DAN_YAN = "ba_shi_dan_yan"              # 拔矢啖睛（夏侯惇）：阵亡概率减半
    TIE_BI = "tie_bi"                              # 铁壁（曹仁）：预留特性
    WEI_ZHEN_HUAXIA = "wei_zhen_huaxia"            # 威震华夏（关羽）：攻击+12%
    WAN_REN_DI = "wan_ren_di"                      # 万人敌（张飞）：目标有守军时攻击+10%
    YI_SHEN_SHI_DAN = "yi_shen_shi_dan"            # 一身是胆（赵云）：预留特性
    HUO_SHAO_CHIBI = "huo_shao_chibi"              # 火烧赤壁（周瑜）：防御+10%
    HUO_SHAO_LIANYING = "huo_shao_lianying"        # 火烧连营（陆逊）：以少胜多时防御+20%
    JIN_FAN_TU_JI = "jin_fan_tu_ji"                # 锦帆突袭（甘宁）：攻击+8%


class General(BaseModel):
    """武将模型，代表三国时期的著名将领。

    武将驻守在特定区块，其特性会影响该区块的战斗结果。
    武将可能在战斗中阵亡。

    Attributes:
        name: 武将名称
        country: 所属国家
        block: 驻守区块名
        trait: 武将特性
        alive: 是否存活
        death_round: 阵亡回合，None表示存活
    """
    name: str
    country: str
    block: str
    trait: GeneralTrait
    alive: bool = True
    death_round: Optional[int] = None


class DiplomaticMessage(BaseModel):
    """外交消息模型，记录国家间的外交通信。

    消息内容通过关键词匹配识别外交意图（结盟、断交、招降等）。
    公开消息（visibility="public"）可用于同盟形成的双向确认。

    Attributes:
        id: 消息唯一ID
        from_country: 发送方国家名
        to_country: 接收方国家名
        content: 消息内容
        visibility: 可见性，"private"或"public"
        round: 发送回合
        timestamp: 发送时间戳
    """
    id: str
    from_country: str
    to_country: str
    content: str
    visibility: str = "private"
    round: int
    timestamp: datetime = Field(default_factory=datetime.now)


class BattleResult(BaseModel):
    """战斗结果模型，记录一次战斗的完整结果。

    由CombatSystem.resolve_attack()生成，包含双方损失、胜负判定、
    区块占领情况和崩溃信息。

    Attributes:
        attacker: 攻方国家名
        defender: 守方国家名
        attacker_block: 攻方出发区块名
        defender_block: 守方防守区块名
        attacker_troops: 攻方出兵数
        defender_troops: 守方守军数
        attacker_loss: 攻方损失
        defender_loss: 守方损失
        attacker_won: 攻方是否胜利
        block_captured: 区块是否被占领
        collapse: 守方是否崩溃
        war_pressure_change: 战争压力变化值
    """
    attacker: str
    defender: str
    attacker_block: str
    defender_block: str
    attacker_troops: int
    defender_troops: int
    attacker_loss: int
    defender_loss: int
    attacker_won: bool
    block_captured: bool
    collapse: bool = False
    war_pressure_change: int = 0


class ActionType(str, Enum):
    """行动类型枚举，定义所有可执行的游戏行动。"""
    MOVE = "move"                        # 调兵
    ATTACK = "attack"                    # 进攻
    HARASS = "harass"                    # 骚扰
    RECRUIT = "recruit"                  # 征兵
    DEVELOP = "develop"                  # 发展
    TAX = "tax"                          # 征税
    SEND_MESSAGE = "send_message"        # 外交消息
    DISBAND = "disband"                  # 裁军
    MOVE_CAPITAL = "move_capital"        # 迁都
    DECLARE_EMPEROR = "declare_emperor"  # 称帝


class Action(BaseModel):
    """行动指令模型，表示一个待执行的游戏行动。

    Attributes:
        action_type: 行动类型
        country: 执行国家名
        parameters: 行动参数字典，不同行动类型有不同参数
    """
    action_type: ActionType
    country: str
    parameters: dict = Field(default_factory=dict)


class Timeline(BaseModel):
    """时间线模型，管理游戏内的年月推进。

    初始为建安五年（200年）1月，每回合推进一个月。

    Attributes:
        year: 当前年份
        month: 当前月份（1-12）
    """
    year: int = 200
    month: int = 1

    def advance(self) -> None:
        """推进一个月，超过12月时年份+1。"""
        self.month += 1
        if self.month > 12:
            self.month = 1
            self.year += 1

    def to_string(self) -> str:
        """返回格式化的时间字符串，如"200年1月"。"""
        return f"{self.year}年{self.month}月"


class WinRateLabel(str, Enum):
    """胜率标签枚举，用于迷雾系统中的战斗胜率提示。"""
    HIGH = "high"        # 高胜率：战力比>=1.5
    MEDIUM = "medium"    # 中等胜率：1.0<=战力比<1.5
    LOW = "low"          # 低胜率：战力比<1.0
    UNKNOWN = "unknown"  # 未知：无相邻己方区块


class BlockVisibility(BaseModel):
    """区块可见性模型，描述某区块对特定观察者的可见程度。

    由迷雾系统计算，不同可见性层级提供不同精度的信息。

    Attributes:
        name: 区块名称
        owner: 所有者（可见时）
        garrison_estimate: 守军估算值（己方为精确值，敌方为估算值）
        order_range: 秩序范围区间（己方为精确值，敌方为范围）
        morale_range: 士气范围区间（己方为精确值，敌方为范围）
        base_manpower: 基础人力（仅己方和同盟可见）
        win_rate_label: 胜率标签（仅相邻敌方区块）
        visible: 是否可见
    """
    name: str
    owner: Optional[str] = None
    garrison_estimate: Optional[int] = None
    order_range: Optional[tuple[int, int]] = None
    morale_range: Optional[tuple[int, int]] = None
    base_manpower: Optional[int] = None
    win_rate_label: WinRateLabel = WinRateLabel.UNKNOWN
    visible: bool = False


class CountryMemory(BaseModel):
    """国家记忆容器模型，存储一个国家的所有外交记忆。

    记忆数量上限为5条，超出时保留最重要的。

    Attributes:
        country_name: 国家名称
        memories: 记忆列表
    """
    country_name: str
    memories: list[Memory] = Field(default_factory=list)


class GameState(BaseModel):
    """游戏状态模型，包含游戏运行时的全部数据。

    这是游戏状态的顶层容器，所有游戏逻辑都通过读写此对象来操作。
    GameState通过Pydantic自动支持JSON序列化/反序列化，用于存档系统。

    Attributes:
        round: 当前回合数
        timeline: 时间线对象
        countries: 国家字典，键为国家名
        blocks: 区块字典，键为区块名
        relations: 外交关系字典，键为排序后的国家对名
        country_memories: 国家记忆字典，键为国家名
        generals: 武将列表
        history: 历史事件列表
        diplomatic_messages: 外交消息列表
        defeated_nations: 已灭亡国家字典，键为国家名，值为灭亡回合
        historical_events_triggered: 已触发的历史事件字典
        battle_results_this_round: 本回合战斗结果列表
        action_log: 行动日志列表
        last_round_actions: 上回合各国家行动字典
        narratives: 编年史叙事列表
    """
    round: int = 1
    timeline: Timeline = Field(default_factory=Timeline)
    countries: dict[str, Country] = Field(default_factory=dict)
    blocks: dict[str, Block] = Field(default_factory=dict)
    relations: dict[str, Relation] = Field(default_factory=dict)
    country_memories: dict[str, CountryMemory] = Field(default_factory=dict)
    generals: list[General] = Field(default_factory=list)
    history: list[dict] = Field(default_factory=list)
    diplomatic_messages: list[DiplomaticMessage] = Field(default_factory=list)
    defeated_nations: dict[str, int] = Field(default_factory=dict)
    historical_events_triggered: dict[str, int] = Field(default_factory=dict)
    battle_results_this_round: list[BattleResult] = Field(default_factory=list)
    action_log: list[dict] = Field(default_factory=list)
    last_round_actions: dict[str, list[dict]] = Field(default_factory=dict)
    narratives: list[dict] = Field(default_factory=list)
