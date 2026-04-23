import random
from typing import Optional
from ..models import GameState, Block, MemoryImpact, MemoryEmotion


class EventsSystem:
    def __init__(self, state: GameState):
        self.state = state

    def check_borderland_events(self) -> list[dict]:
        events = []
        events.extend(self._check_nanzhong_rebellion())
        events.extend(self._check_liaodong_event())
        events.extend(self._check_liangzhou_disturbance())
        return events

    def _check_nanzhong_rebellion(self) -> list[dict]:
        events = []
        nanzhong_blocks = ["永昌", "建宁", "云南", "兴古", "且兰", "万宁", "朱提", "邛都", "会无", "堂狼", "昆明", "定苲"]

        for block_name in nanzhong_blocks:
            block = self.state.blocks.get(block_name)
            if not block:
                continue
            if block.owner == "南中" or block.owner == "neutral":
                continue

            if block.order < 40 and block.region_type.value == "frontier":
                if random.random() < 0.2:
                    event = self._trigger_nanzhong_rebellion(block)
                    events.append(event)

        return events

    def _trigger_nanzhong_rebellion(self, block: Block) -> dict:
        original_owner = block.owner
        original_garrison = block.garrison

        block.owner = "南中"
        block.garrison = int(original_garrison * random.uniform(0.3, 0.5))
        block.order = 40
        block.morale = 70

        country = self.state.countries.get(original_owner)
        if country:
            country.order = max(0, country.order - 5)

        for neighbor_name in block.neighbors:
            neighbor = self.state.blocks.get(neighbor_name)
            if neighbor and neighbor.owner == original_owner:
                neighbor.order = max(0, neighbor.order - 2)

        self._add_memory(original_owner, f"南中叛乱：{block.name}", MemoryImpact.HIGH, MemoryEmotion.FEAR, "南中")

        return {
            "type": "nanzhong_rebellion",
            "block": block.name,
            "original_owner": original_owner,
            "message": f"南中叛乱！{block.name}蛮部作乱，{original_owner}守军溃散！",
        }

    def _check_liaodong_event(self) -> list[dict]:
        events = []
        gongsun_blocks = ["襄平", "新昌", "玄菟", "扶余南", "扶余北", "黑山南", "黑山北", "界鲜卑"]

        for block_name in gongsun_blocks:
            block = self.state.blocks.get(block_name)
            if not block:
                continue
            if block.owner == "公孙度":
                if block.recently_conquered:
                    if block_name == "襄平":
                        events.append({
                            "type": "liaodong_conquered",
                            "conqueror": block.owner,
                            "message": f"{block.owner}征服辽东，北境安宁！",
                        })
                        break

        return events

    def _check_liangzhou_disturbance(self) -> list[dict]:
        events = []
        liangzhou_blocks = ["金城", "西都", "姑臧", "酒泉东", "酒泉西", "敦煌"]

        for block_name in liangzhou_blocks:
            block = self.state.blocks.get(block_name)
            if not block:
                continue
            if block.owner == "凉州" or block.owner == "neutral":
                continue

            if block.order < 30:
                for neighbor_name in block.neighbors:
                    neighbor = self.state.blocks.get(neighbor_name)
                    if neighbor and neighbor.owner == block.owner:
                        loss = int(neighbor.garrison * 0.1)
                        neighbor.garrison = max(0, neighbor.garrison - loss)
                        neighbor.order = max(0, neighbor.order - 2)

                events.append({
                    "type": "liangzhou_disturbance",
                    "block": block.name,
                    "owner": block.owner,
                    "message": f"凉州羌胡扰动，{block.owner}边境不安！",
                })

        return events

    def check_historical_events(self) -> list[dict]:
        events = []
        year = self.state.timeline.year
        month = self.state.timeline.month

        historical_events = [
            {
                "id": "guandu",
                "name": "官渡之战",
                "trigger": (200, 10),
                "country": "魏",
                "effects": {"morale": 10, "gold": 500},
            },
            {
                "id": "sun_ce_death",
                "name": "孙策遇刺",
                "trigger": (200, 4),
                "country": "吴",
                "effects": {"order": -8, "morale": -5},
            },
            {
                "id": "chibi",
                "name": "赤壁之战",
                "trigger": (208, 11),
                "country": "魏",
                "effects": {},
            },
            {
                "id": "yiling",
                "name": "夷陵之战",
                "trigger": (221, 7),
                "country": "蜀",
                "effects": {},
            },
        ]

        for event in historical_events:
            if event["id"] in self.state.historical_events_triggered:
                continue

            trigger_year, trigger_month = event["trigger"]
            if year == trigger_year and month == trigger_month:
                country = self.state.countries.get(event["country"])
                if country and not country.is_defeated:
                    self.state.historical_events_triggered[event["id"]] = self.state.round

                    for key, value in event["effects"].items():
                        if key == "morale":
                            country.morale = max(0, min(100, country.morale + value))
                        elif key == "order":
                            country.order = max(0, min(100, country.order + value))
                        elif key == "gold":
                            country.gold += value

                    events.append({
                        "type": "historical",
                        "name": event["name"],
                        "country": event["country"],
                        "message": f"历史事件：{event['name']}",
                    })

        return events

    def _add_memory(self, country_name: str, event: str, impact: MemoryImpact, emotion: MemoryEmotion, target: str):
        from ..models import Memory
        cm = self.state.country_memories.get(country_name)
        if cm:
            memory = Memory(
                round=self.state.round,
                event=event,
                impact=impact,
                emotion=emotion,
                target=target,
            )
            cm.memories.append(memory)
