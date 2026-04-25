from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import game_router, map_router, ai_router, save_router

app = FastAPI(
    title="AI三国演义 API",
    description="基于因果沙盒的三国博弈叙事沙盒后端服务",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game_router, prefix="/api")
app.include_router(map_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(save_router, prefix="/api")


@app.get("/")
def root():
    return {"name": "AI三国演义 API", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"status": "ok"}
