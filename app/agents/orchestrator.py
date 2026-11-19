import asyncio
import logging
import uuid
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.trader import Trader
from app.agents.base_agent import BaseAgentRunner
from app.trading.risk_manager import risk_manager

logger = logging.getLogger("agents.orchestrator")

DEFAULT_TRADERS_SEED = [
    {
        "name": "Rafael Alcantara",
        "role": "trader",
        "personality": "Agressivo & Veloz",
        "risk_profile": "high",
        "strategy": "Scalping Intraday & Volume",
        "trading_mode": "day_trade",
        "allowed_assets": "ALL",
        "ai_model": "gpt-4o-mini",
        "avatar_color": "#22c55e",
        "desk_index": 0,
        "stop_loss_pct": 0.018,
        "take_profit_pct": 0.040, # 4% alvo
        "analysis_frequency_seconds": 25,
    },
    {
        "name": "Beatriz Mendonça",
        "role": "trader",
        "personality": "Meticulosa & Técnica",
        "risk_profile": "medium",
        "strategy": "RSI & Bollinger Breakout",
        "trading_mode": "day_trade",
        "allowed_assets": "ALL",
        "ai_model": "gpt-4o-mini",
        "avatar_color": "#3b82f6",
        "desk_index": 1,
        "stop_loss_pct": 0.020,
        "take_profit_pct": 0.050, # 5% alvo
        "analysis_frequency_seconds": 35,
    },
    {
        "name": "Lucas Silveira",
        "role": "trader",
        "personality": "Analítico & Paciente",
        "risk_profile": "low",
        "strategy": "Trend Following (Médias 50/200)",
        "trading_mode": "swing_trade",
        "allowed_assets": "ALL",
        "ai_model": "gpt-4o-mini",
        "avatar_color": "#a855f7",
        "desk_index": 2,
        "stop_loss_pct": 0.035,
        "take_profit_pct": 0.080, # 8% alvo
        "analysis_frequency_seconds": 50,
    },
    {
        "name": "Camila Duarte",
        "role": "trader",
        "personality": "Estratégica & Focada em Valor",
        "risk_profile": "medium",
        "strategy": "Suporte, Resistência & Pullback",
        "trading_mode": "swing_trade",
        "allowed_assets": "ALL",
        "ai_model": "gpt-4o-mini",
        "avatar_color": "#f59e0b",
        "desk_index": 3,
        "stop_loss_pct": 0.030,
        "take_profit_pct": 0.075, # 7.5% alvo
        "analysis_frequency_seconds": 45,
    },
    {
        "name": "Marcos Hayashi",
        "role": "trader",
        "personality": "Contrarian & Oportunista",
        "risk_profile": "high",
        "strategy": "Reversão à Média com MACD",
        "trading_mode": "day_trade",
        "allowed_assets": "ALL",
        "ai_model": "gpt-4o-mini",
        "avatar_color": "#ec4899",
        "desk_index": 4,
        "stop_loss_pct": 0.022,
        "take_profit_pct": 0.045, # 4.5% alvo
        "analysis_frequency_seconds": 30,
    },
    {
        "name": "Helena Rostova",
        "role": "trader",
        "personality": "Quantitativa & Sistemática",
        "risk_profile": "low",
        "strategy": "Bandas de Volatilidade e Momentum",
        "trading_mode": "swing_trade",
        "allowed_assets": "ALL",
        "ai_model": "gpt-4o-mini",
        "avatar_color": "#06b6d4",
        "desk_index": 5,
        "stop_loss_pct": 0.030,
        "take_profit_pct": 0.070, # 7% alvo
        "analysis_frequency_seconds": 60,
    },
]

class AgentOrchestrator:
    def __init__(self):
        self.is_running = False
        self.agent_tasks: list[asyncio.Task] = []
        self.risk_task: asyncio.Task | None = None

    async def start(self):
        self.is_running = True
        logger.info("Iniciando orquestrador de operadores...")
        await self._seed_default_traders_if_empty()
        
        # Inicia loop contínuo de avaliação de risco
        self.risk_task = asyncio.create_task(self._risk_monitoring_loop())
        
        # Inicia loops autônomos para cada operador ativo
        await self._spawn_all_active_agents()

    async def stop(self):
        self.is_running = False
        if self.risk_task:
            self.risk_task.cancel()
        for t in self.agent_tasks:
            t.cancel()
        self.agent_tasks.clear()

    async def _seed_default_traders_if_empty(self):
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Trader))
            existing = result.scalars().all()
            if existing:
                logger.info(f"Histórico prévio preservado: {len(existing)} operadores mantidos no banco de dados.")
                return

            logger.info("Mesa vazia. Criando equipe padrão de operadores com capital inicial de $200.00...")
            for t_data in DEFAULT_TRADERS_SEED:
                trader = Trader(
                    id=str(uuid.uuid4()),
                    name=t_data["name"],
                    role=t_data["role"],
                    personality=t_data["personality"],
                    risk_profile=t_data["risk_profile"],
                    strategy=t_data["strategy"],
                    trading_mode=t_data["trading_mode"],
                    allowed_assets=t_data.get("allowed_assets", "ALL"),
                    ai_model=t_data["ai_model"],
                    avatar_color=t_data["avatar_color"],
                    desk_index=t_data["desk_index"],
                    initial_capital=200.0,
                    cash_balance=200.0,
                    invested_capital=0.0,
                    realized_pnl=0.0,
                    unrealized_pnl=0.0,
                    total_equity=200.0,
                    stop_loss_pct=t_data["stop_loss_pct"],
                    take_profit_pct=t_data["take_profit_pct"],
                    analysis_frequency_seconds=t_data["analysis_frequency_seconds"],
                    status="active",
                    current_activity="Pronto para operar com $200"
                )
                db.add(trader)
            await db.commit()

    async def _spawn_all_active_agents(self):
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Trader).where(Trader.status == "active"))
            active_traders = result.scalars().all()
            for trader in active_traders:
                task = asyncio.create_task(self._run_trader_worker(trader.id, trader.analysis_frequency_seconds))
                self.agent_tasks.append(task)
        logger.info(f"{len(self.agent_tasks)} agentes autônomos ativos retomando operações.")

    async def _run_trader_worker(self, trader_id: str, frequency: int):
        await asyncio.sleep(float(uuid.UUID(trader_id).int % 10))
        while self.is_running:
            try:
                async with AsyncSessionLocal() as db:
                    await BaseAgentRunner.run_cycle(db, trader_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no ciclo do agente {trader_id}: {e}")
            
            await asyncio.sleep(max(15, frequency))

    async def _risk_monitoring_loop(self):
        """Avalia Stop Loss / Take Profit em todas as posições abertas a cada segundo."""
        while self.is_running:
            try:
                await risk_manager.evaluate_open_positions_tick()
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no monitoramento de risco: {e}")
                await asyncio.sleep(2.0)

agent_orchestrator = AgentOrchestrator()
