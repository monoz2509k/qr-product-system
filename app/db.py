from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, connect_args={"connect_timeout": 2})
SessionLocal = sessionmaker(bind=engine)
