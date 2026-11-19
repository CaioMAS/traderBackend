import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.trader import Trader
from app.models.position import Position
from app.models.trade import Trade

router = APIRouter(prefix="/api/traders", tags=["traders"])

class CreateTraderRequest(BaseModel):
    name: str
    role: str = "trader"
    personality: str = "meticuloso"
    risk_profile: str = "medium"
    strategy: str = "RSI & EMA Momentum"
    trading_mode: str = "day_trade"
    allowed_assets: str = "ALL"
    ai_model: str = "gpt-4o-mini"
    avatar_color: str = "#3b82f6"
    desk_index: int = 0
    initial_capital: float = 100.0
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04
    analysis_frequency_seconds: int = 45

class UpdateTraderRequest(BaseModel):
    name: Optional[str] = None
    personality: Optional[str] = None
    risk_profile: Optional[str] = None
    strategy: Optional[str] = None
    trading_mode: Optional[str] = None
    allowed_assets: Optional[str] = None
    ai_model: Optional[str] = None
    avatar_color: Optional[str] = None
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    status: Optional[str] = None

@router.get("")
async def list_traders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Trader).order_by(Trader.desk_index))
    traders = result.scalars().all()
    return [t.to_dict() for t in traders]

@router.get("/{trader_id}")
async def get_trader_detail(trader_id: str, db: AsyncSession = Depends(get_db)):
    trader = await db.get(Trader, trader_id)
    if not trader:
        raise HTTPException(status_code=404, detail="Operador não encontrado.")

    pos_res = await db.execute(
        select(Position).where(Position.trader_id == trader_id).order_by(Position.opened_at.desc())
    )
    positions = [p.to_dict() for p in pos_res.scalars().all()]

    trade_res = await db.execute(
        select(Trade).where(Trade.trader_id == trader_id).order_by(Trade.executed_at.desc()).limit(20)
    )
    trades = [t.to_dict() for t in trade_res.scalars().all()]

    return {
        "trader": trader.to_dict(),
        "positions": positions,
        "recent_trades": trades,
    }

@router.post("")
async def create_trader(req: CreateTraderRequest, db: AsyncSession = Depends(get_db)):
    trader = Trader(
        id=str(uuid.uuid4()),
        name=req.name,
        role=req.role,
        personality=req.personality,
        risk_profile=req.risk_profile,
        strategy=req.strategy,
        trading_mode=req.trading_mode,
        allowed_assets=req.allowed_assets or "ALL",
        ai_model=req.ai_model,
        avatar_color=req.avatar_color,
        desk_index=req.desk_index,
        initial_capital=req.initial_capital,
        cash_balance=req.initial_capital,
        invested_capital=0.0,
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        total_equity=req.initial_capital,
        stop_loss_pct=req.stop_loss_pct,
        take_profit_pct=req.take_profit_pct,
        analysis_frequency_seconds=req.analysis_frequency_seconds,
        status="active",
        current_activity="Recém-contratado na mesa"
    )
    db.add(trader)
    await db.commit()
    return trader.to_dict()

@router.patch("/{trader_id}")
async def update_trader(trader_id: str, req: UpdateTraderRequest, db: AsyncSession = Depends(get_db)):
    trader = await db.get(Trader, trader_id)
    if not trader:
        raise HTTPException(status_code=404, detail="Operador não encontrado.")

    for field, val in req.model_dump(exclude_unset=True).items():
        setattr(trader, field, val)

    await db.commit()
    return trader.to_dict()

@router.post("/{trader_id}/reset")
async def reset_trader(trader_id: str, db: AsyncSession = Depends(get_db)):
    trader = await db.get(Trader, trader_id)
    if not trader:
        raise HTTPException(status_code=404, detail="Operador não encontrado.")

    pos_res = await db.execute(select(Position).where(Position.trader_id == trader_id, Position.status == "OPEN"))
    for p in pos_res.scalars().all():
        p.status = "CLOSED"

    trader.cash_balance = trader.initial_capital
    trader.invested_capital = 0.0
    trader.realized_pnl = 0.0
    trader.unrealized_pnl = 0.0
    trader.total_equity = trader.initial_capital
    trader.status = "active"
    trader.current_activity = "Carteira reiniciada com $100"

    await db.commit()
    return trader.to_dict()

@router.delete("/{trader_id}")
async def delete_trader(trader_id: str, db: AsyncSession = Depends(get_db)):
    trader = await db.get(Trader, trader_id)
    if not trader:
        raise HTTPException(status_code=404, detail="Operador não encontrado.")

    await db.delete(trader)
    await db.commit()
    return {"message": "Operador removido com sucesso."}
