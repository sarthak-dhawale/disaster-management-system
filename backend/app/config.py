import os, re
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
DB_URL = os.getenv("DATABASE_URL") or URL.create(
    "mysql+pymysql",
    username=os.getenv("DB_USER", "disaster_user"),
    password=os.getenv("DB_PASSWORD", ""),
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.getenv("DB_NAME", "disaster_management"),
)
ORIGINS = [
    x.strip()
    for x in os.getenv("CORS_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500").split(",")
    if x.strip()
]
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
SESSION_HOURS = int(os.getenv("SESSION_HOURS", "8"))
if not 1 <= SESSION_HOURS <= 168:
    raise ValueError("SESSION_HOURS must be between 1 and 168")
DB_TIME_ZONE = os.getenv("DB_TIME_ZONE", "+05:30")
if not re.fullmatch(r"[+-](?:0\d|1[0-3]):[0-5]\d|\+14:00", DB_TIME_ZONE):
    raise ValueError("DB_TIME_ZONE must be a valid UTC offset, such as +05:30")
