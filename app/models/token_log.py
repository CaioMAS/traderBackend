import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class TokenLog(Base):
    __tablename__ = "token_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trader_id = Column(String(36), ForeignKey("traders.id"), nullable=True)
    model = Column(String(64), nullable=False)
    group = Column(Integer, nullable=False) # 1 ou 2
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    purpose = Column(String(64), default="trade_decision")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    trader = relationship("Trader", back_populates="token_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "trader_id": self.trader_id,
            "model": self.model,
            "group": self.group,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 5),
            "purpose": self.purpose,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
