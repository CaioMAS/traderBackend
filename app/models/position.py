import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Position(Base):
    __tablename__ = "positions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trader_id = Column(String(36), ForeignKey("traders.id"), nullable=False)
    symbol = Column(String(32), nullable=False) # ex: BTCUSDT
    side = Column(String(16), default="LONG") # LONG, SHORT
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    invested_amount = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, default=0.0)
    unrealized_pnl_pct = Column(Float, default=0.0)
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    status = Column(String(16), default="OPEN") # OPEN, CLOSED
    opened_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime, nullable=True)

    trader = relationship("Trader", back_populates="positions")

    def to_dict(self):
        return {
            "id": self.id,
            "trader_id": self.trader_id,
            "symbol": self.symbol,
            "side": self.side,
            "entry_price": round(self.entry_price, 4),
            "current_price": round(self.current_price, 4),
            "quantity": round(self.quantity, 6),
            "invested_amount": round(self.invested_amount, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "unrealized_pnl_pct": round(self.unrealized_pnl_pct, 2),
            "stop_loss_price": round(self.stop_loss_price, 4) if self.stop_loss_price else None,
            "take_profit_price": round(self.take_profit_price, 4) if self.take_profit_price else None,
            "status": self.status,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }
