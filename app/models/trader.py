import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class Trader(Base):
    __tablename__ = "traders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(64), nullable=False)
    role = Column(String(32), default="trader") # trader, news_analyst
    personality = Column(String(64), default="meticuloso") # agressivo, conservador, etc.
    risk_profile = Column(String(32), default="medium") # low, medium, high
    strategy = Column(String(64), default="EMA & RSI Momentum")
    trading_mode = Column(String(32), default="day_trade") # day_trade, swing_trade
    allowed_assets = Column(String(512), default="ALL") # ALL ou lista separada por vírgula (ex: NVDA,AAPL)
    ai_model = Column(String(64), default="gpt-4o-mini")
    avatar_color = Column(String(32), default="#3b82f6")
    desk_index = Column(Integer, default=0) # Posição na sala 3D

    # Finanças (Carteira Isolada com $200.00)
    initial_capital = Column(Float, default=200.0)
    cash_balance = Column(Float, default=200.0)
    invested_capital = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    total_equity = Column(Float, default=200.0)

    # Parâmetros de Risco
    stop_loss_pct = Column(Float, default=0.02) # 2%
    take_profit_pct = Column(Float, default=0.04) # 4%
    max_drawdown_daily_pct = Column(Float, default=0.15) # 15%
    analysis_frequency_seconds = Column(Integer, default=60) # Intervalo do ciclo

    # Status Operacional
    status = Column(String(32), default="active") # active, paused, circuit_break
    current_activity = Column(String(256), default="Observando fluxo de mercado")
    last_decision_reasoning = Column(String(1024), default="")
    
    # Métricas
    total_tokens_consumed = Column(Integer, default=0)
    total_trades_count = Column(Integer, default=0)
    winning_trades_count = Column(Integer, default=0)
    losing_trades_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relacionamentos
    positions = relationship("Position", back_populates="trader", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="trader", cascade="all, delete-orphan")
    token_logs = relationship("TokenLog", back_populates="trader", cascade="all, delete-orphan")

    def to_dict(self):
        pnl_pct = 0.0
        if self.initial_capital > 0:
            pnl_pct = ((self.total_equity - self.initial_capital) / self.initial_capital) * 100

        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "personality": self.personality,
            "risk_profile": self.risk_profile,
            "strategy": self.strategy,
            "trading_mode": self.trading_mode,
            "allowed_assets": self.allowed_assets or "ALL",
            "ai_model": self.ai_model,
            "avatar_color": self.avatar_color,
            "desk_index": self.desk_index,
            "initial_capital": round(self.initial_capital, 2),
            "cash_balance": round(self.cash_balance, 2),
            "invested_capital": round(self.invested_capital, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "total_equity": round(self.total_equity, 2),
            "pnl_pct": round(pnl_pct, 2),
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "status": self.status,
            "current_activity": self.current_activity,
            "last_decision_reasoning": self.last_decision_reasoning,
            "total_tokens_consumed": self.total_tokens_consumed,
            "total_trades_count": self.total_trades_count,
            "winning_trades_count": self.winning_trades_count,
            "losing_trades_count": self.losing_trades_count,
        }
