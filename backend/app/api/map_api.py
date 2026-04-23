from fastapi import APIRouter
from pathlib import Path
import json

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/geojson")
def get_geojson():
    geojson_path = Path(__file__).parent.parent / "data" / "maps" / "three_kingdoms.geojson"
    if not geojson_path.exists():
        docs_path = Path(__file__).parent.parent.parent.parent / "docs" / "three_kingdoms.geojson"
        if docs_path.exists():
            with open(docs_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"type": "FeatureCollection", "features": []}

    with open(geojson_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/blocks-summary")
def get_blocks_summary():
    from ..core import GameEngine
    from ..api.game import engine

    if not engine.state:
        return {"error": "Game not initialized"}

    state = engine.state
    features = []
    for name, block in state.blocks.items():
        features.append({
            "type": "Feature",
            "properties": {
                "label": name,
                "owner": block.owner,
                "garrison": block.garrison,
                "order": block.order,
                "morale": block.morale,
                "region_type": block.region_type.value,
                "supply_connected": block.supply_connected,
            },
        })

    return {"type": "FeatureCollection", "features": features}
