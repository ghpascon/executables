from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.session import Base


class DbRfid(Base):
    __tablename__ = "rfid"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=True, default=func.now())
    device = Column(String(50), nullable=False, index=True)
    epc = Column(String(24), nullable=False, index=True)
    door = Column(Integer, nullable=False)
    user_id = Column(String(50), nullable=False)

class DbUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(String(50), unique=True, index=True, nullable=False)
