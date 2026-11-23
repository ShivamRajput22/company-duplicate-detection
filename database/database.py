from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker
from pathlib import Path
import os
from app.config import settings

# Ensure database directory exists if path is relative sqlite
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///./"):
    rel_path = db_url.replace("sqlite:///./", "")
    db_file_dir = Path(rel_path).parent
    db_file_dir.mkdir(parents=True, exist_ok=True)
elif db_url.startswith("sqlite:////"):
    pass

connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    echo=False
)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
