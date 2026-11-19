import uuid
from datetime import datetime, timezone
import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.trader import Trader
from app.models.position import Position
from app.models.trade import Trade
from app.core.config import settings

class OrderSimulator:
    """Simulador de execução de ordens com taxas e slippage realista."""

    @staticmethod
    async def execute_buy(
        db: AsyncSession,
        trader: Trader,
        symbol: str,
        target_allocation_usd: float,
        current_price: float,
        stop_loss_pct: float,
        take_profit_pct: float,
        reasoning: str
    ) -> Trade | None:
        if trader.cash_balance < 10.0:
            return None # Saldo insuficiente
        
        # Alocação máxima respeitando saldo disponível
        allocation = min(trader.cash_balance, target_allocation_usd)
        if allocation < 5.0:
            return None

        # Slippage sutil (ex: 0.02% para ações líquidas como AAPL, NVDA)
        slippage = random.uniform(0.0001, 0.0003)
        execution_price = round(current_price * (1 + slippage), 2)
        
        # Taxa simulada (0.1% padrão)
        fee = round(allocation * settings.SIMULATED_FEE_PERCENTAGE, 4)
        net_allocation = allocation - fee
        quantity = round(net_allocation / execution_price, 4)

        if quantity <= 0:
            return None

        # Debita saldo
        trader.cash_balance -= allocation
        trader.invested_capital += net_allocation
        trader.total_equity = trader.cash_balance + trader.invested_capital + trader.unrealized_pnl

        # Cria posição aberta
        sl_price = round(execution_price * (1 - stop_loss_pct), 2)
        tp_price = round(execution_price * (1 + take_profit_pct), 2)

        position = Position(
            id=str(uuid.uuid4()),
            trader_id=trader.id,
            symbol=symbol,
            side="LONG",
            entry_price=execution_price,
            current_price=execution_price,
            quantity=quantity,
            invested_amount=net_allocation,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            stop_loss_price=sl_price,
            take_profit_price=tp_price,
            status="OPEN"
        )
        db.add(position)
        await db.flush()

        trade = Trade(
            id=str(uuid.uuid4()),
            trader_id=trader.id,
            position_id=position.id,
            symbol=symbol,
            side="BUY",
            price=execution_price,
            quantity=quantity,
            total_value=allocation,
            fee_paid=fee,
            realized_pnl=0.0,
            reasoning=reasoning
        )
        db.add(trade)

        trader.total_trades_count += 1
        trader.last_decision_reasoning = f"COMPRA {symbol} @ ${execution_price:.2f} — {reasoning}"
        await db.commit()
        return trade

    @staticmethod
    async def execute_sell(
        db: AsyncSession,
        trader: Trader,
        position: Position,
        current_price: float,
        reasoning: str
    ) -> Trade | None:
        if position.status != "OPEN":
            return None

        # Slippage sutil na venda
        slippage = random.uniform(0.0001, 0.0003)
        execution_price = round(current_price * (1 - slippage), 2)
        
        gross_value = round(position.quantity * execution_price, 2)
        fee = round(gross_value * settings.SIMULATED_FEE_PERCENTAGE, 4)
        net_proceeds = gross_value - fee

        # Lucro realizado efetivo
        realized_pnl = round(net_proceeds - position.invested_amount, 2)

        # Atualiza carteira do operador
        trader.cash_balance += net_proceeds
        trader.invested_capital -= position.invested_amount
        if trader.invested_capital < 0:
            trader.invested_capital = 0.0

        trader.realized_pnl += realized_pnl
        trader.total_equity = trader.cash_balance + trader.invested_capital

        trader.total_trades_count += 1
        if realized_pnl >= 0:
            trader.winning_trades_count += 1
        else:
            trader.losing_trades_count += 1

        position.status = "CLOSED"
        position.closed_at = datetime.now(timezone.utc)
        position.current_price = execution_price
        position.unrealized_pnl = 0.0

        trade = Trade(
            id=str(uuid.uuid4()),
            trader_id=trader.id,
            position_id=position.id,
            symbol=position.symbol,
            side="SELL",
            price=execution_price,
            quantity=position.quantity,
            total_value=gross_value,
            fee_paid=fee,
            realized_pnl=realized_pnl,
            reasoning=reasoning
        )
        db.add(trade)
        trader.last_decision_reasoning = f"VENDA {position.symbol} @ ${execution_price:.2f} (P&L: ${realized_pnl:+.2f}) — {reasoning}"
        
        await db.commit()
        return trade
