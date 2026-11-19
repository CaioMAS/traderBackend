import logging
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.trader import Trader
from app.models.position import Position
from app.models.trade import Trade
from app.market.price_feed import stock_feed
from app.trading.order_simulator import OrderSimulator

logger = logging.getLogger("trading.reconciler")

class StateReconciler:
    """Garante persistência total do histórico e reconcilia posições abertas após reinicializações."""

    @staticmethod
    async def reconcile_on_startup():
        logger.info("=== RECONCILIAÇÃO DE ESTADO E PERSISTÊNCIA INICIADA ===")
        async with AsyncSessionLocal() as db:
            # 1. Contagem de auditoria
            traders_count = await db.scalar(select(func.count(Trader.id))) or 0
            trades_count = await db.scalar(select(func.count(Trade.id))) or 0
            open_pos_count = await db.scalar(select(func.count(Position.id)).where(Position.status == "OPEN")) or 0

            logger.info(
                f"Auditoria de Persistência: {traders_count} operadores, "
                f"{trades_count} operações históricas arquivadas, "
                f"{open_pos_count} posições abertas."
            )

            if traders_count == 0:
                logger.info("Nenhum operador anterior encontrado. A mesa será inicializada pela primeira vez.")
                return

            # 2. Reconciliação de posições abertas com cotações atuais de mercado
            pos_result = await db.execute(select(Position).where(Position.status == "OPEN"))
            open_positions = pos_result.scalars().all()

            for pos in open_positions:
                cur_price = stock_feed.get_price(pos.symbol)
                pos.current_price = cur_price
                gross_value = pos.quantity * cur_price
                unrealized = round(gross_value - pos.invested_amount, 2)
                pos.unrealized_pnl = unrealized
                pos.unrealized_pnl_pct = round((unrealized / pos.invested_amount) * 100, 2)

                trader = await db.get(Trader, pos.trader_id)
                if not trader:
                    continue

                # Checa se o preço cruzou Stop Loss durante o período offline
                if pos.stop_loss_price and cur_price <= pos.stop_loss_price:
                    logger.warning(
                        f"[RECONCILIAÇÃO] Posição em {pos.symbol} atingiu Stop Loss offline (${cur_price:.2f} <= ${pos.stop_loss_price:.2f}). Executando saída..."
                    )
                    await OrderSimulator.execute_sell(
                        db, trader, pos, cur_price,
                        reasoning=f"Stop Loss offline acionado na reconciliação de boot (${cur_price:.2f} <= ${pos.stop_loss_price:.2f})"
                    )
                    continue

                # Checa Take Profit offline
                if pos.take_profit_price and cur_price >= pos.take_profit_price:
                    logger.info(
                        f"[RECONCILIAÇÃO] Posição em {pos.symbol} atingiu Take Profit offline (${cur_price:.2f} >= ${pos.take_profit_price:.2f}). Executando realização..."
                    )
                    await OrderSimulator.execute_sell(
                        db, trader, pos, cur_price,
                        reasoning=f"Take Profit offline acionado na reconciliação de boot (${cur_price:.2f} >= ${pos.take_profit_price:.2f})"
                    )
                    continue

            # 3. Recalcula patrimônio total e P&L consolidado de cada operador
            traders_res = await db.execute(select(Trader))
            for t in traders_res.scalars().all():
                # Soma P&L não realizado de posições que continuam abertas
                t_pos_res = await db.execute(
                    select(Position).where(Position.trader_id == t.id, Position.status == "OPEN")
                )
                t_open_pos = t_pos_res.scalars().all()
                total_unrealized = sum(p.unrealized_pnl for p in t_open_pos)
                total_invested = sum(p.invested_amount for p in t_open_pos)

                t.unrealized_pnl = round(total_unrealized, 2)
                t.invested_capital = round(total_invested, 2)
                t.total_equity = round(t.cash_balance + t.invested_capital + t.unrealized_pnl, 2)
                t.current_activity = "Restaurado com sucesso após reinicialização"

            await db.commit()
            logger.info("=== RECONCILIAÇÃO CONCLUÍDA: Todos os operadores e históricos preservados! ===")

state_reconciler = StateReconciler()
