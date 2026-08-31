from datetime import datetime, timezone
# pyrefly: ignore [missing-import]
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, Table, Boolean
)
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship
from db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


def format_utc_iso(dt):
    if not dt:
        return None
    iso = dt.isoformat()
    if not iso.endswith("Z") and "+" not in iso:
        iso += "Z"
    return iso


class User(Base):
    """User entity for authentication and authorization."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": format_utc_iso(self.created_at),
            "updated_at": format_utc_iso(self.updated_at),
        }


class Project(Base):
    """Project entity representing a target scope or assessment campaign."""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(String(128), default="local-user", nullable=False, index=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)  # ACTIVE, ARCHIVED
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    targets = relationship("Target", back_populates="project", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    scans = relationship("Scan", back_populates="project", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="project", cascade="all, delete-orphan")

    def to_dict(self):
        last_scan_time = None
        if self.scans:
            sorted_scans = sorted(self.scans, key=lambda s: s.start_time or datetime.min, reverse=True)
            if sorted_scans and sorted_scans[0].start_time:
                last_scan_time = format_utc_iso(sorted_scans[0].start_time)

        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "target_count": len(self.targets),
            "asset_count": len(self.assets),
            "scan_count": len(self.scans),
            "finding_count": sum(len(a.findings) for a in self.assets),
            "last_scan": last_scan_time,
            "created_at": format_utc_iso(self.created_at),
            "updated_at": format_utc_iso(self.updated_at),
        }


class Target(Base):
    """Target scope entity associated with a project."""
    __tablename__ = "targets"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    target = Column(String(255), nullable=False, index=True)
    target_type = Column(String(64), default="Domain")  # Domain, Subdomain, IP, CIDR, URL
    status = Column(String(32), default="active")  # active, pending, scanned
    created_at = Column(DateTime, default=utc_now)

    project = relationship("Project", back_populates="targets")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "target": self.target,
            "target_type": self.target_type,
            "status": self.status,
            "created_at": format_utc_iso(self.created_at),
        }


class Activity(Base):
    """Audit & history log entity for project events."""
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(128), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    project = relationship("Project", back_populates="activities")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "action": self.action,
            "details": self.details,
            "created_at": format_utc_iso(self.created_at),
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
    status = Column(String(32), default="active")  # active, inactive, investigating, archived
    risk_score = Column(Integer, default=0)  # 0 to 100
    first_seen = Column(DateTime, default=utc_now)
    last_seen = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # Argus 2.0 Asset Feature additions
    exposure = Column(String(64), nullable=True, default="Unknown") # Internet-Facing, Internal, Unknown
    discovery_sources = Column(Text, nullable=True, default="DNS") # comma-separated
    confidence = Column(Integer, default=90)
    tags = Column(Text, nullable=True, default="") # comma-separated
    web_url = Column(String(512), nullable=True)
    web_status_code = Column(Integer, nullable=True)
    web_title = Column(String(256), nullable=True)
    web_server = Column(String(128), nullable=True)
    web_security_headers = Column(Text, nullable=True)
    cert_issuer = Column(String(256), nullable=True)
    cert_valid_from = Column(DateTime, nullable=True)
    cert_expires = Column(DateTime, nullable=True)
    cert_sans = Column(Text, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="assets")
    services = relationship("Service", back_populates="asset", cascade="all, delete-orphan")
    technologies = relationship("Technology", back_populates="asset", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="asset", cascade="all, delete-orphan")
    endpoints = relationship("Endpoint", back_populates="asset", cascade="all, delete-orphan")
    history = relationship("AssetHistory", back_populates="asset", cascade="all, delete-orphan")
    notes = relationship("AssetNote", back_populates="asset", cascade="all, delete-orphan")
    
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
        # Helper to safely split comma-separated text into a list
        def to_list(val):
            if not val:
                return []
            return [x.strip() for x in val.split(",") if x.strip()]

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
            "endpoint_count": len(self.endpoints),
            "note_count": len(self.notes),
            "history_count": len(self.history),
            "first_seen": format_utc_iso(self.first_seen),
            "last_seen": format_utc_iso(self.last_seen),
            # Argus 2.0 Asset Feature additions
            "exposure": self.exposure or "Unknown",
            "discovery_sources": to_list(self.discovery_sources or "DNS"),
            "confidence": self.confidence,
            "tags": to_list(self.tags),
            "web_url": self.web_url,
            "web_status_code": self.web_status_code,
            "web_title": self.web_title,
            "web_server": self.web_server,
            "web_security_headers": self.web_security_headers,
            "cert_issuer": self.cert_issuer,
            "cert_valid_from": format_utc_iso(self.cert_valid_from),
            "cert_expires": format_utc_iso(self.cert_expires),
            "cert_sans": to_list(self.cert_sans)
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
    state = Column(String(32), default="Open")  # Open, Closed, Filtered
    discovery_source = Column(String(64), nullable=True)
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
            "state": self.state,
            "discovery_source": self.discovery_source,
            "created_at": format_utc_iso(self.created_at),
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
    vendor = Column(String(128), nullable=True)
    detection_source = Column(String(64), nullable=True)
    confidence = Column(Integer, default=90)

    asset = relationship("Asset", back_populates="technologies")

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "name": self.name,
            "version": self.version,
            "category": self.category,
            "cpe": self.cpe,
            "vendor": self.vendor,
            "detection_source": self.detection_source,
            "confidence": self.confidence
        }



class Finding(Base):
    """Vulnerability or security observation linked to an asset."""
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id", ondelete="SET NULL"), nullable=True, index=True)
    target_id = Column(Integer, ForeignKey("targets.id", ondelete="SET NULL"), nullable=True, index=True)
    first_scan_id = Column(Integer, ForeignKey("scans.id", ondelete="SET NULL"), nullable=True)
    last_scan_id = Column(Integer, ForeignKey("scans.id", ondelete="SET NULL"), nullable=True)
    
    title = Column(String(255), nullable=False)
    severity = Column(String(32), default="Informational")  # Critical, High, Medium, Low, Informational
    priority = Column(String(32), nullable=True)  # CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL
    priority_score = Column(Integer, default=0)
    priority_explanation = Column(Text, nullable=True)  # JSON or text string of factors
    risk_score = Column(Integer, default=0)
    cvss_score = Column(Float, nullable=True)
    
    description = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    cve_id = Column(String(64), nullable=True)
    
    port = Column(Integer, nullable=True)
    service_name = Column(String(64), nullable=True)
    technology = Column(String(128), nullable=True)
    endpoint = Column(String(512), nullable=True)
    discovery_source = Column(String(128), nullable=True)

    status = Column(String(32), default="open")  # open, resolved, false_positive
    lifecycle_status = Column(String(32), default="NEW")  # NEW, EXISTING, RECURRING, RESOLVED
    ai_enhanced = Column(Boolean, default=False)
    first_seen = Column(DateTime, default=utc_now)
    last_seen = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    asset = relationship("Asset", back_populates="findings")
    scan = relationship("Scan", foreign_keys=[scan_id])
    target = relationship("Target", foreign_keys=[target_id])
    first_scan = relationship("Scan", foreign_keys=[first_scan_id])
    last_scan = relationship("Scan", foreign_keys=[last_scan_id])

    def to_dict(self):
        asset_name = self.asset.name if self.asset else None
        project_id = self.asset.project_id if self.asset else None
        project_name = self.asset.project.name if (self.asset and self.asset.project) else None
        target_name = self.target.target if self.target else (self.scan.target if self.scan else None)
        exposure = self.asset.exposure if self.asset else "Unknown"
        asset_risk_score = self.asset.risk_score if self.asset else 0

        explanation_list = []
        if self.priority_explanation:
            try:
                import json
                explanation_list = json.loads(self.priority_explanation)
            except Exception:
                explanation_list = [f.strip() for f in self.priority_explanation.split("\n") if f.strip()]

        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "asset_name": asset_name,
            "project_id": project_id,
            "project_name": project_name,
            "target_id": self.target_id,
            "target_name": target_name,
            "scan_id": self.scan_id,
            "first_scan_id": self.first_scan_id,
            "last_scan_id": self.last_scan_id,
            "title": self.title,
            "severity": self.severity,  # Original severity - never overwritten
            "priority": self.priority or (self.severity.upper() if self.severity else "INFORMATIONAL"),
            "priority_score": self.priority_score or 0,
            "priority_explanation": explanation_list,
            "risk_score": self.risk_score,
            "cvss": round(min(10.0, max(0.0, float(self.cvss_score) if self.cvss_score is not None else (float(self.risk_score or 0) / 10.0 if (self.risk_score or 0) > 10 else float(self.risk_score or 0)))), 1),
            "description": self.description,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "cve_id": self.cve_id,
            "status": self.status,
            "lifecycle_status": self.lifecycle_status or "NEW",
            "ai_enhanced": self.ai_enhanced or False,
            "port": self.port,
            "service_name": self.service_name,
            "technology": self.technology,
            "endpoint": self.endpoint,
            "exposure": exposure,
            "asset_risk_score": asset_risk_score,
            "discovery_source": self.discovery_source or "Scanner",
            "first_seen": format_utc_iso(self.first_seen or self.created_at),
            "last_seen": format_utc_iso(self.last_seen or self.created_at),
            "created_at": format_utc_iso(self.created_at),
        }


class Relationship(Base):
    """Directed connection between assets and entities in the attack relationship graph."""
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    source_id = Column(String(255), nullable=False, index=True)
    source_type = Column(String(64), nullable=False, default="Asset")
    source_label = Column(String(255), nullable=True)
    source_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=True, index=True)
    
    target_id = Column(String(255), nullable=False, index=True)
    target_type = Column(String(64), nullable=False, default="Entity")
    target_label = Column(String(255), nullable=True)
    target_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=True, index=True)
    
    relationship_type = Column(String(64), nullable=False)  # SUBDOMAIN_OF, RESOLVES_TO, HAS_PORT, RUNS_SERVICE, USES_TECH, HAS_ENDPOINT, HAS_CERTIFICATE, HAS_FINDING, DISCOVERED_IN_SCAN, BELONGS_TO_TARGET
    confidence = Column(Float, default=1.0)
    source_scan_id = Column(Integer, ForeignKey("scans.id", ondelete="SET NULL"), nullable=True, index=True)
    discovery_source = Column(String(128), nullable=True)
    status = Column(String(32), default="active", nullable=False)  # active, stale
    first_seen = Column(DateTime, default=utc_now)
    last_seen = Column(DateTime, default=utc_now, onupdate=utc_now)
    created_at = Column(DateTime, default=utc_now)

    source_asset = relationship("Asset", foreign_keys=[source_asset_id], back_populates="outgoing_relationships")
    target_asset = relationship("Asset", foreign_keys=[target_asset_id], back_populates="incoming_relationships")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "source_label": self.source_label or self.source_id,
            "source_asset_id": self.source_asset_id,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "target_label": self.target_label or self.target_id,
            "target_asset_id": self.target_asset_id,
            "relationship_type": self.relationship_type,
            "confidence": self.confidence,
            "source_scan_id": self.source_scan_id,
            "discovery_source": self.discovery_source or "Scan Correlation",
            "status": self.status or "active",
            "first_seen": format_utc_iso(self.first_seen or self.created_at),
            "last_seen": format_utc_iso(self.last_seen or self.created_at),
            "created_at": format_utc_iso(self.created_at),
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
            "start_time": format_utc_iso(self.start_time),
            "end_time": format_utc_iso(self.end_time),
        }


class Endpoint(Base):
    """Endpoint entity for tracking APIs and Web endpoints."""
    __tablename__ = "endpoints"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    method = Column(String(16), default="GET")
    path = Column(String(512), nullable=False)
    status_code = Column(Integer, nullable=True)
    discovery_source = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    asset = relationship("Asset", back_populates="endpoints")

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "method": self.method,
            "path": self.path,
            "status_code": self.status_code,
            "discovery_source": self.discovery_source,
            "created_at": format_utc_iso(self.created_at),
        }


class AssetHistory(Base):
    """Tracks historical events/changes for a given asset."""
    __tablename__ = "asset_history"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    event_name = Column(String(128), nullable=False)
    event_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    asset = relationship("Asset", back_populates="history")

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "event_name": self.event_name,
            "event_details": self.event_details,
            "created_at": format_utc_iso(self.created_at),
        }


class AssetNote(Base):
    """Tracks analyst notes for an asset."""
    __tablename__ = "asset_notes"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    author = Column(String(128), default="Analyst")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    asset = relationship("Asset", back_populates="notes")

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "author": self.author,
            "content": self.content,
            "created_at": format_utc_iso(self.created_at),
        }

