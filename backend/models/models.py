from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, Table
)
from sqlalchemy.orm import relationship
from db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Project(Base):
    """Project entity representing a target scope or assessment campaign."""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    assets = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    scans = relationship("Scan", back_populates="project", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "asset_count": len(self.assets),
            "scan_count": len(self.scans),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Asset(Base):
    """Asset entity representing hostnames, domains, IPs, services, or APIs."""
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    asset_type = Column(String(64), nullable=False, default="Domain")  # Domain, Subdomain, IP, Service, Website, API
    ip_address = Column(String(64), nullable=True, index=True)
    domain = Column(String(255), nullable=True, index=True)
    status = Column(String(32), default="active")  # active, inactive, investigating
    risk_score = Column(Integer, default=0)  # 0 to 100
    first_seen = Column(DateTime, default=utc_now)
    last_seen = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    project = relationship("Project", back_populates="assets")
    services = relationship("Service", back_populates="asset", cascade="all, delete-orphan")
    technologies = relationship("Technology", back_populates="asset", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="asset", cascade="all, delete-orphan")
    
    outgoing_relationships = relationship(
        "Relationship",
        foreign_keys="[Relationship.source_asset_id]",
        back_populates="source_asset",
        cascade="all, delete-orphan"
    )
    incoming_relationships = relationship(
        "Relationship",
        foreign_keys="[Relationship.target_asset_id]",
        back_populates="target_asset",
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "asset_type": self.asset_type,
            "ip_address": self.ip_address,
            "domain": self.domain,
            "status": self.status,
            "risk_score": self.risk_score,
            "service_count": len(self.services),
            "technology_count": len(self.technologies),
            "finding_count": len(self.findings),
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }


class Service(Base):
    """Port & service discovery findings linked to an asset."""
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    port = Column(Integer, nullable=False)
    protocol = Column(String(16), default="tcp")
    service_name = Column(String(64), nullable=False)
    banner = Column(Text, nullable=True)
    version = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    asset = relationship("Asset", back_populates="services")

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "port": self.port,
            "protocol": self.protocol,
            "service_name": self.service_name,
            "banner": self.banner,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Technology(Base):
    """Software/Technology fingerprint attached to an asset."""
    __tablename__ = "technologies"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    version = Column(String(64), nullable=True)
    category = Column(String(64), nullable=True)
    cpe = Column(String(255), nullable=True)

    asset = relationship("Asset", back_populates="technologies")

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "name": self.name,
            "version": self.version,
            "category": self.category,
            "cpe": self.cpe,
        }


class Finding(Base):
    """Vulnerability or security observation linked to an asset."""
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    severity = Column(String(32), default="Informational")  # Critical, High, Medium, Low, Informational
    risk_score = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    cve_id = Column(String(64), nullable=True)
    status = Column(String(32), default="open")  # open, resolved, false_positive
    created_at = Column(DateTime, default=utc_now)

    asset = relationship("Asset", back_populates="findings")

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "title": self.title,
            "severity": self.severity,
            "risk_score": self.risk_score,
            "description": self.description,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "cve_id": self.cve_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Relationship(Base):
    """Directed connection between two assets in the attack graph."""
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True, index=True)
    source_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    target_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(64), nullable=False)  # RESOLVES_TO, SUBDOMAIN_OF, HOSTS_SERVICE, USES_TECH
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=utc_now)

    source_asset = relationship("Asset", foreign_keys=[source_asset_id], back_populates="outgoing_relationships")
    target_asset = relationship("Asset", foreign_keys=[target_asset_id], back_populates="incoming_relationships")

    def to_dict(self):
        return {
            "id": self.id,
            "source_asset_id": self.source_asset_id,
            "target_asset_id": self.target_asset_id,
            "relationship_type": self.relationship_type,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Scan(Base):
    """Scan job model tracking background discovery progress."""
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    target = Column(String(255), nullable=False)
    scan_type = Column(String(64), default="full")  # full, discovery, network, web
    status = Column(String(32), default="pending")  # pending, running, completed, failed
    progress = Column(Integer, default=0)  # 0 to 100
    current_stage = Column(String(128), default="Initializing")
    logs = Column(Text, default="")
    results_summary = Column(Text, nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="scans")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "target": self.target,
            "scan_type": self.scan_type,
            "status": self.status,
            "progress": self.progress,
            "current_stage": self.current_stage,
            "logs": self.logs,
            "results_summary": self.results_summary,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }
