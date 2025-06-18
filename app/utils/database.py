from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database configuration from environment variables
DB_ENGINE = os.getenv('DB_ENGINE', 'sqlite')
DB_USER = os.getenv('DB_USER', 'dummy')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'dummy')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'metadata_extractor')

print(f"Using database engine: {DB_ENGINE}")

# Create database URL
if DB_ENGINE == 'sqlite':
    SQLALCHEMY_DATABASE_URL = "sqlite:///./metadata_extractor.db"
elif DB_ENGINE == 'postgresql':
    SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
elif DB_ENGINE == 'mysql':
    SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    raise ValueError(f"Unsupported database engine: {DB_ENGINE}")

# Create engine with appropriate settings for environment
is_production = os.getenv('FLASK_ENV') == 'production'

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=not is_production,  # Only echo in non-production environments
    pool_pre_ping=True,  # Helps with connection issues after idle periods
    pool_recycle=600,  # Recycle connections after 10 minutes
    pool_size=10 if is_production else 5  # Larger pool for production
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Function to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()