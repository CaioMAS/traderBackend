import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.news import NewsItem

logger = logging.getLogger("ai.news_analyst")

STOCK_NEWS_DISPATCHES = [
    {
        "title": "Fed sinaliza estabilidade nas taxas de juros com inflação em trajetória controlada",
        "source": "Federal Reserve Press / Bloomberg",
        "summary": "A autoridade monetária americana indicou manutenção das taxas, favorecendo o apetite a risco no setor de tecnologia e índices S&P 500.",
        "sentiment_score": 0.65,
        "impact_level": "HIGH",
        "affected_assets": "SPY,QQQ,AAPL,MSFT"
    },
    {
        "title": "Nvidia anuncia nova geração de semicondutores com eficiência energética recorde para data centers",
        "source": "TechWire / Reuters",
        "summary": "Analistas de Wall Street revisaram o preço-alvo da fabricante de chips para cima, projetando forte demanda de hyperscalers.",
        "sentiment_score": 0.85,
        "impact_level": "HIGH",
        "affected_assets": "NVDA,MSFT"
    },
    {
        "title": "Tesla registra aceleração na produção global e expansão de infraestrutura de robótaxis",
        "source": "Automotive News / CNBC",
        "summary": "Dados preliminares de entregas trimestrais superaram as expectativas de consenso do mercado.",
        "sentiment_score": 0.70,
        "impact_level": "MEDIUM",
        "affected_assets": "TSLA"
    },
    {
        "title": "Setor de computação em nuvem apresenta margens operacionais sólidas nos balanços trimestrais",
        "source": "Wall Street Journal",
        "summary": "Amazon AWS e Microsoft Azure reportam crescimento de dois dígitos em receitas corporativas de inteligência artificial.",
        "sentiment_score": 0.75,
        "impact_level": "MEDIUM",
        "affected_assets": "AMZN,MSFT"
    },
    {
        "title": "Volatilidade no mercado de títulos públicos (Treasuries) gera cautela pontual em ações de crescimento",
        "source": "Financial Times",
        "summary": "Rendimento da Treasury de 10 anos subiu levemente, levando fundos quantitativos a realizarem lucros parciais no índice Nasdaq.",
        "sentiment_score": -0.30,
        "impact_level": "LOW",
        "affected_assets": "QQQ,AAPL"
    }
]

class NewsAnalyst:
    """Analista de Inteligência de Mercado que sintetiza notícias e compartilha no quadro de avisos central."""

    def __init__(self):
        self.latest_briefing: str = "Mercado de ações operando em tom construtivo, com liderança das big techs (NVDA, MSFT, AAPL)."
        self.latest_sentiment: float = 0.50
        self.is_running: bool = False
        self.task: asyncio.Task | None = None

    async def start(self):
        self.is_running = True
        self.task = asyncio.create_task(self._analysis_loop())
        logger.info("Agente Analista de Notícias inicializado.")

    async def stop(self):
        self.is_running = False
        if self.task:
            self.task.cancel()

    def get_market_intelligence_briefing(self) -> str:
        return self.latest_briefing

    async def _analysis_loop(self):
        # Gera uma notícia inicial de imediato
        await self._publish_random_news()
        
        while self.is_running:
            # Analisa o mercado e publica um novo briefing a cada 2 minutos
            await asyncio.sleep(120)
            if not self.is_running:
                break
            await self._publish_random_news()

    async def _publish_random_news(self):
        try:
            item_data = random.choice(STOCK_NEWS_DISPATCHES)
            async with AsyncSessionLocal() as db:
                news = NewsItem(
                    title=item_data["title"],
                    source=item_data["source"],
                    summary=item_data["summary"],
                    sentiment_score=item_data["sentiment_score"],
                    impact_level=item_data["impact_level"],
                    affected_assets=item_data["affected_assets"]
                )
                db.add(news)
                await db.commit()

            self.latest_briefing = f"[{item_data['source']}] {item_data['title']}: {item_data['summary']}"
            self.latest_sentiment = item_data["sentiment_score"]
            logger.info(f"Novo briefing publicado pelo Analista: {news.title}")
        except Exception as e:
            logger.error(f"Erro ao publicar briefing de notícias: {e}")

news_analyst = NewsAnalyst()
