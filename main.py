import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.core.security import verify_session_token
from app.market.stock_market_feed import stock_market_client
from app.trading.reconciler import state_reconciler
from app.ai.news_analyst import news_analyst
from app.agents.orchestrator import agent_orchestrator
from app.api.websocket_hub import websocket_hub
from app.api.routes_auth import router as auth_router
from app.api.routes_traders import router as traders_router
from app.api.routes_admin import router as admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== INICIANDO TRADING FLOOR AI (MESA DE OPERAÇÕES) ===")
    await init_db()
    await stock_market_client.start()
    await state_reconciler.reconcile_on_startup()
    await news_analyst.start()
    await agent_orchestrator.start()
    await websocket_hub.start()
    logger.info("Mesa de Operações totalmente operacional com persistência garantida.")
    yield
    
    logger.info("Desligando serviços...")
    await websocket_hub.stop()
    await agent_orchestrator.stop()
    await news_analyst.stop()
    await stock_market_client.stop()
    logger.info("Serviços finalizados com sucesso.")

app = FastAPI(
    title="Trading Floor AI",
    description="Mesa de Operações com Agentes Autônomos em Mercado de Ações",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(traders_router)
app.include_router(admin_router)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = Query(None)):
    # Valida senha/token se configurada no .env
    if settings.ACCESS_PASSWORD and not verify_session_token(token):
        logger.warning("Conexão WebSocket rejeitada: token não autorizado.")
        await websocket.close(code=1008)
        return

    await websocket_hub.connect(websocket)
    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_hub.disconnect(websocket)
    except Exception:
        websocket_hub.disconnect(websocket)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "market": "stocks",
        "assets": stock_market_client.monitored_stocks,
        "auth_enabled": bool(settings.ACCESS_PASSWORD),
        "persistence": "SQLite WAL in backend/data"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=False)
