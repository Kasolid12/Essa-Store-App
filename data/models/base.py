# app_essa/data/models/base.py (or data/models/base.py depending on your exact folder name)

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    This is the foundational class that all other SQLAlchemy models inherit from.
    Alembic uses this Base to find all your tables and generate the migrations.
    """
    pass