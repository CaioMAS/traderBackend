from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.trader import Trader
from app.models.news import NewsItem
from app.trading.risk_manager import risk_manager
from app.ai.token_governor import token_governor
from app.market.stock_market_feed import stock_market_client

router = APIRouter(prefix="/api/admin", tags=["admin"])

class AddAssetRequest(BaseModel):
    symbol: str

@router.get("/assets")
async def get_monitored_assets():
    return {
        "assets": stock_market_client.monitored_stocks
    }

@router.post("/assets")
async def add_monitored_asset(req: AddAssetRequest):
    sym = req.symbol.strip().upper()
    if not sym:
        raise HTTPException(status_code=400, detail="Símbolo inválido.")
    added = await stock_market_client.add_stock(sym)
    return {
        "symbol": sym,
        "added": added,
        "all_assets": stock_market_client.monitored_stocks
    }

@router.delete("/assets/{symbol}")
async def remove_monitored_asset(symbol: str):
    removed = await stock_market_client.remove_stock(symbol)
    return {
        "symbol": symbol.upper(),
        "removed": removed,
        "all_assets": stock_market_client.monitored_stocks
    }

@router.post("/kill-switch/toggle")
async def toggle_kill_switch():
    if risk_manager.kill_switch_active:
        risk_manager.deactivate_kill_switch()
    else:
        risk_manager.activate_kill_switch()
    return {"kill_switch_active": risk_manager.kill_switch_active}

@router.get("/tokens")
async def get_token_metrics():
    return token_governor.get_status_dashboard()

@router.get("/rankings")
async def get_rankings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Trader))
    traders = result.scalars().all()
    
    sorted_traders = sorted(
        traders,
        key=lambda t: (t.realized_pnl + t.unrealized_pnl),
        reverse=True
    )
    
    rankings = []
    for rank, t in enumerate(sorted_traders, 1):
        total_pnl = t.realized_pnl + t.unrealized_pnl
        total_trades = t.winning_trades_count + t.losing_trades_count
        win_rate = (t.winning_trades_count / total_trades * 100) if total_trades > 0 else 0.0
        
        rankings.append({
            "rank": rank,
            "id": t.id,
            "name": t.name,
            "strategy": t.strategy,
            "trading_mode": t.trading_mode,
            "allowed_assets": getattr(t, "allowed_assets", "ALL"),
            "total_pnl": round(total_pnl, 2),
            "realized_pnl": round(t.realized_pnl, 2),
            "unrealized_pnl": round(t.unrealized_pnl, 2),
            "win_rate": round(win_rate, 1),
            "total_trades": total_trades,
            "status": t.status
        })
    return rankings

@router.get("/news")
async def get_news_feed(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NewsItem).order_by(NewsItem.created_at.desc()).limit(15))
    news = result.scalars().all()
    return [n.to_dict() for n in news]

@router.post("/pause-all")
async def pause_all_traders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Trader))
    for t in result.scalars().all():
        t.status = "paused"
        t.current_activity = "Pausado pelo Administrador"
    await db.commit()
    return {"message": "Todos os operadores foram pausados."}

@router.post("/resume-all")
async def resume_all_traders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Trader))
    for t in result.scalars().all():
        t.status = "active"
        t.current_activity = "Reativado pelo Administrador"
    await db.commit()
    return {"message": "Todos os operadores foram reativados."}
