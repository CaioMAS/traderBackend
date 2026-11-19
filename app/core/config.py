import os
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent

load_dotenv(ROOT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")

DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DB_PATH = (DATA_DIR / "trading_floor.db").as_posix()

class Settings:
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    PORT: int = int(os.getenv("PORT", "8000"))
    SECRET_KEY: str = os.getenv("SECRET_KEY", "trading_floor_secret_key_default_2026")
    
    # Senha Mestra para Acesso Web à Mesa de Operações
    ACCESS_PASSWORD: str = os.getenv("ACCESS_PASSWORD", "trader2026")
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Limites diários de tokens com margem de segurança (10% de folga)
    TOKEN_LIMIT_GROUP1_DAILY: int = int(os.getenv("TOKEN_LIMIT_GROUP1_DAILY", "225000"))
    TOKEN_LIMIT_GROUP2_DAILY: int = int(os.getenv("TOKEN_LIMIT_GROUP2_DAILY", "2250000"))
    
    # Banco de Dados Persistente
    raw_db_url = os.getenv("DATABASE_URL", "")
    if not raw_db_url or "trading_floor.db" in raw_db_url:
        DATABASE_URL: str = f"sqlite+aiosqlite:///{DEFAULT_DB_PATH}"
    else:
        DATABASE_URL: str = raw_db_url
    
    # Paper Trading & Mercado de Ações (Capital Base $200.00 por operador)
    PAPER_TRADING_ENABLED: bool = os.getenv("PAPER_TRADING_ENABLED", "true").lower() == "true"
    DEFAULT_INITIAL_CAPITAL: float = float(os.getenv("DEFAULT_INITIAL_CAPITAL", "200.0"))
    SIMULATED_FEE_PERCENTAGE: float = float(os.getenv("SIMULATED_FEE_PERCENTAGE", "0.001")) # 0.1%
    
    raw_assets = os.getenv("DEFAULT_MONITORED_ASSETS", "NVDA,AAPL,TSLA,MSFT,AMZN,SPY,QQQ")
    MONITORED_ASSETS: list[str] = [a.strip().upper() for a in raw_assets.split(",") if a.strip()]
    STOCK_FEED_PROVIDER: str = os.getenv("STOCK_FEED_PROVIDER", "yfinance")

settings = Settings()
