# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# Load environment variables
local_env = os.path.join(os.path.dirname(__file__), '.env')
parent_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
env_path = local_env if os.path.exists(local_env) else parent_env if os.path.exists(parent_env) else None
print('Chemin .env utilisé :', env_path)
if env_path:
    load_dotenv(dotenv_path=env_path)

# Construct PostgreSQL database URL from environment variables
POSTGRES_USER = os.getenv("POSTGRES_USER", "aiuser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "aipassword")
POSTGRES_DB = os.getenv("POSTGRES_DB", "airepert")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

print('DATABASE_URL:', DATABASE_URL)

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to load Solcast API keys and site IDs dynamically
def charger_cles_solcast():
    cles = []
    i = 1
    while True:
        api_key = os.getenv(f'SOLCAST_API_KEY{i}')
        site_id = os.getenv(f'SOLCAST_SITE_ID{i}')
        if api_key and site_id:
            cles.append((api_key, site_id))
            i += 1
        else:
            break
    return cles