import os
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import declarative_base, sessionmaker

def _load_env_file():
    """Auto-load .env file if present."""
    for p in ['.env', '../.env', 'backend/.env']:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            if k.strip() not in os.environ:
                                os.environ[k.strip()] = v.strip().strip('"').strip("'")
            except Exception:
                pass

_load_env_file()

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Database URL configuration (PostgreSQL / Supabase / SQLite)
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
backend_db = os.path.join(BASE_DIR, "backend", "argus.db")
DEFAULT_DB_PATH = backend_db if os.path.exists(backend_db) else os.path.join(BASE_DIR, "argus.db")

# Fallback to /tmp for serverless read-only filesystems (Vercel / AWS Lambda)
is_serverless = os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
if is_serverless and not os.environ.get("DATABASE_URL"):
    DEFAULT_DB_PATH = "/tmp/argus.db"

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

# Convert postgres:// URI scheme to postgresql:// for SQLAlchemy compatibility
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# For SQLite, enable check_same_thread=False for multi-threaded Flask requests
is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine_kwargs = {
    "connect_args": connect_args,
    "echo": False
}
if not is_sqlite:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(DATABASE_URL, **engine_kwargs)

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
    from models.models import User, Project, Asset, Service, Technology, Endpoint, AssetHistory, AssetNote

    is_sqlite_dialect = engine.dialect.name == "sqlite"

    # SQLite dynamic table column check and reset legacy schema if present
    if is_sqlite_dialect:
        with engine.begin() as conn:
            res = conn.exec_driver_sql("PRAGMA table_info(relationships)")
            cols = res.fetchall()
            if cols and any(c[1] == "source_asset_id" and c[3] == 1 for c in cols):
                conn.exec_driver_sql("DROP TABLE relationships")

    Base.metadata.create_all(bind=engine)
    
    # Dynamic SQLite migrations for new columns
    if is_sqlite_dialect:
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

    # Ensure default project exists and migrate legacy unowned projects
    db = SessionLocal()
    try:
        first_user = db.query(User).order_by(User.id.asc()).first()
        if first_user:
            unowned_projects = db.query(Project).filter(Project.owner_id == "local-user").all()
            for up in unowned_projects:
                up.owner_id = str(first_user.id)
            if unowned_projects:
                db.commit()

        default_proj = db.query(Project).filter_by(name="Default Project").first()
        if not default_proj:
            owner_id = str(first_user.id) if first_user else "local-user"
            default_proj = Project(
                name="Default Project",
                description="Default security assessment project for Argus 2.0",
                status="ACTIVE",
                owner_id=owner_id
            )
            db.add(default_proj)
            db.commit()
            db.refresh(default_proj)

        # Self-healing migration: Normalize legacy finding CVSS scores & recalculate priorities
        from models.models import Finding
        from services.finding_correlator import FindingCorrelator
        from sqlalchemy import or_

        legacy_findings = db.query(Finding).filter(or_(Finding.cvss_score == None, Finding.cvss_score > 10.0)).all()
        for f in legacy_findings:
            needs_update = False
            if f.cvss_score is None:
                if f.risk_score and f.risk_score > 10:
                    f.cvss_score = round(f.risk_score / 10.0, 1)
                elif f.risk_score and f.risk_score <= 10:
                    f.cvss_score = float(f.risk_score)
                else:
                    s_lower = (f.severity or "").lower()
                    if s_lower == "critical": f.cvss_score = 9.0
                    elif s_lower == "high": f.cvss_score = 7.5
                    elif s_lower == "medium": f.cvss_score = 5.3
                    elif s_lower == "low": f.cvss_score = 2.5
                    else: f.cvss_score = 0.0
                needs_update = True
            elif f.cvss_score > 10.0:
                f.cvss_score = round(f.cvss_score / 10.0, 1)
                needs_update = True

            if needs_update:
                FindingCorrelator.correlate_and_prioritize_finding(db, f)

        db.commit()
    except Exception as e:
        print(f"Legacy database self-healing warning: {e}")
    finally:
        db.close()

