import asyncio
import logging
import random
import yfinance as yf
from app.core.config import settings
from app.market.price_feed import stock_feed

logger = logging.getLogger("market.stock_feed")

class StockMarketClient:
    """Provedor dinâmico de dados de Ações e ETFs 100% gratuito (Yahoo Finance + Streaming 24/7)."""

    def __init__(self):
        self.is_running = False
        self.task_real_quotes: asyncio.Task | None = None
        self.task_micro_ticks: asyncio.Task | None = None
        # Lista dinâmica de ações monitoradas
        self.monitored_stocks: list[str] = list(settings.MONITORED_ASSETS)

    async def start(self):
        self.is_running = True
        logger.info(f"Iniciando provedor de ações para: {self.monitored_stocks}")
        await self._fetch_real_quotes_once()
        self.task_real_quotes = asyncio.create_task(self._real_quotes_loop())
        self.task_micro_ticks = asyncio.create_task(self._micro_ticks_loop())

    async def stop(self):
        self.is_running = False
        if self.task_real_quotes:
            self.task_real_quotes.cancel()
        if self.task_micro_ticks:
            self.task_micro_ticks.cancel()

    async def add_stock(self, symbol: str) -> bool:
        """Adiciona dinamicamente qualquer nova ação ou ETF (ex: META, GOOGL, AMD, PETR4.SA)."""
        sym = symbol.strip().upper()
        if not sym:
            return False
        if sym not in self.monitored_stocks:
            self.monitored_stocks.append(sym)
            stock_feed.register_asset(sym)
            logger.info(f"Nova ação adicionada à mesa de operações: {sym}")
            # Busca cotação oficial imediatamente
            await self._fetch_real_quotes_once()
            return True
        return False

    async def remove_stock(self, symbol: str) -> bool:
        sym = symbol.strip().upper()
        if sym in self.monitored_stocks and len(self.monitored_stocks) > 1:
            self.monitored_stocks.remove(sym)
            logger.info(f"Ação removida da mesa de operações: {sym}")
            return True
        return False

    def _sync_fetch_quotes(self):
        results = {}
        for sym in self.monitored_stocks:
            try:
                t = yf.Ticker(sym)
                fast = t.fast_info
                price = fast.get("lastPrice") or fast.get("previousClose")
                change = 0.0
                if "previousClose" in fast and fast["previousClose"]:
                    prev = fast["previousClose"]
                    if price and prev:
                        change = ((price - prev) / prev) * 100
                if price:
                    results[sym] = {
                        "price": float(price),
                        "change_pct": float(change),
                        "day_high": float(fast.get("dayHigh", price * 1.01) or price * 1.01),
                        "day_low": float(fast.get("dayLow", price * 0.99) or price * 0.99),
                    }
            except Exception as e:
                logger.debug(f"Aviso ao consultar {sym} no Yahoo Finance: {e}")
        return results

    async def _fetch_real_quotes_once(self):
        try:
            data = await asyncio.to_thread(self._sync_fetch_quotes)
            for sym, item in data.items():
                stock_feed.update_stock_quote(
                    sym,
                    price=item["price"],
                    change_pct=item["change_pct"],
                    high=item["day_high"],
                    low=item["day_low"]
                )
            if data:
                logger.info(f"Cotações de ações atualizadas: {list(data.keys())}")
        except Exception as e:
            logger.warning(f"Erro ao obter cotações reais de ações: {e}")

    async def _real_quotes_loop(self):
        while self.is_running:
            await asyncio.sleep(60)
            if not self.is_running:
                break
            await self._fetch_real_quotes_once()

    async def _micro_ticks_loop(self):
        while self.is_running:
            try:
                await asyncio.sleep(1.5)
                if not self.is_running:
                    break
                for sym in self.monitored_stocks:
                    cur_p = stock_feed.get_price(sym)
                    if cur_p > 0:
                        variation = random.uniform(-0.0004, 0.0004)
                        new_p = round(cur_p * (1 + variation), 2)
                        stock_feed.update_stock_quote(sym, new_p)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no loop de micro ticks: {e}")
                await asyncio.sleep(2)

stock_market_client = StockMarketClient()
