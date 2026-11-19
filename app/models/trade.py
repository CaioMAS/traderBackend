import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Trade(Base):
    __tablename__ = "trades"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trader_id = Column(String(36), ForeignKey("traders.id"), nullable=False)
    position_id = Column(String(36), nullable=True)
    symbol = Column(String(32), nullable=False)
    side = Column(String(16), nullable=False) # BUY, SELL
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    fee_paid = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    reasoning = Column(String(1024), default="")
    executed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    trader = relationship("Trader", back_populates="trades")

    def to_dict(self):
        return {
            "id": self.id,
            "trader_id": self.trader_id,
            "position_id": self.position_id,
            "symbol": self.symbol,
            "side": self.side,
            "price": round(self.price, 4),
            "quantity": round(self.quantity, 6),
            "total_value": round(self.total_value, 2),
            "fee_paid": round(self.fee_paid, 4),
            "realized_pnl": round(self.realized_pnl, 2),
            "reasoning": self.reasoning,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }
