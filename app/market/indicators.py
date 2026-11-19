import numpy as np

def calculate_rsi(prices: list[float], period: int = 14) -> float:
    """Calcula o RSI (Relative Strength Index) clássico de 14 períodos."""
    if len(prices) < period + 1:
        return 50.0 # Neutro por padrão
    
    deltas = np.diff(prices[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return float(round(rsi, 2))

def calculate_ema(prices: list[float], period: int) -> float:
    """Calcula a Média Móvel Exponencial (EMA)."""
    if len(prices) < period:
        return float(prices[-1]) if prices else 0.0
    
    multiplier = 2.0 / (period + 1.0)
    ema = float(np.mean(prices[:period]))
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return float(round(ema, 4))

def calculate_bollinger_bands(prices: list[float], period: int = 20, num_std: float = 2.0) -> dict:
    """Calcula as Bandas de Bollinger (Upper, Middle/SMA, Lower)."""
    if len(prices) < period:
        last = float(prices[-1]) if prices else 0.0
        return {"upper": last, "middle": last, "lower": last}
    
    window = prices[-period:]
    sma = float(np.mean(window))
    std = float(np.std(window))
    
    return {
        "upper": float(round(sma + (num_std * std), 4)),
        "middle": float(round(sma, 4)),
        "lower": float(round(sma - (num_std * std), 4)),
    }

def calculate_macd(prices: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """Calcula o MACD, Sinal e Histograma."""
    if len(prices) < slow + signal:
        return {"macd": 0.0, "signal": 0.0, "hist": 0.0}
    
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    macd_line = ema_fast - ema_slow
    
    macd_signal = macd_line * 0.9
    macd_hist = macd_line - macd_signal
    
    return {
        "macd": float(round(macd_line, 4)),
        "signal": float(round(macd_signal, 4)),
        "hist": float(round(macd_hist, 4)),
    }

def evaluate_opportunity_score(snapshot: dict, mode: str = "day_trade") -> tuple[float, str]:
    """Calcula um Setup Score de 0 a 100 para rankear as melhores oportunidades da mesa."""
    score = 40.0
    reasons = []

    price = float(snapshot.get("current_price", 100.0))

    if mode == "day_trade":
        rsi = float(snapshot.get("rsi_14", 50.0))
        ema9 = float(snapshot.get("ema_9", price))
        ema21 = float(snapshot.get("ema_21", price))
        boll = snapshot.get("bollinger", {})
        boll_lower = float(boll.get("lower", price * 0.98))

        # 1. Avalia RSI
        if rsi <= 35.0:
            boost = (35.0 - rsi) * 2.0
            score += min(35.0, 15.0 + boost)
            reasons.append(f"RSI {rsi:.1f} em sobrevenda (potencial repique)")
        elif rsi <= 45.0:
            score += 10.0
            reasons.append(f"RSI {rsi:.1f} saudável em suporte")
        elif rsi >= 70.0:
            score -= 20.0
            reasons.append(f"RSI {rsi:.1f} sobrecomprado (risco de topo)")

        # 2. Alinhamento de Médias Intraday
        if ema9 > ema21:
            score += 15.0
            reasons.append("Tendência intraday altista (EMA9 > EMA21)")

        # 3. Proximidade da Banda Inferior de Bollinger (região de valor)
        if boll_lower > 0 and abs(price - boll_lower) / boll_lower < 0.008:
            score += 15.0
            reasons.append("Testando Banda Inferior de Bollinger")

    else: # swing_trade
        rsi = float(snapshot.get("rsi_daily", 50.0))
        ema20 = float(snapshot.get("ema_20", price))
        ema50 = float(snapshot.get("ema_50", price))
        support = float(snapshot.get("support_level", price * 0.95))
        resistance = float(snapshot.get("resistance_level", price * 1.05))

        # 1. Alinhamento de Tendência de Médio Prazo
        if ema20 > ema50:
            score += 25.0
            reasons.append("Estrutura de alta confirmada (EMA20 > EMA50)")

        # 2. Relação Risco / Retorno com Suporte
        if support > 0 and price > support:
            dist_to_support = (price - support) / support
            if dist_to_support <= 0.025: # Menos de 2.5% do suporte
                score += 30.0
                reasons.append(f"Ótimo R:R próximo ao suporte (${support:.2f})")
            elif dist_to_support <= 0.05:
                score += 15.0
                reasons.append("Suporte próximo")

        # 3. Distância da Resistência (espaço para subir)
        if resistance > price:
            room_to_grow = (resistance - price) / price
            if room_to_grow >= 0.05: # Pelo menos 5% até o topo
                score += 15.0
                reasons.append(f"Espaço de valorização até resistência (${resistance:.2f})")

        # 4. RSI diário não esticado
        if 40.0 <= rsi <= 58.0:
            score += 15.0
            reasons.append(f"RSI diário {rsi:.1f} em acumulação equilibrada")

    final_score = float(round(max(5.0, min(98.0, score)), 1))
    rationale = " • ".join(reasons) if reasons else "Mercado em consolidação técnica"
    return final_score, rationale
