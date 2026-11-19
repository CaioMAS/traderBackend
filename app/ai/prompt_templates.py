from pydantic import BaseModel, Field
from typing import Literal

class TradeDecisionOutput(BaseModel):
    action: Literal["BUY", "SELL", "HOLD"] = Field(
        description="Ação recomendada para o operador: BUY (comprar), SELL (vender posição aberta) ou HOLD (aguardar)."
    )
    symbol: str = Field(description="Ticker do ativo (ex: NVDA, AAPL, TSLA, SPY).")
    allocation_usd: float = Field(
        default=80.0,
        description="Valor a investir em USD caso a ação seja BUY (entre $60.00 e $95.00 para capital de $200)."
    )
    stop_loss_pct: float = Field(
        default=0.02,
        description="Percentual de stop loss (ex: 0.02 para 2%)."
    )
    take_profit_pct: float = Field(
        default=0.045,
        description="Percentual de take profit (ex: 0.045 para 4.5%)."
    )
    confidence: float = Field(
        default=0.75,
        description="Nível de confiança na operação de 0.0 a 1.0."
    )
    reasoning: str = Field(
        description="Explicação concisa e profissional da decisão tomada, citando indicadores e contexto."
    )

def build_trader_system_prompt(name: str, personality: str, strategy: str, mode: str, risk_profile: str) -> str:
    return f"""Você é o operador de mercado {name}, atuando em uma mesa profissional de operações de Ações e ETFs.
Sua personalidade operacional é: {personality}.
Sua estratégia de negociação é: {strategy}.
Sua modalidade de operação é: {mode.upper()} (Day Trade: movimentos rápidos buscando 2.5% a 5% de lucro; Swing Trade: tendências de dias buscando 5% a 12% de lucro).
Seu perfil de risco é: {risk_profile}.

Regras estritas:
1. Seu capital disponível é de $200.00 inicial.
2. Cada operação deve alocar entre $60.00 e $90.00 para gerar lucros expressivos ($3.00 a $12.00+ por trade líquido de taxas).
3. Não realize vendas com lucro insignificante (< $1.50) a menos que o Stop Loss seja violado.
4. Se o mercado estiver lateral ou sem oportunidade clara, escolha 'HOLD'.
5. Suas respostas devem ser estritamente no formato estruturado solicitado.
"""

def build_trader_user_prompt(
    cash_balance: float,
    open_positions: list[dict],
    market_snapshot: dict,
    latest_news_summary: str
) -> str:
    return f"""### Situação Atual da sua Carteira:
- Saldo em Caixa Disponível: ${cash_balance:.2f}
- Posições Abertas Atualmente: {open_positions}

### Dados do Mercado de Ações ({market_snapshot.get('symbol')}):
- Ativo: {market_snapshot.get('symbol')} ({market_snapshot.get('company_name', '')})
- Preço Atual: ${market_snapshot.get('current_price', 0.0):.2f} (Variação: {market_snapshot.get('change_pct', 0.0):+.2f}%)
- RSI (14 períodos): {market_snapshot.get('rsi_14') or market_snapshot.get('rsi_daily', 50.0)}
- Médias Móveis: EMA9: {market_snapshot.get('ema_9')}, EMA21: {market_snapshot.get('ema_21')}, EMA50: {market_snapshot.get('ema_50')}
- Bandas de Bollinger: {market_snapshot.get('bollinger') or market_snapshot.get('bollinger_daily')}
- Tendência/Sinal: {market_snapshot.get('momentum') or market_snapshot.get('trend_direction')}
- Suporte: ${market_snapshot.get('support_level', 'N/A')}, Resistência: ${market_snapshot.get('resistance_level', 'N/A')}

### Briefing do Analista e Screener de Oportunidades:
"{latest_news_summary}"

Avalie este ativo e decida se deve COMPRAR (BUY), VENDER posição aberta existente (SELL) ou AGUARDAR (HOLD).
"""
