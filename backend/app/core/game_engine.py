"""
游戏引擎核心模块
处理游戏初始化、回合处理、状态更新等核心逻辑
"""
import json
import random
from pathlib import Path
from typing import Optional
from collections import deque

from ..models import (
    Block, Country, Relation, Memory, General, GameState,
    RegionType, GeographicTrait, StrategicGoal, MemoryImpact, MemoryEmotion,
    GeneralTrait, Timeline, CountryMemory, BattleResult,
)
from ..core.constants import (
    GAME_CONSTANTS, INITIAL_COUNTRIES, SPECIAL_NEUTRAL_FORCES,
    INITIAL_GENERALS, CORE_REGIONS, get_config,
)


class GameEngine:
    """
    游戏引擎主类
    管理游戏状态、初始化、回合处理等核心功能
    """
    
    def __init__(self):
        self.state: Optional[GameState] = None
        self.geojson_data: Optional[dict] = None

    def initialize_game(self, geojson_path: Optional[str] = None) -> GameState:
        """
        初始化游戏
        加载地图、创建区块、国家、外交关系、武将等
        """
        self.state = GameState()
        self._load_geojson(geojson_path)
        self._initialize_blocks()
        self._initialize_countries()
        self._initialize_relations()
        self._initialize_generals()
        return self.state

    def _load_geojson(self, geojson_path: Optional[str]) -> None:
        """加载GeoJSON地图数据"""
        if geojson_path is None:
            geojson_path = str(Path(__file__).parent.parent / "data" / "maps" / "three_kingdoms.geojson")
        
        try:
            with open(geojson_path, "r", encoding="utf-8") as f:
                self.geojson_data = json.load(f)
        except FileNotFoundError:
            # 如果找不到地图文件，创建空的FeatureCollection
            self.geojson_data = {"type": "FeatureCollection", "features": []}

    def _initialize_blocks(self) -> None:
        """
        初始化所有区块
        从GeoJSON数据创建区块对象，设置邻居关系
        """
        if not self.geojson_data:
            return

        for feature in self.geojson_data.get("features", []):
            name = feature.get("properties", {}).get("label", "未知")
            if not name:
                continue

            # 查找相邻区块
            neighbors = self._find_neighbors(feature)
            # 确定区块类型（核心/边境）
            region_type = self._determine_region_type(name)
            # 确定地理特性
            geographic_trait = self._determine_geographic_trait(name, feature)
            
            block = Block(
                name=name,
                neighbors=neighbors,
                base_manpower=random.randint(600, 1200),
                manpower_pool=random.randint(600, 1200),
                owner="neutral",
                garrison=random.randint(0, 200),
                order=random.randint(40, 60),
                morale=50,
                region_type=region_type,
                geographic_trait=geographic_trait,
            )
            self.state.blocks[name] = block

        # 分配初始所有者
        self._assign_initial_owners()
        # 建立双向邻居关系
        self._build_neighbor_relations()

    def _find_neighbors(self, feature: dict) -> list[str]:
        """
        查找相邻区块
        通过共享边界点判断相邻关系
        """
        neighbors = []
        all_coords = self._extract_coords(feature)

        for other in self.geojson_data.get("features", []):
            other_name = other.get("properties", {}).get("label", "")
            if not other_name or other_name == feature.get("properties", {}).get("label"):
                continue
            other_coords = self._extract_coords(other)
            # 如果两个区块有共享的边界点，则相邻
            if all_coords & other_coords:
                neighbors.append(other_name)
        return neighbors

    def _extract_coords(self, feature: dict) -> set[tuple[float, float]]:
        """
        从GeoJSON特征中提取所有坐标点
        用于判断相邻关系
        """
        coords_set = set()
        geometry = feature.get("geometry", {})
        if not geometry:
            return coords_set
        coord_data = geometry.get("coordinates", [])
        if not coord_data:
            return coords_set

        def _walk(obj):
            """递归遍历坐标数据结构"""
            if isinstance(obj, (list, tuple)) and len(obj) > 0:
                if isinstance(obj[0], (list, tuple)):
                    for item in obj:
                        _walk(item)
                else:
                    if len(obj) >= 2 and isinstance(obj[0], (int, float)) and isinstance(obj[1], (int, float)):
                        coords_set.add((round(obj[0], 4), round(obj[1], 4)))

        _walk(coord_data)
        return coords_set

    def _determine_region_type(self, name: str) -> RegionType:
        """根据区块名称确定区块类型（核心/边境）"""
        for region, blocks in CORE_REGIONS.items():
            if name in blocks:
                if region.endswith("_frontier"):
                    return RegionType.FRONTIER
                return RegionType.CORE
        return RegionType.FRONTIER

    def _determine_geographic_trait(self, name: str, feature: dict) -> GeographicTrait:
        """确定区块的地理特性（要塞/农业/贸易等）"""
        SPECIAL_TRAITS = {
            "洛阳": GeographicTrait.FORTRESS,
            "武阳": GeographicTrait.FARMING,
            "新都": GeographicTrait.TRADE,
        }
        if name in SPECIAL_TRAITS:
            return SPECIAL_TRAITS[name]
        return GeographicTrait.NONE

    def _assign_initial_owners(self) -> None:
        """分配初始区块所有者"""
        # 分配主要国家
        for country_name, data in INITIAL_COUNTRIES.items():
            for block_name in data["blocks"]:
                if block_name in self.state.blocks:
                    block = self.state.blocks[block_name]
                    block.owner = country_name
                    block.garrison = random.randint(400, 800)
                    block.order = data["order"]
                    block.morale = data["morale"]
                    block.region_type = RegionType.CORE

        # 分配特殊中立势力
        for force_name, data in SPECIAL_NEUTRAL_FORCES.items():
            for block_name in data["blocks"]:
                if block_name in self.state.blocks:
                    block = self.state.blocks[block_name]
                    block.owner = force_name
                    block.garrison = random.randint(200, 400)
                    block.order = random.randint(50, 70)
                    block.morale = 60

    def _build_neighbor_relations(self) -> None:
        """建立双向邻居关系"""
        for name, block in self.state.blocks.items():
            for neighbor_name in block.neighbors:
                if neighbor_name in self.state.blocks:
                    neighbor = self.state.blocks[neighbor_name]
                    if name not in neighbor.neighbors:
                        neighbor.neighbors.append(name)

    def _initialize_countries(self) -> None:
        """初始化所有国家"""
        # 初始化主要国家
        for country_name, data in INITIAL_COUNTRIES.items():
            country_config = get_config(f"country_settings.{country_name}", {})
            country = Country(
                name=country_name,
                gold=country_config.get("initial_gold", data["gold"]),
                order=country_config.get("initial_order", data["order"]),
                morale=country_config.get("initial_morale", data["morale"]),
                capital=country_config.get("capital", data["capital"]),
                aggression=data["aggression"],
                loyalty=data["loyalty"],
                risk_preference=data["risk_preference"],
            )
            self.state.countries[country_name] = country
            self.state.country_memories[country_name] = CountryMemory(country_name=country_name)

        # 初始化特殊中立势力
        for force_name, data in SPECIAL_NEUTRAL_FORCES.items():
            country = Country(
                name=force_name,
                gold=random.randint(500, 1000),
                order=random.randint(50, 70),
                morale=60,
                capital=data["capital"],
                aggression=0.2,
                loyalty=0.8,
                risk_preference=0.3,
            )
            self.state.countries[force_name] = country
            self.state.country_memories[force_name] = CountryMemory(country_name=force_name)

    def _initialize_relations(self) -> None:
        """初始化国家间外交关系"""
        major_countries = list(INITIAL_COUNTRIES.keys())
        for i, country_a in enumerate(major_countries):
            for country_b in major_countries[i + 1:]:
                key = f"{country_a}-{country_b}"
                self.state.relations[key] = Relation(
                    country_a=country_a,
                    country_b=country_b,
                    trust=0.5,
                    grudge=0.0,
                )

    def _initialize_generals(self) -> None:
        """初始化武将"""
        for gen_data in INITIAL_GENERALS:
            general = General(
                name=gen_data["name"],
                country=gen_data["country"],
                block=gen_data["block"],
                trait=GeneralTrait(gen_data["trait"]),
            )
            self.state.generals.append(general)

    def process_round(self) -> dict:
        """
        处理回合结束
        执行人力恢复、秩序恢复、补给线更新、战略目标更新等
        """
        if not self.state:
            return {"error": "Game not initialized"}

        results = {
            "round": self.state.round,
            "events": [],
            "battle_results": [],
            "diplomatic_events": [],
        }

        # 各项回合处理
        self._manpower_recovery()
        self._order_morale_recovery()
        self._update_supply_lines()
        self._update_strategic_goals()
        self._clear_newly_conquered()
        self._check_capital_events()
        self._check_defeat()
        self._check_historical_events()
        self._check_fatigue()
        self._reset_action_points()

        # 推进回合
        self.state.round += 1
        self.state.timeline.advance()

        return results

    def _manpower_recovery(self) -> None:
        """人力池恢复"""
        recovery_rate = GAME_CONSTANTS["MANPOWER_RECOVERY_RATE"]
        for block in self.state.blocks.values():
            if block.owner != "neutral":
                recovery = int(block.base_manpower * recovery_rate)
                block.manpower_pool = min(
                    block.manpower_pool + recovery,
                    block.base_manpower
                )

    def _order_morale_recovery(self) -> None:
        """秩序和士气恢复"""
        for block in self.state.blocks.values():
            if block.owner != "neutral" and not block.recently_conquered:
                if block.order < 100:
                    block.order = min(100, block.order + 5)
                if block.morale < 100:
                    block.morale = min(100, block.morale + 5)

    def _update_supply_lines(self) -> None:
        """
        更新补给线
        检查每个区块是否与首都连通
        """
        for country_name, country in self.state.countries.items():
            if country.is_defeated or not country.capital:
                continue
            
            capital = self.state.blocks.get(country.capital)
            if not capital or capital.owner != country_name:
                continue

            # BFS查找与首都连通的所有区块
            connected = self._find_connected_blocks(country_name, country.capital)
            for block_name, block in self.state.blocks.items():
                if block.owner == country_name:
                    block.supply_connected = block_name in connected

    def _find_connected_blocks(self, country_name: str, start_block: str) -> set[str]:
        """BFS查找与起始区块连通的所有己方区块"""
        connected = set()
        queue = deque([start_block])
        visited = set()

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            block = self.state.blocks.get(current)
            if not block or block.owner != country_name:
                continue

            connected.add(current)
            for neighbor in block.neighbors:
                if neighbor not in visited:
                    queue.append(neighbor)

        return connected

    def _update_strategic_goals(self) -> None:
        """更新各国的战略目标"""
        for country_name, country in self.state.countries.items():
            if country.is_defeated:
                continue

            blocks_count = sum(1 for b in self.state.blocks.values() if b.owner == country_name)
            
            # 根据情况选择战略目标
            if country.order < 40 or self._count_low_order_blocks(country_name) > 2:
                country.goal = StrategicGoal.STABILIZE
            elif self._has_high_grudge(country_name):
                country.goal = StrategicGoal.REVENGE
            elif blocks_count >= GAME_CONSTANTS["EMPEROR_REQUIRED_BLOCKS"]:
                if self._controls_historical_capital(country_name):
                    country.goal = StrategicGoal.DECLARE_EMPEROR
                else:
                    country.goal = StrategicGoal.EXPAND
            else:
                country.goal = StrategicGoal.EXPAND

    def _count_low_order_blocks(self, country_name: str) -> int:
        """统计低秩序区块数量"""
        return sum(
            1 for b in self.state.blocks.values()
            if b.owner == country_name and b.order < 30
        )

    def _has_high_grudge(self, country_name: str) -> bool:
        """检查是否有高仇怨关系"""
        for key, relation in self.state.relations.items():
            if country_name in (relation.country_a, relation.country_b):
                if relation.grudge >= 0.6:
                    return True
        return False

    def _controls_historical_capital(self, country_name: str) -> bool:
        """检查是否控制历史首都"""
        historical_capitals = ["长安", "洛阳", "许昌", "成都", "建业", "武昌"]
        return any(
            self.state.blocks.get(cap) and self.state.blocks[cap].owner == country_name
            for cap in historical_capitals
        )

    def _clear_newly_conquered(self) -> None:
        """清除新占领标记"""
        for block in self.state.blocks.values():
            block.recently_conquered = False

    def _check_capital_events(self) -> None:
        """检查首都事件（首都沦陷等）"""
        for country_name, country in self.state.countries.items():
            if country.is_defeated:
                continue

            capital_block = self.state.blocks.get(country.capital)
            if capital_block and capital_block.owner != country_name:
                self._handle_capital_fallen(country_name)

    def _handle_capital_fallen(self, country_name: str) -> None:
        """处理首都沦陷"""
        country = self.state.countries.get(country_name)
        if not country:
            return

        # 进入流亡状态
        country.in_exile = True
        country.former_capital = country.capital
        country.exile_rounds = 12
        country.order = max(0, country.order - 15)
        country.morale = max(0, country.morale - 10)

        # 寻找新首都
        new_capital = self._find_new_capital(country_name)
        if new_capital:
            country.capital = new_capital

        self.state.history.append({
            "round": self.state.round,
            "event": "capital_fallen",
            "country": country_name,
            "new_capital": new_capital,
        })

    def _find_new_capital(self, country_name: str) -> Optional[str]:
        """寻找新首都（选择秩序、士气、兵力最高的区块）"""
        best_block = None
        best_score = -1

        for block_name, block in self.state.blocks.items():
            if block.owner != country_name:
                continue
            if block.recently_conquered or not block.supply_connected:
                continue

            # 综合评分
            score = block.order + block.morale + block.garrison / 10
            if score > best_score:
                best_score = score
                best_block = block_name

        return best_block

    def _check_defeat(self) -> None:
        """检查国家是否灭亡"""
        for country_name, country in self.state.countries.items():
            if country.is_defeated:
                continue

            blocks_count = sum(1 for b in self.state.blocks.values() if b.owner == country_name)
            if blocks_count == 0:
                country.is_defeated = True
                self.state.defeated_nations[country_name] = self.state.round
                self.state.history.append({
                    "round": self.state.round,
                    "event": "nation_defeated",
                    "country": country_name,
                })

    def _check_historical_events(self) -> None:
        """检查历史事件（预留接口）"""
        pass

    def _trigger_historical_event(self, event_id: str, event: dict) -> None:
        """触发历史事件"""
        self.state.historical_events_triggered[event_id] = self.state.round
        self.state.history.append({
            "round": self.state.round,
            "event": "historical",
            "name": event["name"],
        })

    def _check_fatigue(self) -> None:
        """
        检查战争疲劳
        游戏后期随机降低秩序和士气
        """
        if self.state.round < GAME_CONSTANTS["FATIGUE_START_ROUND"]:
            return

        if random.randint(
            GAME_CONSTANTS["FATIGUE_INTERVAL_MIN"],
            GAME_CONSTANTS["FATIGUE_INTERVAL_MAX"]
        ) == GAME_CONSTANTS["FATIGUE_INTERVAL_MIN"]:
            for block in self.state.blocks.values():
                if block.owner != "neutral":
                    block.order = max(0, block.order - 1)
                    block.morale = max(0, block.morale - 1)

    def _reset_action_points(self) -> None:
        """重置行动点数"""
        ap = get_config("game_settings.initial_action_points", 6.0)
        for country in self.state.countries.values():
            if not country.is_defeated:
                country.action_points = ap

    def get_state(self) -> GameState:
        """获取游戏状态"""
        return self.state

    def get_block(self, name: str) -> Optional[Block]:
        """获取指定区块"""
        return self.state.blocks.get(name) if self.state else None

    def get_country(self, name: str) -> Optional[Country]:
        """获取指定国家"""
        return self.state.countries.get(name) if self.state else None
