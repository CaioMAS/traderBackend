import asyncio
import json
import logging
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.trader import Trader
from app.market.price_feed import stock_feed
from app.ai.token_governor import token_governor
from app.ai.news_analyst import news_analyst
from app.trading.risk_manager import risk_manager

logger = logging.getLogger("api.websocket_hub")

class WebSocketHub:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.broadcast_task: asyncio.Task | None = None
        self.is_running = False

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Cliente WebSocket conectado. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"Cliente WebSocket desconectado. Total: {len(self.active_connections)}")

    async def start(self):
        self.is_running = True
        self.broadcast_task = asyncio.create_task(self._broadcast_loop())

    async def stop(self):
        self.is_running = False
        if self.broadcast_task:
            self.broadcast_task.cancel()

    async def _broadcast_loop(self):
        """Transmite o estado completo da sala 3D a cada 1 segundo para o frontend."""
        while self.is_running:
            try:
                if self.active_connections:
                    payload = await self._build_floor_state_payload()
                    msg = json.dumps(payload)
                    # Envia para todos os clientes conectados
                    to_remove = set()
                    for ws in self.active_connections:
                        try:
                            await ws.send_text(msg)
                        except Exception:
                            to_remove.add(ws)
                    for dead_ws in to_remove:
                        self.active_connections.discard(dead_ws)
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no loop do WebSocketHub: {e}")
                await asyncio.sleep(2.0)

    async def _build_floor_state_payload(self) -> dict:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Trader).order_by(Trader.desk_index))
            traders = [t.to_dict() for t in result.scalars().all()]

        tickers = stock_feed.get_all_tickers()
        token_stats = token_governor.get_status_dashboard()
        news_memo = news_analyst.get_market_intelligence_briefing()

        total_floor_equity = sum(t["total_equity"] for t in traders)
        total_realized_pnl = sum(t["realized_pnl"] for t in traders)
        total_unrealized_pnl = sum(t["unrealized_pnl"] for t in traders)

        return {
            "type": "FLOOR_UPDATE",
            "timestamp": asyncio.get_event_loop().time(),
            "kill_switch_active": risk_manager.kill_switch_active,
            "tickers": tickers,
            "traders": traders,
            "token_stats": token_stats,
            "news_briefing": news_memo,
            "floor_summary": {
                "total_equity": round(total_floor_equity, 2),
                "total_realized_pnl": round(total_realized_pnl, 2),
                "total_unrealized_pnl": round(total_unrealized_pnl, 2),
                "active_traders_count": len([t for t in traders if t["status"] == "active"]),
            }
        }

websocket_hub = WebSocketHub()
