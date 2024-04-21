from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL to connect to PostgreSQL database
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://postgres:Homework11@localhost:5433/contacts"

# Creating an engine object
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Creating a session for working with the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base = declarative_base()
Base.metadata.create_all(bind=engine)

# A function to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()