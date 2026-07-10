from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
NEWS_DATA_DIR = DATA_DIR / "news"
DB_PATH = DATA_DIR / "cynthia.db"
ENV_PATH = PROJECT_ROOT / ".env"
PERSONAL_BRAND_PATH = CONFIG_DIR / "personal_brand.md"
