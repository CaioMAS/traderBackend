import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.trader import Trader
from app.models.position import Position
from app.market.price_feed import stock_feed
from app.market.stock_market_feed import stock_market_client
from app.market.indicators import evaluate_opportunity_score
from app.trading.risk_manager import risk_manager
from app.trading.order_simulator import OrderSimulator
from app.ai.model_router import model_router
from app.ai.news_analyst import news_analyst
from app.ai.prompt_templates import (
    build_trader_system_prompt,
    build_trader_user_prompt
)

logger = logging.getLogger("agents.base")

class BaseAgentRunner:
    """Executa o ciclo autônomo com triagem inteligente e metas de lucro expressivas."""

    @staticmethod
    async def run_cycle(db: AsyncSession, trader_id: str) -> None:
        trader = await db.get(Trader, trader_id)
        if not trader or trader.status != "active":
            return

        # 1. Observar posições abertas
        pos_query = select(Position).where(
            Position.trader_id == trader.id,
            Position.status == "OPEN"
        )
        pos_res = await db.execute(pos_query)
        open_positions = pos_res.scalars().all()

        # 2. Lista de ativos candidatos
        allowed = getattr(trader, "allowed_assets", "ALL")
        if allowed and allowed != "ALL":
            candidates = [a.strip().upper() for a in allowed.split(",") if a.strip()]
        else:
            candidates = list(stock_market_client.monitored_stocks)

        if not candidates:
            candidates = ["NVDA", "AAPL", "TSLA", "MSFT", "AMZN", "SPY", "QQQ"]

        current_unrealized = 0.0

        # 3. SE TEM POSIÇÃO ABERTA: avalia para deixar correr o lucro ou sair
        if open_positions:
            active_pos = open_positions[0]
            target_symbol = active_pos.symbol
            current_unrealized = active_pos.unrealized_pnl
            opportunity_context = f"Gerenciando posição em {target_symbol} (P&L: ${current_unrealized:+.2f})"
            if trader.trading_mode == "day_trade":
                snapshot = stock_feed.get_day_trade_snapshot(target_symbol)
            else:
                snapshot = stock_feed.get_swing_trade_snapshot(target_symbol)

        # 4. SE NÃO TEM POSIÇÃO: Varre todo o mercado e escolhe a MELHOR oportunidade
        else:
            scored_opportunities = []
            for sym in candidates:
                if trader.trading_mode == "day_trade":
                    snap = stock_feed.get_day_trade_snapshot(sym)
                else:
                    snap = stock_feed.get_swing_trade_snapshot(sym)
                
                score, rationale = evaluate_opportunity_score(snap, trader.trading_mode)
                scored_opportunities.append({
                    "symbol": sym,
                    "score": score,
                    "rationale": rationale,
                    "snapshot": snap
                })

            scored_opportunities.sort(key=lambda x: x["score"], reverse=True)
            best = scored_opportunities[0]
            runner_up = scored_opportunities[1] if len(scored_opportunities) > 1 else None

            target_symbol = best["symbol"]
            snapshot = best["snapshot"]
            
            opportunity_context = (
                f"Varredura em {len(candidates)} ações: {target_symbol} selecionada como MELHOR OPORTUNIDADE "
                f"(Score: {best['score']:.0f}/100 • {best['rationale']})"
            )
            if runner_up:
                opportunity_context += f" | 2º Lugar: {runner_up['symbol']} ({runner_up['score']:.0f}/100)"

        trader.current_activity = f"Avaliando {target_symbol} — {opportunity_context}"
        await db.commit()

        # 5. Coleta memorando do Analista de Notícias
        news_memo = news_analyst.get_market_intelligence_briefing()

        # 6. Avalia regras de risco preliminares
        can_open, risk_reason = risk_manager.can_open_position(trader, len(open_positions))

        # 7. Prepara prompts estruturados
        sys_prompt = build_trader_system_prompt(
            name=trader.name,
            personality=trader.personality,
            strategy=trader.strategy,
            mode=trader.trading_mode,
            risk_profile=trader.risk_profile
        )

        open_pos_summary = [
            {
                "symbol": p.symbol,
                "entry": p.entry_price,
                "current": p.current_price,
                "unrealized_pnl": p.unrealized_pnl
            }
            for p in open_positions
        ]

        user_prompt = build_trader_user_prompt(
            cash_balance=trader.cash_balance,
            open_positions=open_pos_summary,
            market_snapshot=snapshot,
            latest_news_summary=f"{news_memo}\n[Screener]: {opportunity_context}"
        )

        # 8. Decisão da IA com Pydantic Structured Outputs
        has_pos_in_target = any(p.symbol == target_symbol for p in open_positions)
        decision = await model_router.decide_trade(
            trader_id=trader.id,
            preferred_model=trader.ai_model,
            system_prompt=sys_prompt,
            user_prompt=user_prompt,
            market_snapshot=snapshot,
            has_open_position=has_pos_in_target,
            unrealized_pnl=current_unrealized
        )

        # 9. Execução da Decisão
        if decision.action == "BUY":
            if not can_open:
                trader.current_activity = f"Aguardando (Risco: {risk_reason})"
                await db.commit()
                return

            cur_p = stock_feed.get_price(target_symbol)
            # Alocação inteligente proporcional a $200 (investe $70 a $95 por trade)
            allocated = min(trader.cash_balance * 0.48, max(70.0, decision.allocation_usd))
            
            await OrderSimulator.execute_buy(
                db=db,
                trader=trader,
                symbol=target_symbol,
                target_allocation_usd=allocated,
                current_price=cur_p,
                stop_loss_pct=trader.stop_loss_pct,
                take_profit_pct=trader.take_profit_pct,
                reasoning=f"[Melhor Oportunidade Alocada: ${allocated:.2f}] {decision.reasoning}"
            )
            trader.current_activity = f"Comprou {target_symbol} @ ${cur_p:.2f} (Alocado: ${allocated:.2f})"

        elif decision.action == "SELL" and has_pos_in_target:
            pos_to_sell = next(p for p in open_positions if p.symbol == target_symbol)
            cur_p = stock_feed.get_price(target_symbol)
            await OrderSimulator.execute_sell(
                db=db,
                trader=trader,
                position=pos_to_sell,
                current_price=cur_p,
                reasoning=decision.reasoning
            )
            trader.current_activity = f"Vendeu {target_symbol} @ ${cur_p:.2f} (Lucro realizado: ${pos_to_sell.unrealized_pnl:+.2f})"

        else:
            trader.current_activity = f"Varreu {len(candidates)} ações. Monitorando {target_symbol}"
            trader.last_decision_reasoning = f"HOLD em {target_symbol} — {decision.reasoning}"

        # 10. Atualiza estado e patrimônio
        await db.commit()
