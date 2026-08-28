import os
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import declarative_base, sessionmaker

# Database URL configuration (SQLite default, customizable via environment variable)
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
backend_db = os.path.join(BASE_DIR, "backend", "argus.db")
DEFAULT_DB_PATH = backend_db if os.path.exists(backend_db) else os.path.join(BASE_DIR, "argus.db")
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
    from models.models import Project, Asset, Service, Technology, Endpoint, AssetHistory, AssetNote

    # Ensure relationships table is recreated if old NOT NULL schema is present
    with engine.begin() as conn:
        res = conn.exec_driver_sql("PRAGMA table_info(relationships)")
        cols = res.fetchall()
        if cols and any(c[1] == "source_asset_id" and c[3] == 1 for c in cols):
            conn.exec_driver_sql("DROP TABLE relationships")

    Base.metadata.create_all(bind=engine)
    
    # Dynamic SQLite migrations for new columns
    with engine.begin() as conn:
        def add_col(table, col, col_type):
            res = conn.exec_driver_sql(f"PRAGMA table_info({table})")
            existing_cols = [row[1] for row in res.fetchall()]
            if col not in existing_cols:
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")

        # projects table
        add_col("projects", "owner_id", "VARCHAR(128) DEFAULT 'local-user'")
        add_col("projects", "status", "VARCHAR(32) DEFAULT 'ACTIVE'")

        # assets table
        add_col("assets", "exposure", "VARCHAR(64) DEFAULT 'Unknown'")
        add_col("assets", "discovery_sources", "TEXT DEFAULT 'DNS'")
        add_col("assets", "confidence", "INTEGER DEFAULT 90")
        add_col("assets", "tags", "TEXT DEFAULT ''")
        add_col("assets", "web_url", "VARCHAR(512)")
        add_col("assets", "web_status_code", "INTEGER")
        add_col("assets", "web_title", "VARCHAR(256)")
        add_col("assets", "web_server", "VARCHAR(128)")
        add_col("assets", "web_security_headers", "TEXT")
        add_col("assets", "cert_issuer", "VARCHAR(256)")
        add_col("assets", "cert_valid_from", "DATETIME")
        add_col("assets", "cert_expires", "DATETIME")
        add_col("assets", "cert_sans", "TEXT")

        # services table
        add_col("services", "state", "VARCHAR(32) DEFAULT 'Open'")
        add_col("services", "discovery_source", "VARCHAR(64)")

        # technologies table
        add_col("technologies", "vendor", "VARCHAR(128)")
        add_col("technologies", "detection_source", "VARCHAR(64)")
        add_col("technologies", "confidence", "INTEGER DEFAULT 90")

        # relationships table
        add_col("relationships", "project_id", "INTEGER")
        add_col("relationships", "source_id", "VARCHAR(255)")
        add_col("relationships", "source_type", "VARCHAR(64) DEFAULT 'Asset'")
        add_col("relationships", "source_label", "VARCHAR(255)")
        add_col("relationships", "target_id", "VARCHAR(255)")
        add_col("relationships", "target_type", "VARCHAR(64) DEFAULT 'Entity'")
        add_col("relationships", "target_label", "VARCHAR(255)")
        add_col("relationships", "source_scan_id", "INTEGER")
        add_col("relationships", "discovery_source", "VARCHAR(128)")
        add_col("relationships", "status", "VARCHAR(32) DEFAULT 'active'")
        add_col("relationships", "first_seen", "DATETIME")
        # findings table
        add_col("findings", "scan_id", "INTEGER")
        add_col("findings", "target_id", "INTEGER")
        add_col("findings", "first_scan_id", "INTEGER")
        add_col("findings", "last_scan_id", "INTEGER")
        add_col("findings", "priority", "VARCHAR(32)")
        add_col("findings", "priority_score", "INTEGER DEFAULT 0")
        add_col("findings", "priority_explanation", "TEXT")
        add_col("findings", "cvss_score", "FLOAT")
        add_col("findings", "port", "INTEGER")
        add_col("findings", "service_name", "VARCHAR(64)")
        add_col("findings", "technology", "VARCHAR(128)")
        add_col("findings", "endpoint", "VARCHAR(512)")
        add_col("findings", "discovery_source", "VARCHAR(128)")
        add_col("findings", "lifecycle_status", "VARCHAR(32) DEFAULT 'NEW'")
        add_col("findings", "ai_enhanced", "BOOLEAN DEFAULT 0")
        add_col("findings", "first_seen", "DATETIME")
        add_col("findings", "last_seen", "DATETIME")

    # Ensure default project exists
    db = SessionLocal()
    try:
        default_proj = db.query(Project).filter_by(name="Default Project").first()
        if not default_proj:
            default_proj = Project(
                name="Default Project",
                description="Default security assessment project for Argus 2.0",
                status="ACTIVE",
                owner_id="local-user"
            )
            db.add(default_proj)
            db.commit()
            db.refresh(default_proj)
    finally:
        db.close()

