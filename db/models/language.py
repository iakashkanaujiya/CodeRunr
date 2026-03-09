from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func

from db.base import Base


class Language(Base):
    __tablename__ = "languages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    version = Column(String, nullable=True)
    compile_cmd = Column(String, nullable=True)
    run_cmd = Column(String, nullable=False)
    source_file = Column(String, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())
