from .game import router as game_router
from .map_api import router as map_router
from .ai_api import router as ai_router
from .save_api import router as save_router

__all__ = ["game_router", "map_router", "ai_router", "save_router"]
