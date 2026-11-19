import logging
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.trader import Trader
from app.models.position import Position
from app.market.price_feed import stock_feed
from app.trading.order_simulator import OrderSimulator

logger = logging.getLogger("trading.risk_manager")

class RiskManager:
    def __init__(self):
        self.kill_switch_active = False

    def activate_kill_switch(self):
        self.kill_switch_active = True
        logger.warning("KILL SWITCH GLOBAL ATIVADO: Novas operações bloqueadas em toda a mesa.")

    def deactivate_kill_switch(self):
        self.kill_switch_active = False
        logger.info("KILL SWITCH GLOBAL DESATIVADO: Operações liberadas.")

    def can_open_position(self, trader: Trader, open_positions_count: int) -> tuple[bool, str]:
        if self.kill_switch_active:
            return False, "Kill Switch global ativado."

        if trader.status != "active":
            return False, f"Operador em status '{trader.status}'."

        if trader.cash_balance < 10.0:
            return False, "Saldo livre insuficiente (< $10.00)."

        # Limite máximo de 2 posições simultâneas para capital de $100
        if open_positions_count >= 2:
            return False, "Limite máximo de posições simultâneas atingido (2)."

        # Limite de perda diária (Drawdown)
        max_loss = trader.initial_capital * trader.max_drawdown_daily_pct
        if trader.realized_pnl <= -max_loss:
            return False, f"Limite de perda diária atingido (${trader.realized_pnl:.2f} <= -${max_loss:.2f})."

        return True, "Aprovado"

    async def evaluate_open_positions_tick(self):
        """Avalia todas as posições abertas contra o preço atual das ações,
        calculando P&L não realizado e disparando Stop Loss / Take Profit automaticamente."""
        async with AsyncSessionLocal() as db:
            query = select(Position).where(Position.status == "OPEN")
            result = await db.execute(query)
            open_positions = result.scalars().all()

            for pos in open_positions:
                cur_price = stock_feed.get_price(pos.symbol)
                if cur_price <= 0:
                    continue

                # Atualiza preço corrente
                pos.current_price = cur_price
                gross_cur_val = pos.quantity * cur_price
                unrealized = round(gross_cur_val - pos.invested_amount, 2)
                pos.unrealized_pnl = unrealized
                pos.unrealized_pnl_pct = round((unrealized / pos.invested_amount) * 100, 2)

                trader = await db.get(Trader, pos.trader_id)
                if not trader:
                    continue

                # Checa Stop Loss
                if pos.stop_loss_price and cur_price <= pos.stop_loss_price:
                    logger.info(f"Disparo de STOP LOSS para {trader.name} em {pos.symbol} @ ${cur_price:.2f}")
                    await OrderSimulator.execute_sell(
                        db, trader, pos, cur_price,
                        reasoning=f"Stop Loss automático acionado (${cur_price:.2f} <= ${pos.stop_loss_price:.2f})"
                    )
                    continue

                # Checa Take Profit
                if pos.take_profit_price and cur_price >= pos.take_profit_price:
                    logger.info(f"Disparo de TAKE PROFIT para {trader.name} em {pos.symbol} @ ${cur_price:.2f}")
                    await OrderSimulator.execute_sell(
                        db, trader, pos, cur_price,
                        reasoning=f"Take Profit automático atingido (${cur_price:.2f} >= ${pos.take_profit_price:.2f})"
                    )
                    continue

                # Recalcula patrimônio total do operador
                trader.unrealized_pnl = unrealized
                trader.total_equity = round(trader.cash_balance + trader.invested_capital + unrealized, 2)

            await db.commit()

risk_manager = RiskManager()
