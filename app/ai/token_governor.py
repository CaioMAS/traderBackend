import logging
from datetime import datetime, timezone, date
from app.core.config import settings

logger = logging.getLogger("ai.token_governor")

GROUP1_MODELS = {
    "gpt-5.4", "gpt-5.2", "gpt-5.1", "gpt-5", "gpt-4.1", "gpt-4o", "o1", "o3"
}
GROUP2_MODELS = {
    "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5-mini", "gpt-5-nano",
    "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o-mini", "o3-mini", "o4-mini"
}

# Preços aproximados por 1M de tokens (Entrada / Saída em USD)
PRICING_TABLE = {
    "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "o3-mini": {"input": 1.10 / 1_000_000, "output": 4.40 / 1_000_000},
}

class TokenGovernor:
    """Gerenciador centralizado de orçamento e limites de tokens da OpenAI."""

    def __init__(self):
        self.current_day: date = datetime.now(timezone.utc).date()
        
        self.group1_limit = settings.TOKEN_LIMIT_GROUP1_DAILY # 225.000
        self.group2_limit = settings.TOKEN_LIMIT_GROUP2_DAILY # 2.250.000
        
        self.group1_consumed = 0
        self.group2_consumed = 0
        
        self.total_cost_usd = 0.0
        self.consumption_by_model: dict[str, int] = {}
        self.consumption_by_trader: dict[str, int] = {}

    def _check_and_reset_day(self):
        today = datetime.now(timezone.utc).date()
        if today != self.current_day:
            logger.info(f"Virada de dia detectada ({self.current_day} -> {today}). Reiniciando contadores de tokens.")
            self.current_day = today
            self.group1_consumed = 0
            self.group2_consumed = 0

    def get_group_for_model(self, model_name: str) -> int:
        clean = model_name.lower().strip()
        if any(m in clean for m in GROUP1_MODELS):
            return 1
        return 2

    def can_consume(self, model_name: str, estimated_tokens: int = 1000) -> tuple[bool, str, str]:
        """Verifica se a chamada é permitida e sugere fallback se necessário.
        Retorna: (permitido: bool, modelo_aprovado: str, motivo: str)"""
        self._check_and_reset_day()
        group = self.get_group_for_model(model_name)

        if group == 1:
            used = self.group1_consumed
            limit = self.group1_limit
            # Se atingiu 90% do teto do Grupo 1, faz fallback inteligente para Grupo 2
            if (used + estimated_tokens) >= (limit * 0.90):
                logger.warning(f"Grupo 1 em {used}/{limit} tokens (>=90%). Degradando para modelo econômico gpt-4o-mini.")
                return self.can_consume("gpt-4o-mini", estimated_tokens)
            return True, model_name, "Cota do Grupo 1 disponível"
        else:
            used = self.group2_consumed
            limit = self.group2_limit
            # Se atingiu 95% do teto do Grupo 2, bloqueia chamadas e aciona regras locais heurísticas
            if (used + estimated_tokens) >= (limit * 0.95):
                logger.error(f"CIRCUIT BREAKER: Grupo 2 atingiu {used}/{limit} tokens (>=95%). Bloqueando chamadas de IA.")
                return False, model_name, "Limite diário do Grupo 2 atingido"
            return True, model_name, "Cota do Grupo 2 disponível"

    def record_usage(self, model_name: str, prompt_tokens: int, completion_tokens: int, trader_id: str | None = None) -> float:
        self._check_and_reset_day()
        total = prompt_tokens + completion_tokens
        group = self.get_group_for_model(model_name)

        if group == 1:
            self.group1_consumed += total
        else:
            self.group2_consumed += total

        # Rastreia modelo
        self.consumption_by_model[model_name] = self.consumption_by_model.get(model_name, 0) + total

        # Rastreia operador
        if trader_id:
            self.consumption_by_trader[trader_id] = self.consumption_by_trader.get(trader_id, 0) + total

        # Cálculo de custo estimado em USD
        rates = PRICING_TABLE.get(model_name, PRICING_TABLE["gpt-4o-mini"])
        cost = (prompt_tokens * rates["input"]) + (completion_tokens * rates["output"])
        self.total_cost_usd += cost
        
        return cost

    def get_status_dashboard(self) -> dict:
        self._check_and_reset_day()
        g1_pct = (self.group1_consumed / self.group1_limit * 100) if self.group1_limit > 0 else 0
        g2_pct = (self.group2_consumed / self.group2_limit * 100) if self.group2_limit > 0 else 0

        return {
            "date": self.current_day.isoformat(),
            "group1": {
                "consumed": self.group1_consumed,
                "limit": self.group1_limit,
                "available": max(0, self.group1_limit - self.group1_consumed),
                "pct_used": round(g1_pct, 2),
            },
            "group2": {
                "consumed": self.group2_consumed,
                "limit": self.group2_limit,
                "available": max(0, self.group2_limit - self.group2_consumed),
                "pct_used": round(g2_pct, 2),
            },
            "total_cost_usd": round(self.total_cost_usd, 4),
            "by_model": self.consumption_by_model,
        }

token_governor = TokenGovernor()
