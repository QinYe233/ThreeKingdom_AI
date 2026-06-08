"""
游戏引擎核心模块

处理游戏初始化、回合处理、状态更新等核心逻辑。
游戏引擎是整个游戏状态的管理者，负责从地图数据创建游戏世界、
维护国家/区块/外交关系/武将等核心数据，以及每回合的状态更新。

主要功能：
- 游戏初始化：加载地图GeoJSON、创建区块、国家、外交关系、武将
- 回合处理：人力恢复、秩序恢复、补给线更新、首都沦陷检查、国家灭亡检查
- 补给线计算：基于BFS算法检查区块与首都的连通性
- 战略目标更新：根据国家状况自动调整战略目标
- 战争疲劳：游戏后期随机降低秩序和士气
"""
import json
import random
from pathlib import Path
from typing import Optional
from collections import deque

from ..models import (
    Block, Country, Relation, General, GameState,
    RegionType, GeographicTrait, StrategicGoal,
    GeneralTrait, CountryMemory,
)
from ..core.constants import (
    GAME_CONSTANTS, INITIAL_COUNTRIES, SPECIAL_NEUTRAL_FORCES,
    INITIAL_GENERALS, CORE_REGIONS, get_config, HISTORICAL_CAPITALS,
)


class GameEngine:
    """
    游戏引擎主类

    管理游戏状态、初始化、回合处理等核心功能。
    是游戏状态的唯一管理者，所有对游戏状态的修改都应通过游戏引擎进行。

    Attributes:
        state: 当前游戏状态对象，包含所有区块、国家、关系等数据
        geojson_data: 原始GeoJSON地图数据，用于初始化区块
    """

    def __init__(self):
        """初始化游戏引擎，状态和地图数据初始为空。"""
        self.state: Optional[GameState] = None
        self.geojson_data: Optional[dict] = None

    def initialize_game(self, geojson_path: Optional[str] = None) -> GameState:
        """
        初始化游戏

        按顺序执行以下初始化步骤：
        1. 创建空的GameState
        2. 加载GeoJSON地图数据
        3. 从地图数据创建区块对象
        4. 初始化国家（魏/蜀/吴/中立势力）
        5. 初始化国家间外交关系
        6. 初始化武将

        Args:
            geojson_path: GeoJSON地图文件路径，为None时使用默认路径

        Returns:
            初始化完成后的GameState对象
        """
        self.state = GameState()
        self._load_geojson(geojson_path)
        self._initialize_blocks()
        self._initialize_countries()
        self._initialize_relations()
        self._initialize_generals()
        return self.state

    def _load_geojson(self, geojson_path: Optional[str]) -> None:
        """加载GeoJSON地图数据。

        从指定路径加载地图的GeoJSON数据，包含所有区块的地理边界信息。
        如果文件不存在，创建空的FeatureCollection以允许无地图运行。

        Args:
            geojson_path: GeoJSON文件路径，为None时使用默认路径
                （backend/data/maps/three_kingdoms.geojson）
        """
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

        从GeoJSON数据创建区块对象，为每个区块设置：
        - 邻居关系（通过共享边界点判断）
        - 区块类型（核心/边境）
        - 地理特性（要塞/农业/贸易）
        - 初始属性（人力、守军、秩序等随机值）

        初始化后执行：
        - 分配初始所有者（主要国家和中立势力）
        - 建立双向邻居关系
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
                # 初始人力和人力池随机生成（600-1200）
                base_manpower=random.randint(600, 1200),
                manpower_pool=random.randint(600, 1200),
                owner="neutral",
                # 中立区块初始守军较少
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

        通过共享边界点判断相邻关系。两个区块如果有坐标点
        （精度为小数点后4位）完全相同，则判定为相邻。

        Args:
            feature: GeoJSON特征对象

        Returns:
            相邻区块名称列表
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

        递归遍历GeoJSON的coordinates数据结构（可能是多层嵌套数组），
        提取所有坐标点并四舍五入到小数点后4位，用于判断相邻关系。

        Args:
            feature: GeoJSON特征对象

        Returns:
            坐标点集合，每个坐标为(round(lon, 4), round(lat, 4))的元组
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
        """根据区块名称确定区块类型（核心/边境）。

        通过CORE_REGIONS常量查找区块所属区域，
        区域名以"_frontier"结尾的为边境区块，其余为核心区块。
        未在CORE_REGIONS中定义的区块默认为边境。

        Args:
            name: 区块名称

        Returns:
            RegionType.CORE 或 RegionType.FRONTIER
        """
        for region, blocks in CORE_REGIONS.items():
            if name in blocks:
                if region.endswith("_frontier"):
                    return RegionType.FRONTIER
                return RegionType.CORE
        return RegionType.FRONTIER

    def _determine_geographic_trait(self, name: str, feature: dict) -> GeographicTrait:
        """确定区块的地理特性（要塞/农业/贸易等）。

        目前仅对少数特殊区块硬编码了地理特性：
        - 洛阳：要塞（古都，易守难攻）
        - 武阳：农业（天府之国的粮仓）
        - 新都：贸易（商业重镇）

        其余区块默认为无特殊地理特性。

        Args:
            name: 区块名称
            feature: GeoJSON特征对象（预留，未来可从属性中读取）

        Returns:
            GeographicTrait枚举值
        """
        SPECIAL_TRAITS = {
            "洛阳": GeographicTrait.FORTRESS,
            "武阳": GeographicTrait.FARMING,
            "新都": GeographicTrait.TRADE,
        }
        if name in SPECIAL_TRAITS:
            return SPECIAL_TRAITS[name]
        return GeographicTrait.NONE

    def _assign_initial_owners(self) -> None:
        """分配初始区块所有者。

        分两个阶段：
        1. 分配主要国家（魏/蜀/吴）的初始区块，设置较高的守军和秩序
        2. 分配特殊中立势力（公孙度/士燮/南中/山越/凉州）的区块
        """
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
        """建立双向邻居关系。

        GeoJSON中的邻居关系可能是单向的（A的邻居列表中有B，但B中没有A），
        此方法确保所有邻居关系都是双向的。
        """
        for name, block in self.state.blocks.items():
            for neighbor_name in block.neighbors:
                if neighbor_name in self.state.blocks:
                    neighbor = self.state.blocks[neighbor_name]
                    if name not in neighbor.neighbors:
                        neighbor.neighbors.append(name)

    def _initialize_countries(self) -> None:
        """初始化所有国家。

        分两个阶段：
        1. 初始化主要国家（魏/蜀/吴），从INITIAL_COUNTRIES读取配置，
           支持通过game_config.json覆盖默认值
        2. 初始化特殊中立势力，使用固定参数（低侵略性、高忠诚度）
        """
        # 初始化主要国家
        for country_name, data in INITIAL_COUNTRIES.items():
            # 优先使用game_config.json中的配置，未配置的使用默认值
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
                # 中立势力不主动进攻，但忠诚度高（不易被策反）
                aggression=0.2,
                loyalty=0.8,
                risk_preference=0.3,
            )
            self.state.countries[force_name] = country
            self.state.country_memories[force_name] = CountryMemory(country_name=force_name)

    def _initialize_relations(self) -> None:
        """初始化国家间外交关系。

        仅为三个主要国家（魏/蜀/吴）之间创建初始关系，
        初始信任度为0.5（中性），无仇怨。
        与中立势力的关系在需要时动态创建。
        """
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
        """初始化武将。

        从INITIAL_GENERALS常量读取武将配置，创建武将对象。
        每个武将拥有名称、所属国家、驻守区块和特性。
        """
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

        按顺序执行以下回合处理步骤：
        1. 人力恢复：非中立区块的人力池恢复
        2. 秩序士气恢复：非新占领区块的秩序和士气恢复
        3. 补给线更新：检查各区块与首都的连通性
        4. 清除新占领标记
        5. 首都沦陷检查：首都被占则进入流亡状态
        6. 国家灭亡检查：无区块则灭亡
        7. 历史事件检查（预留接口）
        8. 战争疲劳检查：游戏后期随机降低秩序士气
        9. 重置行动点和战争压力

        Returns:
            包含round/events/battle_results/diplomatic_events的字典
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
        self._clear_newly_conquered()
        self._check_capital_events()
        self._check_defeat()
        self._check_historical_events()
        self._check_fatigue()
        self._reset_action_points()

        # 推进回合和时间线
        self.state.round += 1
        self.state.timeline.advance()

        return results

    def _manpower_recovery(self) -> None:
        """人力池恢复。

        每回合非中立区块的人力池恢复基础人力的12%（MANPOWER_RECOVERY_RATE），
        但不超过基础人力上限。
        """
        recovery_rate = GAME_CONSTANTS["MANPOWER_RECOVERY_RATE"]
        for block in self.state.blocks.values():
            if block.owner != "neutral":
                recovery = int(block.base_manpower * recovery_rate)
                block.manpower_pool = min(
                    block.manpower_pool + recovery,
                    block.base_manpower
                )

    def _order_morale_recovery(self) -> None:
        """秩序和士气恢复。

        每回合非新占领区块的秩序和士气各恢复5点，上限100。
        新占领区块不恢复（民心未附）。
        """
        for block in self.state.blocks.values():
            if block.owner != "neutral" and not block.recently_conquered:
                if block.order < 100:
                    block.order = min(100, block.order + 5)
                if block.morale < 100:
                    block.morale = min(100, block.morale + 5)

    def _update_supply_lines(self) -> None:
        """
        更新补给线

        检查每个区块是否与首都连通。补给线影响：
        - 攻方战力：断连区块攻方战力×0.85
        - 守方战力：断连区块守方战力×0.9
        - 发展/专精：飞地无法发展

        使用BFS算法从首都出发，沿己方区块的邻居关系搜索连通区域。
        """
        for country_name, country in self.state.countries.items():
            if country.is_defeated or not country.capital:
                continue

            capital = self.state.blocks.get(country.capital)
            # 首都被占则无法建立补给线
            if not capital or capital.owner != country_name:
                continue

            # BFS查找与首都连通的所有区块
            connected = self._find_connected_blocks(country_name, country.capital)
            for block_name, block in self.state.blocks.items():
                if block.owner == country_name:
                    block.supply_connected = block_name in connected

    def _find_connected_blocks(self, country_name: str, start_block: str) -> set[str]:
        """BFS查找与起始区块连通的所有己方区块。

        从起始区块出发，沿邻居关系广度优先搜索，
        只经过属于同一国家的区块，找出所有连通的己方区块。

        Args:
            country_name: 国家名
            start_block: 起始区块名（通常为首都）

        Returns:
            与起始区块连通的己方区块名称集合
        """
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
        """更新各国的战略目标。

        根据国家当前状况自动选择战略目标，优先级从高到低：
        1. STABILIZE（稳定）：秩序<40或低秩序区块>2个
        2. REVENGE（复仇）：存在仇怨>=0.6的外交关系
        3. DECLARE_EMPEROR（称帝）：控制>=45个区块且拥有历史首都
        4. EXPAND（扩张）：控制>=45个区块但无历史首都，或默认目标
        """
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
        """统计低秩序区块数量（秩序<30）。

        Args:
            country_name: 国家名

        Returns:
            低秩序区块数量
        """
        return sum(
            1 for b in self.state.blocks.values()
            if b.owner == country_name and b.order < 30
        )

    def _has_high_grudge(self, country_name: str) -> bool:
        """检查是否有高仇怨关系（仇怨>=0.6）。

        Args:
            country_name: 国家名

        Returns:
            存在高仇怨关系返回True
        """
        for key, relation in self.state.relations.items():
            if country_name in (relation.country_a, relation.country_b):
                if relation.grudge >= 0.6:
                    return True
        return False

    def _controls_historical_capital(self, country_name: str) -> bool:
        """检查是否控制本国历史首都。

        每个国家有1-2个历史首都（如魏的许昌和洛阳），
        控制任一即可满足称帝条件之一。

        Args:
            country_name: 国家名

        Returns:
            控制至少一个历史首都返回True
        """
        historical_capitals = HISTORICAL_CAPITALS.get(country_name, [])
        return any(
            self.state.blocks.get(cap) and self.state.blocks[cap].owner == country_name
            for cap in historical_capitals
        )

    def _clear_newly_conquered(self) -> None:
        """清除新占领标记。

        新占领标记(recently_conquered)用于限制新占领区块的征兵和发展，
        每回合结束时清除，表示占领已稳定。
        """
        for block in self.state.blocks.values():
            block.recently_conquered = False

    def _check_capital_events(self) -> None:
        """检查首都事件（首都沦陷等）。

        遍历所有国家，如果首都区块的所有者不是该国，
        触发首都沦陷处理。
        """
        for country_name, country in self.state.countries.items():
            if country.is_defeated:
                continue

            capital_block = self.state.blocks.get(country.capital)
            if capital_block and capital_block.owner != country_name:
                self._handle_capital_fallen(country_name)

    def _handle_capital_fallen(self, country_name: str) -> None:
        """处理首都沦陷。

        首都沦陷效果：
        - 进入流亡状态（in_exile=True）
        - 记录原首都（former_capital）
        - 流亡持续12回合（exile_rounds=12）
        - 秩序-15，士气-10
        - 自动选择新首都（秩序/士气/守军综合评分最高的己方区块）
        - 记录历史事件

        Args:
            country_name: 首都沦陷的国家名
        """
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
        """寻找新首都（选择秩序、士气、兵力最高的区块）。

        候选条件：
        - 属于本国
        - 非新占领
        - 与首都补给连通

        评分公式：score = 秩序 + 士气 + 守军/10

        Args:
            country_name: 国家名

        Returns:
            最佳候选区块名，无候选时返回None
        """
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
        """检查国家是否灭亡。

        当国家不再拥有任何区块时，标记为已灭亡，
        记录灭亡回合和历史事件。
        """
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
        """检查历史事件（预留接口）。

        未来可用于实现基于回合数的脚本化历史事件，
        如黄巾之乱、赤壁之战等。
        """
        pass

    def _trigger_historical_event(self, event_id: str, event: dict) -> None:
        """触发历史事件。

        记录历史事件的触发回合和事件名称。

        Args:
            event_id: 事件唯一标识
            event: 事件数据，需包含"name"字段
        """
        self.state.historical_events_triggered[event_id] = self.state.round
        self.state.history.append({
            "round": self.state.round,
            "event": "historical",
            "name": event["name"],
        })

    def _check_fatigue(self) -> None:
        """
        检查战争疲劳

        游戏后期（回合>=400）随机降低所有非中立区块的秩序和士气各1点。
        触发概率为 1/(FATIGUE_INTERVAL_MAX - FATIGUE_INTERVAL_MIN + 1)，
        约每3-4回合触发一次，模拟长期战争对社会的消耗。
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
        """重置行动点数和战争压力。

        每回合开始时，所有未灭亡国家的行动点恢复为默认值（6.0），
        战争压力清零。行动点以毫点为单位（6000毫点=6.0行动点）。
        """
        ap = get_config("game_settings.initial_action_points", 6.0)
        for country in self.state.countries.values():
            if not country.is_defeated:
                country.action_points = ap
                country.war_pressure = 0

    def get_state(self) -> GameState:
        """获取游戏状态

        Returns:
            当前GameState对象
        """
        return self.state

    def get_block(self, name: str) -> Optional[Block]:
        """获取指定区块

        Args:
            name: 区块名称

        Returns:
            Block对象，不存在时返回None
        """
        return self.state.blocks.get(name) if self.state else None

    def get_country(self, name: str) -> Optional[Country]:
        """获取指定国家

        Args:
            name: 国家名称

        Returns:
            Country对象，不存在时返回None
        """
        return self.state.countries.get(name) if self.state else None
