from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# --- Project Schemas ---
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Unique project name")
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    id: int
    asset_count: int = 0
    scan_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- Asset Schemas ---
class AssetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    asset_type: str = "Domain"
    ip_address: Optional[str] = None
    domain: Optional[str] = None
    status: str = "active"
    risk_score: int = Field(default=0, ge=0, le=100)


class AssetCreate(AssetBase):
    project_id: int


class AssetResponse(AssetBase):
    id: int
    project_id: int
    service_count: int = 0
    technology_count: int = 0
    finding_count: int = 0
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- Finding Schemas ---
class FindingBase(BaseModel):
    title: str
    severity: str = "Informational"
    risk_score: int = 0
    description: Optional[str] = None
    evidence: Optional[str] = None
    recommendation: Optional[str] = None
    cve_id: Optional[str] = None
    status: str = "open"


class FindingCreate(FindingBase):
    asset_id: int


class FindingResponse(FindingBase):
    id: int
    asset_id: int
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- Scan Schemas ---
class ScanCreate(BaseModel):
    target: str = Field(..., min_length=1, max_length=255)
    project_id: Optional[int] = None
    scan_type: str = "full"


class ScanResponse(BaseModel):
    id: int
    project_id: int
    target: str
    scan_type: str
    status: str
    progress: int
    current_stage: str
    logs: Optional[str] = ""
    results_summary: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
