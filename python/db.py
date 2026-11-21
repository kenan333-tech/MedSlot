"""PostgreSQL bağlantisi. Bütün SQLAlchemy skriptləri buradan import edir."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://app:app123@localhost:5432/layihe",
)

# psycopg2 (report.py) üçün eyni bağlantının "sadə" forması
PSYCOPG_DSN = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")

TIMEZONE = "Asia/Baku"

# Sessiyanın saat qurşağı Bakı olsun ki, vaxtlar n8n ilə eyni görünsün
engine = create_engine(
    DATABASE_URL,
    connect_args={"options": f"-c timezone={TIMEZONE}"},
)

SessionLocal = sessionmaker(bind=engine)
