from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class RegionType(str, Enum):
    CORE = "core"
    FRONTIER = "frontier"


class GeographicTrait(str, Enum):
    FARMING = "farming"
    TRADE = "trade"
    FORTRESS = "fortress"
    NONE = "none"


class BlockSpecialization(str, Enum):
    FARMING = "farming"
    TRADE = "trade"
    FORTRESS = "fortress"


class Block(BaseModel):
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
    EXPAND = "expand"
    DEFEND = "defend"
    REVENGE = "revenge"
    STABILIZE = "stabilize"
    DECLARE_EMPEROR = "declare_emperor"


class Country(BaseModel):
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
    action_points: float = 6.0


class Relation(BaseModel):
    country_a: str
    country_b: str
    trust: float = 0.5
    grudge: float = 0.0
    is_allied: bool = False
    alliance_round: int = -1
    at_war: bool = False


class MemoryImpact(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MemoryEmotion(str, Enum):
    ANGER = "anger"
    FEAR = "fear"
    GRATITUDE = "gratitude"
    GRIEF = "grief"


class Memory(BaseModel):
    round: int
    event: str
    impact: MemoryImpact
    emotion: MemoryEmotion
    target: str
    decay: float = 0.1
    current_value: float = 1.0


class GeneralTrait(str, Enum):
    WEI_ZHEN_XIAOYAOJIN = "wei_zhen_xiaoyaojin"
    BA_SHI_DAN_YAN = "ba_shi_dan_yan"
    TIE_BI = "tie_bi"
    WEI_ZHEN_HUAXIA = "wei_zhen_huaxia"
    WAN_REN_DI = "wan_ren_di"
    YI_SHEN_SHI_DAN = "yi_shen_shi_dan"
    HUO_SHAO_CHIBI = "huo_shao_chibi"
    HUO_SHAO_LIANYING = "huo_shao_lianying"
    JIN_FAN_TU_JI = "jin_fan_tu_ji"


class General(BaseModel):
    name: str
    country: str
    block: str
    trait: GeneralTrait
    alive: bool = True
    death_round: Optional[int] = None


class DiplomaticMessage(BaseModel):
    id: str
    from_country: str
    to_country: str
    content: str
    visibility: str = "private"
    round: int
    timestamp: datetime = Field(default_factory=datetime.now)


class BattleResult(BaseModel):
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
    MOVE = "move"
    ATTACK = "attack"
    HARASS = "harass"
    RECRUIT = "recruit"
    DEVELOP = "develop"
    TAX = "tax"
    SEND_MESSAGE = "send_message"
    DISBAND = "disband"
    MOVE_CAPITAL = "move_capital"
    DECLARE_EMPEROR = "declare_emperor"


class Action(BaseModel):
    action_type: ActionType
    country: str
    parameters: dict = Field(default_factory=dict)


class Timeline(BaseModel):
    year: int = 200
    month: int = 1

    def advance(self) -> None:
        self.month += 1
        if self.month > 12:
            self.month = 1
            self.year += 1

    def to_string(self) -> str:
        return f"{self.year}年{self.month}月"


class WinRateLabel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class BlockVisibility(BaseModel):
    name: str
    owner: Optional[str] = None
    garrison_estimate: Optional[int] = None
    order_range: Optional[tuple[int, int]] = None
    morale_range: Optional[tuple[int, int]] = None
    base_manpower: Optional[int] = None
    win_rate_label: WinRateLabel = WinRateLabel.UNKNOWN
    visible: bool = False


class CountryMemory(BaseModel):
    country_name: str
    memories: list[Memory] = Field(default_factory=list)


class GameState(BaseModel):
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
