import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database URL configuration (SQLite default, customizable via environment variable)
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "argus.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

# For SQLite, enable check_same_thread=False for multi-threaded Flask requests
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Context-managed database session iterator."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables and create default workspace project if empty."""
    from models.models import Project
    Base.metadata.create_all(bind=engine)
    
    # Ensure default project exists
    db = SessionLocal()
    try:
        default_proj = db.query(Project).filter_by(name="Default Project").first()
        if not default_proj:
            default_proj = Project(
                name="Default Project",
                description="Default security assessment project for Argus 2.0"
            )
            db.add(default_proj)
            db.commit()
            db.refresh(default_proj)
    finally:
        db.close()
