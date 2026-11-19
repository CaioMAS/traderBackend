import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime
from app.core.database import Base

class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(256), nullable=False)
    source = Column(String(64), default="Bloomberg / Reuters Wire")
    summary = Column(String(1024), nullable=False)
    sentiment_score = Column(Float, default=0.0) # -1.0 (muito negativo) a +1.0 (muito positivo)
    impact_level = Column(String(16), default="MEDIUM") # LOW, MEDIUM, HIGH
    affected_assets = Column(String(64), default="BTC,ETH")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "summary": self.summary,
            "sentiment_score": round(self.sentiment_score, 2),
            "impact_level": self.impact_level,
            "affected_assets": self.affected_assets,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
