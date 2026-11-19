import time
import random
from typing import Dict, List, Optional
from app.market.indicators import calculate_rsi, calculate_ema, calculate_bollinger_bands, calculate_macd

class StockCandle:
    def __init__(self, timestamp: float, open_: float, high: float, low: float, close: float, volume: float):
        self.timestamp = timestamp
        self.open = open_
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

    def to_dict(self):
        return {
            "time": int(self.timestamp),
            "open": round(self.open, 2),
            "high": round(self.high, 2),
            "low": round(self.low, 2),
            "close": round(self.close, 2),
            "volume": round(self.volume, 2),
        }

class StockPriceFeed:
    """Gerencia em memória as cotações do mercado de ações (NYSE, NASDAQ, B3, etc.),
    candles intraday (Day Trade) e candles diários (Swing Trade)."""

    def __init__(self):
        self.prices: Dict[str, float] = {}
        self.change_24h: Dict[str, float] = {}
        self.high_24h: Dict[str, float] = {}
        self.low_24h: Dict[str, float] = {}
        self.company_names: Dict[str, str] = {
            "NVDA": "Nvidia Corporation",
            "AAPL": "Apple Inc.",
            "TSLA": "Tesla, Inc.",
            "MSFT": "Microsoft Corporation",
            "AMZN": "Amazon.com, Inc.",
            "SPY": "SPDR S&P 500 ETF Trust",
            "QQQ": "Invesco QQQ Trust (Nasdaq 100)",
            "META": "Meta Platforms, Inc.",
            "GOOGL": "Alphabet Inc.",
            "AMD": "Advanced Micro Devices",
            "NFLX": "Netflix, Inc.",
            "PETR4.SA": "Petrobras PN (B3)",
            "VALE3.SA": "Vale ON (B3)",
        }
        # Candles de 1 minuto para Day Trade
        self.intraday_candles: Dict[str, List[StockCandle]] = {}
        # Candles diários para Swing Trade
        self.daily_candles: Dict[str, List[StockCandle]] = {}
        # Histórico de preços recentes
        self.price_history: Dict[str, List[float]] = {}

        self._seed_initial_stocks()

    def _seed_initial_stocks(self):
        stock_seeds = {
            "NVDA": 138.50,
            "AAPL": 228.30,
            "TSLA": 242.80,
            "MSFT": 422.10,
            "AMZN": 186.40,
            "SPY": 585.20,
            "QQQ": 492.60,
        }
        for symbol, base_price in stock_seeds.items():
            self.register_asset(symbol, base_price)

    def register_asset(self, symbol: str, base_price: float = 120.0, name: str = ""):
        """Registra e inicializa qualquer nova ação no feed em tempo real."""
        symbol = symbol.upper().strip()
        if not symbol:
            return

        if name:
            self.company_names[symbol] = name
        elif symbol not in self.company_names:
            self.company_names[symbol] = f"{symbol} Stock"

        now = time.time()
        self.prices[symbol] = base_price
        self.change_24h[symbol] = round(random.uniform(-1.5, 2.5), 2)
        self.high_24h[symbol] = round(base_price * 1.015, 2)
        self.low_24h[symbol] = round(base_price * 0.985, 2)
        self.intraday_candles[symbol] = []
        self.daily_candles[symbol] = []
        self.price_history[symbol] = []

        # Gera histórico inicial de 60 candles de 1m (Day Trade)
        cur = base_price * 0.99
        for i in range(60):
            t = now - (60 - i) * 60
            var = random.uniform(-0.002, 0.0022)
            op = cur
            cl = cur * (1 + var)
            hi = max(op, cl) * (1 + random.uniform(0.0003, 0.0015))
            lo = min(op, cl) * (1 - random.uniform(0.0003, 0.0015))
            vol = random.uniform(500, 5000)
            self.intraday_candles[symbol].append(StockCandle(t, op, hi, lo, cl, vol))
            self.price_history[symbol].append(cl)
            cur = cl
        self.prices[symbol] = round(cur, 2)

        # Gera histórico inicial de 30 candles diários (Swing Trade)
        day_cur = base_price * 0.92
        for i in range(30):
            dt = now - (30 - i) * 86400
            d_var = random.uniform(-0.015, 0.018)
            d_op = day_cur
            d_cl = day_cur * (1 + d_var)
            d_hi = max(d_op, d_cl) * 1.008
            d_lo = min(d_op, d_cl) * 0.992
            d_vol = random.uniform(100000, 1500000)
            self.daily_candles[symbol].append(StockCandle(dt, d_op, d_hi, d_lo, d_cl, d_vol))
            day_cur = d_cl

    def update_stock_quote(self, symbol: str, price: float, change_pct: Optional[float] = None, high: Optional[float] = None, low: Optional[float] = None):
        symbol = symbol.upper().strip()
        if symbol not in self.prices:
            self.register_asset(symbol, price)

        self.prices[symbol] = round(price, 2)
        if change_pct is not None:
            self.change_24h[symbol] = round(change_pct, 2)
        if high is not None:
            self.high_24h[symbol] = round(high, 2)
        if low is not None:
            self.low_24h[symbol] = round(low, 2)

        if symbol not in self.price_history:
            self.price_history[symbol] = []
        self.price_history[symbol].append(price)
        if len(self.price_history[symbol]) > 300:
            self.price_history[symbol].pop(0)

        # Atualiza candle intraday
        now = time.time()
        if symbol not in self.intraday_candles:
            self.intraday_candles[symbol] = []

        if not self.intraday_candles[symbol] or (now - self.intraday_candles[symbol][-1].timestamp >= 60):
            c = StockCandle(now, price, price, price, price, 100.0)
            self.intraday_candles[symbol].append(c)
            if len(self.intraday_candles[symbol]) > 120:
                self.intraday_candles[symbol].pop(0)
        else:
            c = self.intraday_candles[symbol][-1]
            c.close = price
            c.high = max(c.high, price)
            c.low = min(c.low, price)
            c.volume += 10.0

    def get_price(self, symbol: str) -> float:
        symbol = symbol.upper().strip()
        if symbol not in self.prices:
            self.register_asset(symbol, 100.0)
        return self.prices.get(symbol, 100.0)

    def get_day_trade_snapshot(self, symbol: str) -> dict:
        symbol = symbol.upper().strip()
        price = self.get_price(symbol)
        history = self.price_history.get(symbol, [price])
        
        rsi = calculate_rsi(history, 14)
        ema9 = calculate_ema(history, 9)
        ema21 = calculate_ema(history, 21)
        bollinger = calculate_bollinger_bands(history, 20)
        macd_data = calculate_macd(history)

        return {
            "symbol": symbol,
            "company_name": self.company_names.get(symbol, symbol),
            "mode": "DAY_TRADE",
            "current_price": price,
            "change_pct": self.change_24h.get(symbol, 0.0),
            "high": self.high_24h.get(symbol, price * 1.01),
            "low": self.low_24h.get(symbol, price * 0.99),
            "rsi_14": rsi,
            "ema_9": ema9,
            "ema_21": ema21,
            "bollinger": bollinger,
            "macd": macd_data,
            "momentum": "COMPRA_FORTE" if rsi < 35 and price > ema9 else ("VENDA_FORTE" if rsi > 68 and price < ema9 else "NEUTRO")
        }

    def get_swing_trade_snapshot(self, symbol: str) -> dict:
        symbol = symbol.upper().strip()
        price = self.get_price(symbol)
        daily_closes = [c.close for c in self.daily_candles.get(symbol, [])]
        if not daily_closes:
            daily_closes = [price]

        rsi_daily = calculate_rsi(daily_closes, 14)
        ema_20 = calculate_ema(daily_closes, 20)
        ema_50 = calculate_ema(daily_closes, 50)
        bollinger_daily = calculate_bollinger_bands(daily_closes, 20)
        
        recent_lows = [c.low for c in self.daily_candles.get(symbol, [])[-15:]] or [price * 0.95]
        recent_highs = [c.high for c in self.daily_candles.get(symbol, [])[-15:]] or [price * 1.05]
        support = min(recent_lows)
        resistance = max(recent_highs)

        return {
            "symbol": symbol,
            "company_name": self.company_names.get(symbol, symbol),
            "mode": "SWING_TRADE",
            "current_price": price,
            "change_pct": self.change_24h.get(symbol, 0.0),
            "rsi_daily": rsi_daily,
            "ema_20": ema_20,
            "ema_50": ema_50,
            "trend_direction": "ALTA" if ema_20 > ema_50 else "BAIXA",
            "support_level": round(support, 2),
            "resistance_level": round(resistance, 2),
            "bollinger_daily": bollinger_daily,
        }

    def get_all_tickers(self) -> dict:
        return {
            sym: {
                "symbol": sym,
                "name": self.company_names.get(sym, sym),
                "price": price,
                "change_pct": self.change_24h.get(sym, 0.0),
                "high": self.high_24h.get(sym, price * 1.01),
                "low": self.low_24h.get(sym, price * 0.99),
            }
            for sym, price in self.prices.items()
        }

stock_feed = StockPriceFeed()
